from .base_filter import BaseFilter, filter_result
import re

class InodeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _find_inode_column(self, header_parts):
        normalized = [part.strip().lower() for part in header_parts]
        candidates = {"iuse%", "%iused", "iused%", "%iuse"}

        for idx, part in enumerate(normalized):
            if part in candidates:
                return idx

        return -1

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "bdf -i" in self.command:
            is_success, is_pass, result, message = self.bdf_i_type1(stdout_data)
        elif "df -i" in self.command:
            is_success, is_pass, result, message = self.df_i_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def bdf_i_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            messages_list = []

            threshold = self.inspection_criteria if isinstance(self.inspection_criteria, (int, float)) else 80
            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "Filesystem" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            data_started = False
            filesystem_found_count = 0            

            for line in lines:
                stripped_line = line.strip()
                
                if not data_started and stripped_line.startswith("Filesystem"):
                    data_started = True
                    continue

                if not data_started or not stripped_line:
                    continue

                parts = stripped_line.split()
                if len(parts) >= 8 and parts[7].endswith("%"):
                    try:
                        iused_pct_str = parts[7]
                        iused_pct = float(iused_pct_str.replace("%", ""))
                        filesystem = parts[0]
                        filesystem_found_count += 1

  
                        if iused_pct >= threshold:
                            is_pass = 0
                            messages_list.append(f"❌ 파일시스템 '{filesystem}' 사용률 {iused_pct}% (기준: {threshold}%) - 기준값 초과")  
                    except ValueError:
                        messages_list.append(f"❌ 파일시스템 사용률 파싱 오류: {stripped_line}")
                        is_pass = 0
            if not data_started or filesystem_found_count == 0:
                is_pass = 0
                messages_list.insert(0, f"❌ 'bdf -i' 명령어 줄에서 파일시스템 데이터를 찾을 수 없습니다. (출력값:{str(stdout_data).strip()[:200]}...)")
            if is_pass == 1:
                message = f"✅ 모든 파일시스템 사용률이 정상입니다. (기준: {threshold}%)"
            else:
                message = "\n".join(messages_list) if messages_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def df_i_type1(self, stdout_data):
        try:
            is_success = 1
            try:
                criteria = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = f"❌ 'inspection_criteria' 변수가 정수형식이 아닙니다: {self.inspection_criteria}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            header_line = None
            header_idx = -1
            for i, line in enumerate(lines):
                if line.strip().startswith('Filesystem'):
                    header_line = line
                    header_idx = i
                    break

            if not lines:
                is_pass = 0
                message = "❌ 점검할 내용이 없습니다."
            elif header_line is None:
                is_pass = 0
                message = "❌ 출력에서 'Filesystem' 헤더를 찾을 수 없습니다."
            elif self._find_inode_column(header_line.split()) == -1:
                is_pass = 0
                message = "❌ 'Filesystem' 헤더에서 I-Node 사용률 컬럼(IUse%, %Iused 등)을 찾을 수 없습니다."
            else:
                header_parts = header_line.split()
                iused_col_idx = self._find_inode_column(header_parts)
                failed_lines = []
                for line in lines[header_idx + 1:]:
                    parts = line.split()
                    if not parts or not parts[0].startswith('/'):
                        continue

                    try:
                        iused_value_str = parts[iused_col_idx]
                        iused_value = int(iused_value_str.strip('%'))
                        if iused_value > criteria:
                            failed_lines.append(line)
                    except (ValueError, IndexError) as e:
                        print(f"I-Node 필터 파싱 오류: 라인 '{line}' 처리 중. {e}")
                        continue

                if failed_lines:
                    is_pass = 0
                    failed_output = header_line + "\n" + "\n".join(failed_lines)
                    message = f"❌ I-Node 사용률 점검 필요:\n{failed_output}"
                else:
                    is_pass = 1
                    message = "✅ 모든 파일시스템의 I-Node 사용률이 정상입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ I-Node 필터 처리 중 에러 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
