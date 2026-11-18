from .base_filter import BaseFilter, filter_result
from collections import Counter

class DuplicateCheckFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        명령어 결과를 받아 중복 검사를 수행합니다.
        """
        is_success, is_pass, result, message = self.check_duplicates(stdout_data)

        return {
            'message': message,
            'inspection_criteria': "각 라인의 중복 없음",
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def check_duplicates(self, stdout_data):
        """
        입력 데이터에서 각 줄의 중복 여부를 확인하고 결과를 반환합니다.
        """
        try:
            is_success = 1
            lines = [line.strip() for line in stdout_data.strip().splitlines() if line.strip()]
            
            if not lines:
                is_pass = 0
                message = "❌ 점검할 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            line_counts = Counter(lines)
            
            duplicates = {line for line, count in line_counts.items() if count > 1}

            if duplicates:
                is_pass = 0
                duplicate_messages = ["❌ 중복된 항목이 발견되었습니다:"]
                for line in sorted(list(duplicates)): # 중복 라인을 정렬하여 추가
                    duplicate_messages.append(f"- {line}")
                message = "\n".join(duplicate_messages)
            else:
                is_pass = 1
                message = "✅ 중복된 항목이 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 중복 값 검사 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
