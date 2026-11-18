from .base_filter import BaseFilter, filter_result

class StatFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "stat " in self.command:
            is_success, is_pass, result, message = self.linux_type1(stdout_data)
        elif "ls -ltr" in self.command:
            is_success, is_pass, result, message = self.linux_type2(stdout_data)
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

    def linux_type1(self, stdout_data):
        try:
            is_success = 1
             
            lines = stdout_data.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            has_file_header = any(line.strip().startswith("File:") for line in non_empty_lines)

            if non_empty_lines and has_file_header:
                is_pass = 1
                message = "✅ 정상: stat 파일 상태 정보를 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 점검 필요: stat 파일 상태 정보가 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ stat 파일 상태 정보 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def linux_type2(self, stdout_data):
        try:
            is_success = 1
             
            lines = stdout_data.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]

            if non_empty_lines:
                is_pass = 1
                message = "✅ 정상: 파일 상태 정보를 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 점검 필요: 파일 상태 정보가 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ ls 파일 상태 정보 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
