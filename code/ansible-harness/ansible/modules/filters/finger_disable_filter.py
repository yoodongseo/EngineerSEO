
from .base_filter import BaseFilter, filter_result

class FingerServiceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        try:
            output = stdout_data.strip().lower()

            # 판단 조건: systemctl 결과든, xinetd 설정이든 포함 가능
            is_disabled = False

            if "disabled" in output or "disable = yes" in output:
                is_disabled = True

            if is_disabled:
                is_pass = 1
                result = "[U-19] finger 서비스 비활성화 상태"
                message = output
            else:
                is_pass = 0
                result = "[U-19] finger 서비스 활성화 상태"
                message = output

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"finger 서비스 점검 실패: {str(e)}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }
