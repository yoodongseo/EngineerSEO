
from .base_filter import BaseFilter, filter_result

class RServiceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        try:
            output = stdout_data.strip().lower()
            is_disabled = True

            # 여러 줄일 수 있음 → 하나라도 disable이 아니면 취약
            for line in output.splitlines():
                if ("disable = no" in line) or ("enabled" in line and "disabled" not in line):
                    is_disabled = False
                    break

            if is_disabled:
                is_pass = 1
                result = "[U-21] r 계열 서비스 비활성화 상태"
                message = output
            else:
                is_pass = 0
                result = "[U-21] r 계열 서비스 활성화 상태"
                message = output

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"r 서비스 점검 실패: {str(e)}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }
