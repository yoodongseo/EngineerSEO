from .base_filter import BaseFilter, filter_result

class OracleAccessFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "oracle_ansible.sh" in self.command:
            is_success, is_pass, result, message = self.access_type1(stdout_data)
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

    def access_type1(self, stdout_data):
        try:
            is_success = 1
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]
            has_access_line = any(line == "DB is accessible" for line in lines)

            if has_access_line:
                is_pass = 1
                message = "✅ 정상: DB 접근 가능 상태를 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 점검 필요: DB 접근 가능 결과('DB is accessible')가 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 접근성 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
