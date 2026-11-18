from .base_filter import BaseFilter, filter_result
import re

class RHEL6SharedVolumeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "df -h" in self.command:
            is_success, is_pass, result, message = self.df_type1(stdout_data)
        elif "scsimgr" in self.command:
            is_success, is_pass, result, message = self.scsimgr_type1(stdout_data)
        elif "mount" in self.command:
            is_success, is_pass, result, message = self.mount_type1(stdout_data)
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

    def df_type1(self, stdout_data):
        try:
            is_success = 1
            lines = stdout_data.splitlines()
            results_fail = []
            is_pass = 1
            
            try:
                criteria = float(self.inspection_criteria)
            except Exception:
                criteria = 90.0
            
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 6 and "%" in parts[4]:
                    try:
                        usage_percent = float(parts[4].replace("%", ""))
                        mount_point = parts[5]
                        if usage_percent > criteria:
                            is_pass = 0
                            results_fail.append(f"❌ {mount_point}: {usage_percent:.1f}% (기준 {criteria:.1f}%)")
                    except ValueError:
                        continue

            if not results_fail:
                message = "✅ 모든 파일 시스템 사용량이 임계값({criteria:.1f}%) 이하입니다."
            else:
                message = "\n".join(results_fail)
            
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def scsimgr_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            
            message_list = []

            abnormal_states = []
            abnormal_list_open_close_state = "INACTIVE"

            if isinstance(self.inspection_criteria, list):
                abnormal_states = [str(item).upper() for item in self.inspection_criteria]

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "INFORMATION" not in stdout_data:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'INFORMATION' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lun_sections = re.split(r'(?m)^ {8}LUN PATH INFORMATION FOR LUN : (.+)', stdout_data)[1:]

            for i in range(0, len(lun_sections), 2):
                lun_name = lun_sections[1].strip()
                lun_content = lun_sections[i+1]

                total_paths_match = re.search(r'Total number or LUN paths\s+=\s*(\d+)', lun_content)
                total_paths = int(total_paths_match.group(1)) if total_paths_match else 0

                if total_paths == 2:
                    lun_paths = re.split(r'(?m)^LUN path\s*:\s*(.+)', lun_content)[1:]

                    for j in range(0, len(lun_paths), 2):
                        lun_path_name = lun_paths[j].strip()
                        lun_path_content = lun_paths[j+1]

                        state_match = re.search(r'State\s*=\s*(.+)', lun_path_content)
                        state_val = state_match.group(1).strip().upper() if state_match else "UNKNOWN"

                        last_open_close_state_match = re.search(r'Last Open or Close state\s*=\s*(.+)', lun_path_content)
                        last_open_close_state_val = last_open_close_state_match.group(1).strip().upper() if last_open_close_state_match else "UNKNOWN"

                        if state_val in abnormal_states:
                            is_pass = 0
                            message_list.append(f"❌ LUN '{lun_name}' 의 경로 '{lun_path_name}' 상태가 비정상: '{state_val}' (허용 불가: {', '.join(abnormal_states)})")
                        if last_open_close_state_val == last_open_close_state_match:
                            is_pass = 0
                            message_list.append(f"❌ LUN '{lun_name}' 의 경로 '{lun_path_name}' Last Open or Close state가 비정상: '{last_open_close_state_val}'")


            if is_pass == 1:
                message = "✅ 모든 LUN 경로 상태가 정상입니다."
            else:
                message = "\n".join(messages_list) if messages_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def mount_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_lines = []

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ 'inspection_criteria'가 유효한 문자열이 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            shared_path = self.inspection_criteria.strip()
            
            lines = stdout_data.splitlines()

            matched_lines = []
            for line in lines:
                if f" on {shared_path} " in line:
                    matched_lines.append(line.strip())

            if not matched_lines:
                message = f"✅mount 경로에 '{shared_path}'을(를) 포함하는 점검 대상 공유 볼륨이 없습니다."
                result = message
                return is_success, is_pass, result, message

            for mline in matched_lines:
                if "(" in mline and ")" in mline:
                    opts = mline.split("(", 1)[-1].rsplit(")", 1)[0].lower()
                else:
                    is_pass = 0
                    message_lines.append(f"❌ {shared_path}: mount 옵션 파싱 실패({mline})")
                    continue

                opt_tokens = [o.strip() for o in opts.split(",")]

                if "ro" in opt_tokens:
                    is_pass = 0
                    message_lines.append(f"❌{shared_path}: Read-only(ro)로 마운트 상태 ({opts})")
                elif "rw" in opt_tokens:
                    pass
                else:
                    is_pass = 0
                    message_lines.append(f"❌{shared_path}: rw/ro 옵션 확인 불가 ({opts})")

            if is_pass == 1:
                message = f"✅공유 볼륨 상태 정상"
            else:
                message = "\n".join(message_list)
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"공유 볼륨 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
