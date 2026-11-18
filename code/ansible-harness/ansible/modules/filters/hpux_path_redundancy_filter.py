from .base_filter import BaseFilter, filter_result
import re

class HPUXPathRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "scsimgr" in self.command:
            is_success, is_pass, result, message = self.scsimgr_type1(stdout_data)
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

    def scsimgr_type1(self, stdout_data):
        try:
            is_success = 1
            message_line = []
            is_pass = 1

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "PATH" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'PATH' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if isinstance(self.inspection_criteria, dict):
                min_paths = self.inspection_criteria.get('min_paths', 2)
                fail_states = self.inspection_criteria.get('fail_states', ['DISCONNECTED', 'FAILED', 'OFFLINE'])
            else:
                min_paths = 2
                fail_states = ['DISCONNECTED', 'FAILED', 'OFFLINE']

            fail_states_upper = [s.upper() for s in fail_states]

            lun_blocks = stdout_data.strip().split('LUN PATH INFORMATION FOR LUN :')
            if lun_blocks and not lun_blocks[0].strip():
                lun_blocks = lun_blocks[1:]

            if not lun_blocks:
                is_pass = 0
                message_line.append("❌ 출력에서 LUN 경로 정보를 찾을 수 없습니다.")

            total_luns_processed = 0

            for block in lun_blocks:
                total_luns_processed += 1
                lun_name_match = re.search(r'^(.*?)\n', block)
                lun_name = lun_name_match.group(1).strip() if lun_name_match else "Unknown LUN"

                path_count_match = re.search(r'Total number of LUN paths\s*=\s*(\d+)', block, re.IGNORECASE)
                if path_count_match:
                    path_count = int(path_count_match.group(1))
                    # if path_count < min_paths:
                    #     is_pass = 0
                    #     message_line.append(f"❌ LUN '{lun_name}': Path 개수 부족 (현재: {path_count}, 필요: {min_paths} 이상)")
                else:
                    is_pass = 0
                    message_line.append(f"❌ LUN '{lun_name}': 'Total number of LUN paths' 정보를 찾을 수 없습니다.")
                    continue

                path_sections = block.strip().split('LUN path :')
                if path_sections and not path_sections[0].strip():
                    path_sections = path_sections[1:]

                for path_section in path_sections:
                    state_match = re.search(r'State\s*=\s*(\w+)', path_section, re.IGNORECASE)
                    if state_match:
                        state = state_match.group(1).upper()
                        if state in fail_states_upper and path_count < min_paths:
                            path_name_match = re.search(r'(\w+)', path_section.strip())
                            path_name = path_name_match.group(1) if path_name_match else "Unknown Path"
                            is_pass = 0
                            message_line.append(f"❌ LUN '{lun_name}': Path '{path_name}' 의 상태가 비정상입니다. (상태: {state})")
                
                if total_luns_processed == 0 and is_pass == 1:
                    is_pass = 0
                    message_line.append(f"❌ LUN 정보를 찾지 못했습니다.")

                if is_pass:
                    message = f"✅모든 LUN({total_luns_processed}개) 의 Path 이중화 상태가 정상입니다."
                else:
                    message = "\n".join(message_line) if message_line else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

                result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Path 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
