from .base_filter import BaseFilter, filter_result
import re

class OracleRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "STANDBY" in self.command:
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
            output = stdout_data.strip()
            output_lower = output.lower()

            if "no rows selected" in output_lower:
                is_pass = 1
                message = "✅ 정상: 이중화 미구성 상태입니다."
                result = message
                return is_success, is_pass, result, message

            status_values = []
            error_lines = []

            for line in stdout_data.slitlines():
                stripped = line.strip()
                if not stripped:
                    continue

                upper_line = stripped.upper()
                if "DEESTINATION" in upper_line and "STATUS" in upper_line and "ERROR" in upper_line:
                    continue

                if re.search(r'\bVALID\b', uppper_line):
                    status_values.append("VALID")
                if re.search(r'\bERROR\b', upper_line):
                    status_values.append("ERROR")
                    error_lines.append(stripped)
                    continue

                if "VALID" in upper_line and ("ORA-" in upper_line or "ERROR" in upper_line):
                    error_lines.append(stripped)

            if not status_values and not error_lines:
                is_pass = 0
                message = "❌ 점검 필요: 이중화 구성 결과를 파싱하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            has_error_status = any(v == "ERROR" for v in status_values)
            has_non_valid_status = any(v != "VALID" for v in status_values)

            if has_error_status or has_non_valid_status or error_lines:
                is_pass = 0
                detail_lines = []
                if status_values:
                    detail_lines.append(f"- STATUS 출력값: {', '.join(status_values)}")
                if error_lines:
                    detail_lines.append("- ERROR 감지 라인:")
                    detail_lines.extend([f" {line}" for line in error_lines])
                message = "❌ 점검 필요: 이중화 상태를 확인하세요.\n" + "\n".join(detail_lines)
            else:
                is_pass = 1
                message = "✅ 정상: 이중화 STATUS가 VALID이며 ERROR가 없습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 이중화 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
