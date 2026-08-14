from .base_filter import BaseFilter, filter_result
import re

class PowerFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        장비의 전원 상태를 평가합니다.
        """
        is_success = 1
        message = ""
        
        if "show chassis environment" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "stat system -detail" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def citrix_type1(self, stdout_data):
        """Citrix 'stat system -detail' 출력에서 Power Supply 상태를 점검합니다."""
        try:
            is_success = 1
            failed_power_units = []
            power_lines_found = False

            if isinstance(self.inspection_criteria, list):
                criteria_list = [c.upper() for c in self.inspection_criteria]
            else:
                criteria_string = str(self.inspection_criteria)
                criteria_list = [c.strip().upper() for c in criteria_string.split(',')]

            for line in stdout_data.strip().splitlines():
                stripped_line = line.strip()
                if stripped_line.startswith("Power supply"):
                    power_lines_found = True
                    parts = stripped_line.split()
                    if len(parts) > 4:
                        status = " ".join(parts[4:]).upper()
                        if any(criterion in status for criterion in criteria_list):
                            failed_power_units.append(stripped_line)
            
            if not power_lines_found:
                is_pass = 0
                message = "❌ 'Power supply' 정보를 찾을 수 없습니다."
            elif failed_power_units:
                is_pass = 0
                message = f"❌ 일부 전원 공급 장치의 상태가 비정상('{', '.join(criteria_list)}')입니다:\n" + "\n".join(failed_power_units)
            else:
                is_pass = 1
                message = f"✅ 모든 전원 공급 장치가 정상 상태입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Citrix 전원 상태 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def juniper_type1(self, stdout_data):
        """'show chassis environment' 출력에서 Power 섹션의 상태를 점검합니다."""
        try:
            is_success = 1
            failed_power_units = []
            in_power_section = False
            power_section_found = False
            last_status = "(not found)"

            upper_criteria = str(self.inspection_criteria).upper()
            
            for line in stdout_data.strip().splitlines():
                stripped_line = line.strip()

                if stripped_line.startswith('Power'):
                    in_power_section = True
                    power_section_found = True
                    continue
                
                if in_power_section and not line.startswith(' ') and stripped_line != '':
                    in_power_section = False

                if in_power_section and stripped_line:
                    parts = stripped_line.split()
                    if len(parts) > 1:
                        status = parts[-1].upper()
                        last_status = status
                        if upper_criteria in status:
                            failed_power_units.append(stripped_line)

            if not power_section_found:
                is_pass = 0
                message = "❌ 'Power' Class를 찾을 수 없습니다."
            elif failed_power_units:
                is_pass = 0
                message = f"❌ 일부 전원 공급 장치의 상태가 비정상('{upper_criteria}')입니다:\n" + "\n".join(failed_power_units)
            else:
                is_pass = 1
                message = f"✅ 모든 전원 공급 장치가 정상 상태입니다. (Debug: criteria='{upper_criteria}', last_status='{last_status}')"

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Juniper 전원 상태 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
