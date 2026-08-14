from .base_filter import BaseFilter, filter_result

class AlarmFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        # 'show ns events' 명령어를 기반으로 Citrix 장비로 가정
        if "show ns events" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
        else:
            is_success = 1
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria), # 지적해주신 내용 수정
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def citrix_type1(self, stdout_data):
        """grep 명령어의 출력 결과가 있는지 확인합니다."""
        try:
            is_success = 1
            
            # 출력이 비어있지 않으면(공백 제외), 알람이 발견된 것으로 간주
            if stdout_data and stdout_data.strip():
                is_pass = 0  # 불량
                message = f"❌ 오늘 날짜의 알람 이벤트가 발견되었습니다:\n{stdout_data.strip()}"
            else:
                is_pass = 1  # 정상
                message = "✅ 오늘 날짜의 알람 이벤트가 없습니다."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 알람 필터 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
