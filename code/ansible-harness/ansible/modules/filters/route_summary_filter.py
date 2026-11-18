from .base_filter import BaseFilter, filter_result

class RouteSummaryFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        명령어 결과를 확인하여 데이터 존재 유무만 판단합니다.
        """
        is_success = 1
        message = ""
        
        if "show route summary" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
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
        """'show route summary' 명령어 출력에서 'Router ID:'의 존재 여부만 확인합니다."""
        try:
            is_success = 1
            
            if "Router ID:" in stdout_data:
                is_pass = 1
                message = "✅ 라우팅 요약 정보가 존재합니다."
            else:
                is_pass = 0
                message = "❌ 라우팅 요약 정보가 존재하지 않습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 라우팅 요약 정보 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
