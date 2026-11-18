from .base_filter import BaseFilter, filter_result
import re

class Rhel6InodeFilter(BaseFilter):
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

        if "df -i" in self.command:
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

    def df_i_type1(self, stdout_data):
        try:
            is_success = 1

            try:
                criteria = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = f"❌ inspection_criteria 가 정수 형식이 아닙니다: {self.inspection_criteria}"
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

            if not lines or header_idx == -1:
                is_pass = 0
                message = "❌ 점검할 내용이 없거나 'Filesystem' 헤더를 찾을 수 없습니다."
            else:
                header_parts = header_line.split()
                try:
                    iused_col_idx = self._find_inode_column(header_parts)
                    if iused_col_idx == -1:
                        raise ValueError
                    failed_lines = []
                    
                    for line in lines[header_idx + 1:]:
                        parts = line.split()
                        if not parts or not parts[0].startswith('/'): continue
                        try:
                            iused_value = int(parts[iused_col_idx].strip('%'))
                            if iused_value > criteria:
                                failed_lines.append(line)
                        except (ValueError, IndexError):
                            continue

                    if failed_lines:
                        is_pass = 0
                        failed_output = header_line + "\n" + "\n".join(failed_lines)
                        message = f"❌ I-Node 사용률이 임계값({criteria}%)을 초과한 파일시스템이 있습니다:\n{failed_output}"
                    else:
                        is_pass = 1
                        message = f"✅ 모든 파일시스템의 I-Node 사용률이 임계값({criteria}%) 이하로 정상입니다."
                
                except ValueError:
                    is_pass = 0
                    message = "❌ 헤더에서 I-Node 사용률 컬럼(IUse%, %Iused 등)을 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ I-Node 필터 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
