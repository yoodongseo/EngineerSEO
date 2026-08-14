from .base_filter import BaseFilter, filter_result
import re

class OracleProcessLimitFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "oracle_ansible.sh" in self.command:
            is_success, is_pass, result, message = self.oracle_type1(stdout_data)
        else:
            is_pass = 0
            is_success = 0
            message = f"❌ 지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def oracle_type1(self, stdout_data):
        try:
            is_success = 1

            if not isinstance(self.inspection_criteria, dict):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 딕셔너리 형식이어야 합니다."
                result = message
                return is_success, is_pass, result, message

            if "min_max_processes" not in self.inspection_criteria or "max_usage_percentage" not in self.inspection_criteria:
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria에 min_max_processes, max_usage_percentage 키를 모두 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            min_max_processes = float(self.inspection_criteria["min_max_processes"])
            max_usage_percentage = float(self.inspection_criteria["max_usage_percentage"])

            number_tokens = re.findall(r'\d+\.\d+|\d+', stdout_data)
            if len(number_tokens) < 3:
                is_pass = 0
                message = "❌ 점검 필요: Max Processes / Current Sessions / Usage Percentage 값을 파싱하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            max_processes = int(float(number_tokens[0]))
            current_sessions = int(float(number_tokens[1]))
            usage_percentage = float(number_tokens[2])

            failed = []
            if max_processes <= min_max_processes:
                failed.append("Max Processes가 기준 이하입니다.")
            if current_sessions > max_processes:
                failed.append("Current Sessions가 Max Processes를 초과합니다.")
            if usage_percentage > max_usage_percentage:
                failed.append("Usage Percentage가 기준을 초과합니다.")

            detail = (
                "- Max Processes\n"
                f"  기준값: {min_max_processes:.0f} 초과\n"
                f"  출력값: {max_processes}\n"
                "- current_sessions\n"
                f"  기준값: Max Processes ({max_processes}) 이하\n"
                f"  출력값: {current_sessions}\n"
                "- usage_percentage\n"
                f"  기준값: {max_usage_percentage:.2f}% 이하\n"
                f"  출력값: {usage_percentage:.2f}%"
            )

            if failed:
                is_pass = 0
                message = "❌ 점검 필요: 프로세스 한도/세션/사용률 기준을 확인하세요.\n" + detail + "\n- 점검 항목: " + ", ".join(failed)
            else:
                is_pass = 1
                message = "✅ 정상: 프로세스 한도/세션/사용률이 기준 이내입니다.\n" + detail    

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 프로세스 한도 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
