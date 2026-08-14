from .base_filter import BaseFilter, filter_result
import re

class SharedVolumeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _detect_command_error(self, stdout_data):
        output = (stdout_data or "").strip()
        output_lower = output.lower()
        patterns = [
            "illegal option",
            "invalid option",
            "unknown option",
            "usage:",
            "not found",
            "명령을 찾을 수 없습니다",
            "찾을 수 없습니다",
            "cannot",
        ]
        for pattern in patterns:
            if pattern in output_lower:
                return output
        return None

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if self.command.strip().startswith("df"):
            is_success, is_pass, result, message = self.df_type1(stdout_data)
        elif "scsimgr" in self.command:
            is_success, is_pass, result, message = self.scsimgr_type1(stdout_data)
        elif "mount" in self.command:
            is_success, is_pass, result, message = self.aix_mount_type1(stdout_data)
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
            is_pass = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            results_fail = []
            
            try:
                criteria = float(self.inspection_criteria)
            except Exception:
                criteria = 90.0

            if not lines or "filesystem" not in lines[0].lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            
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
                message = f"✅ 모든 파일 시스템 사용량이 임계값({criteria:.1f}%) 이하입니다."
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

            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
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
                        if last_open_close_state_val == abnormal_list_open_close_state:
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

    def aix_mount_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ 'inspection_criteria'가 유효한 문자열이 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message
            
            lines = stdout_data.strip().splitlines()

            header_line = None
            header_idx = -1
            for i, line in enumerate(lines):
                if line.strip().lower().startswith('node'):
                    header_line = line
                    header_idx = i
                    break

            if header_line is None:
                is_pass = 0
                message = f"❌ 출력에서 헤더 라인('node'로 시작)을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            mounted_over_col = header_line.find('mounted over')
            vfs_col = header_line.find('vfs')
            options_col = header_line.find('options')

            if -1 in [mounted_over_col, vfs_col, options_col]:
                is_pass = 0
                message = f"❌ 헤더에서 컬럼을  찾을 수 없어 파싱에 실패했습니다."
                result = message
                return is_success, is_pass, result, message

            failed_volumes = []
            found_matching_volume = False

            for line in lines[header_idx + 1:]:
                if line.strip().startswith('---') or not line.strip():
                    continue
                
                mounted_over = line[mounted_over_col:vfs_col].strip()
                options = line.strip().split()[-1]

                if self.inspection_criteria in mounted_over:
                    found_matching_volume = True
                    opts_list = [opt.strip() for opt in options.split(',')]
                    if 'ro' in opts_list:
                        failed_volumes.append(line)

            if not found_matching_volume:
                # 점검 대상이 없는 경유
                is_pass = 1
                message = f"✅ 'mounted over' 경로에 '{self.inspection_criteria}'을(를) 포함하는 점검 대상 공유 볼륨이 없습니다."
            else:
                if failed_volumes:
                    is_pass = 0
                    failed_output = header_line + "\n" + "\n".join(failed_volumes)
                    message = f"❌ 다음 공유 볼륨이 'ro' 옵션으로 마운트되었습니다:\n{failed_output}"
                else:
                    is_pass = 1
                    message = f"✅ '{self.inspection_criteria}' 경로를 포함하는 모든 공유 볼륨이 정상입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"공유 볼륨 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
