
from .base_filter import BaseFilter, filter_result

class SUIDSGIDFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        try:
            lines = stdout_data.strip().splitlines()

            # SUID/SGID 파일 존재 여부 판단
            target_lines = [line for line in lines if line.startswith(("-", "d"))]
            count = len(target_lines)

            # 존재하면 취약 (일괄적으로 보고)
            if count > 0:
                is_pass = 0
                result = f"[U-13] SUID/SGID 설정 파일 {count}개 존재"
                message = "\n".join(target_lines[:20])  # 최대 20개만 표시
            else:
                is_pass = 1
                result = "[U-13] SUID/SGID 설정 파일 없음"
                message = result
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"SUID/SGID 점검 실패: {str(e)}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }
