from .base_filter import BaseFilter, filter_result
import re

class VrrpFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""

        if "show vrrp" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message
        
        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def juniper_type1(self, stdout_data):
        """'show vrrp' tabular 출력에서 'State'가 UP이고 'VR Mode'가 Active인지 확인합니다."""
        try:
            is_success = 1
            lines = stdout_data.strip().splitlines()

            failing_instances = []
            processed_main_lines = 0
            
            header_found = False
            for line in lines:
                if "Interface" in line and "State" in line and "VR Mode" in line:
                    header_found = True
                    continue
                if not header_found:
                    continue
                
                line = line.strip()
                if not line:
                    continue

                parts = line.split()

                if len(parts) >= 5:
                    processed_main_lines += 1
                    state = parts[1].lower()
                    vr_mode = parts[4].lower()

                    if state != 'up' or vr_mode != 'active':
                        failing_instances.append(line)

            if failing_instances:
                is_pass = 0
                message = "❌ 다음 VRRP 인스턴스가 비정상 상태입니다:\n" + "\n".join(failing_instances)
            elif processed_main_lines == 0:
                is_pass = 0
                message = "❌ 점검할 VRRP 인스턴스를 찾을 수 없습니다."
            else:
                is_pass = 1
                message = "✅ 모든 VRRP 인스턴스가 정상 상태입니다 (State: UP, VR Mode: Active)."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ VRRP 점검 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
