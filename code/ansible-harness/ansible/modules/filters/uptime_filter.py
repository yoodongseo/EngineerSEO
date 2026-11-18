from .base_filter import BaseFilter, filter_result
import re
from datetime import datetime, timedelta
import locale

class UptimeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        'show system uptime' 또는 'show ns stat' 명령어 결과를 파싱하여 시스템 업타임을 확인합니다.
        """
        is_success = 1
        message = ""
        
        if "show system uptime" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "show ns stat" in self.command:
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

    def juniper_type1(self, stdout_data):
        """'show system uptime' 출력에서 시스템 업타임을 파싱하여 inspection_criteria에 설정된 일수 이상인지 확인합니다."""
        try:
            is_success = 1
            uptime_days = 0
            
            # inspection_criteria 유효성 검사 및 변환
            if not self.inspection_criteria:
                is_pass = 0
                is_success = 0
                message = "❌ 점검 기준(inspection_criteria)이 설정되지 않았습니다."
                result = message
                return is_success, is_pass, result, message
            
            try:
                threshold_days = int(self.inspection_criteria)
            except ValueError:
                is_pass = 0
                is_success = 0
                message = f"❌ 점검 기준(inspection_criteria) '{self.inspection_criteria}'이(가) 유효한 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            # 전체 stdout_data에서 업타임 정보를 추출합니다.
            match = re.search(r'up (\d+)\s+days', stdout_data) # Search entire data
            if match:
                uptime_days = int(match.group(1))
            # 'days'가 발견되지 않으면 uptime_days는 0으로 유지되며, 이는 1일 미만인 경우에 해당합니다.

            if uptime_days >= threshold_days:
                is_pass = 1
                message = f"✅ 시스템 업타임이 {uptime_days}일로 정상입니다 ({threshold_days}일 이상)."
            else:
                is_pass = 0
                message = f"❌ 시스템 업타임이 {uptime_days}일로 확인이 필요합니다 ({threshold_days}일 미만)."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 업타임 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def citrix_type1(self, stdout_data):
        """'show ns stat' 출력에서 'Up since'를 파싱하여 업타임이 inspection_criteria에 설정된 일수보다 많은지 확인합니다."""
        try:
            is_success = 1
            
            # inspection_criteria 유효성 검사
            try:
                threshold_days = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                is_success = 0
                message = f"❌ 점검 기준(inspection_criteria) '{self.inspection_criteria}'이(가) 유효한 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            up_since_line = None
            for line in stdout_data.splitlines():
                if line.strip().startswith("Up since"):
                    up_since_line = line.strip()
                    break
            
            if not up_since_line:
                is_pass = 0
                message = "❌ 'Up since' 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            # 'Up since' 뒤의 날짜 문자열 추출 (앞뒤 공백 제거)
            date_str = up_since_line.replace("Up since", "").strip()
            
            original_locale = locale.getlocale()
            try:
                # 날짜 파싱을 위해 로케일을 영어권(C)으로 임시 변경
                locale.setlocale(locale.LC_TIME, 'C')
                up_since_time = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
            finally:
                # 원래 로케일로 복원
                locale.setlocale(locale.LC_TIME, original_locale)

            # 현재 시간과 비교
            uptime_delta = datetime.now() - up_since_time
            uptime_days = uptime_delta.days

            # "7일 이하면 비정상" -> uptime_days가 threshold_days(7)보다 커야 정상
            if uptime_days >= threshold_days:
                is_pass = 1
                message = f"✅ 시스템 업타임이 {uptime_days}일로 정상입니다 (기준: {threshold_days}일 이상)."
            else:
                is_pass = 0
                message = f"❌ 시스템 업타임이 {uptime_days}일로 확인이 필요합니다 (기준: {threshold_days}일 미만)."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 업타임 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
