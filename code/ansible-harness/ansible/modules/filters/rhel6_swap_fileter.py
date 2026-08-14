from .base_filter import BaseFilter, filter_result
import re

class Rhel6SwapFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "swapon -s" in self.command:
            is_success, is_pass, result, message = self.swapon_type1(stdout_data)
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

    def swapon_type1(self, stdout_data):
        try:
            is_success = 1
            lines = stdout_data.strip().splitlines()
            failures = []

            try:
                criteria = float(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = "❌ 설정 오류: inspection_criteria가 유효한 숫자(임계값)여야 합니다."
                result = message
                return is_success, is_pass, result, message

            if not lines or len(lines) < 2:
                is_pass = 0
                message = "❌ 'swapon -s' 출력에 스왑 정보가 부족합니다."
                result = message
                return is_success, is_pass, result, message

            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    filename = parts[0]
                    try:
                        size_kb = int(parts[2])
                        used_kb = int(parts[3])

                        if size_kb == 0:
                            usage_percent = 0.0
                        else:
                            usage_percent = (used_kb / size_kb) * 100.0

                        if usage_percent > criteria:
                            failures.append(
                                    f"스왑 {filename} 사용률: {usage_percent:.2f}% (할당: {size_kb}KB, 사용: {used_kb}KB) 이 기준치({criteria:.2f}%)를 초과햇습니다."
                            )
                    except ValueError:
                        continue

                if failures:
                    is_pass = 0
                    message = "❌ 스왑 사용량 점검 실패:\n" + "\n".join(failures)
                else:
                    is_pass = 1
                    message = f"✅ 모든 스왑 영역의 사용량이 기준치({criteria:.2f}%) 이하입니다."

                result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Memory Swap 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
