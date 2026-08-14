from .base_filter import BaseFilter, filter_result
import re

class SunPingLossFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        if "ping" in self.command:
            is_success, is_pass, result, message = self.ping_type1(stdout_data)
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

    def ping_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []
            result = ""

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria.strip():
                is_pass = 0
                message = f"❌점검 기준이 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            ok_token = self.inspection_criteria.lower()

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌ ping 출력이 비어있습니다."
                result = message
                return is_success, is_pass, result, message

            low = stdout_data.lower()

            if "no answer" in low:
                is_pass = 0
                message = "❌ ping 응답 없음"
                result = message
                return is_success, is_pass, result, message

            if ok_token in low:
                message = f"✅ Ping 정상"
            else:
                is_pass = 0
                message = f"❌ Ping 결과 판단 불가: {stdout_data.strip()}"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ PING 상태 평가 실패: {str(e)}"
            result = message
        return is_success, is_pass, result, message
