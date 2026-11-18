from .base_filter import BaseFilter, filter_result
import re

class FanFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        
        if "show chassis environment" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "stat system -detail" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
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
        """Juniper 'show chassis environment' 출력에서 Fan 상태 점검"""
        try:
            is_success = 1
            fan_section = False
            failed_fans = []
            known_statuses = ["OK", "FAILED", "CHECK", "ABSENT", "PRESENT"]

            for line in stdout_data.splitlines():
                if line.strip().startswith('Fans'):
                    fan_section = True
                    continue
                
                if fan_section and line.strip().startswith('Fan'):
                    parts = line.strip().split()
                    status = "UNKNOWN"

                    for part in parts:
                        if part.upper() in known_statuses:
                            status = part
                            break

                    if status.upper() != self.inspection_criteria.upper():
                        failed_fans.append(line.strip())
            
            if not fan_section:
                is_pass = 0
                message = "❌ Fan 정보를 찾을 수 없습니다."
                result = message
            elif failed_fans:
                is_pass = 0
                status_icon = "❌"
                message = f"{status_icon} 일부 팬에 문제가 있습니다: {', '.join(failed_fans)}"
                result = message
            else:
                is_pass = 1
                status_icon = "✅"
                message = f"{status_icon} 모든 팬이 정상 상태입니다."
                result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 팬 상태 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def citrix_type1(self, stdout_data):
        """Citrix 'stat system -detail' 출력에서 Fan 상태를 점검합니다."""
        try:
            is_success = 1
            failed_fans = []
            fan_lines_found = False

            # inspection_criteria를 항상 리스트 형태로 처리
            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(c).upper() for c in self.inspection_criteria]
            else:
                criteria_string = str(self.inspection_criteria)
                criteria_list = [c.strip().upper() for c in criteria_string.split(',')]

            for line in stdout_data.strip().splitlines():
                stripped_line = line.strip()
                if stripped_line.startswith("Fan") and "Speed (RPM)" in stripped_line:
                    fan_lines_found = True
                    parts = stripped_line.split()
                    try:
                        # RPM 값을 문자열로 가져옴
                        rpm_value_str = parts[-1].upper()
                        if rpm_value_str in criteria_list:
                            failed_fans.append(stripped_line)
                    except IndexError:
                        # RPM 값을 파싱할 수 없는 경우 실패로 간주
                        failed_fans.append(f"{stripped_line} (RPM 값 없음)")

            if not fan_lines_found:
                is_pass = 0
                message = "❌ 'Fan' 정보를 찾을 수 없습니다."
            elif failed_fans:
                is_pass = 0
                criteria_str = str(self.inspection_criteria)
                message = f"❌ 일부 팬의 RPM 값이 비정상 기준('{criteria_str}')과 일치합니다:\n" + "\n".join(failed_fans)
            else:
                is_pass = 1
                message = f"✅ 모든 팬이 정상 상태입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Citrix 팬 상태 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message