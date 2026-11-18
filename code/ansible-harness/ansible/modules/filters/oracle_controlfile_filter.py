from .base_filter import BaseFilter, filter_result
import re

class OracleControlfileFilter(BaseFilter):
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

            path_pattern = re.compile(r'^\s*([+/][^\s]+controlfile[^\s]*)\s*$')
            paths = []
            invalid_lines = []
            status_tokens = []

            for raw_line in stdout_data.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                match = path_pattern.match(raw_line)
                if match:
                    paths.append(match.group(1))

                upper_line = line.upper()
                if "INVALID" in upper_line:
                    invalid_linnes.append(line)
                    status_tokens.append("INVALID")
                elif "CURRENT" in upper_line:
                    status_tokens.append("CURRENT")

            unique_paths = sorted(set(paths))
            has_invalid = len(invalid_lines) > 0
            has_current = any(token == "CURRENT" for token in status_tokens)

            if len(unique_paths) < 2:
                is_pass = 0
                message = (
                    "❌ 점검 필요: 컨트롤 파일 이중화 구성이 확인되지 않습니다.\n"
                    f"- 감지된 경로 수: {len(unique_paths)}\n"
                    f"- 감지된 경로: {', '.join(unique_paths) if unique_paths else '없음'}"
                )
                result = message
                return is_success, is_pass, result, message

            if has_invalid:
                is_pass = 0
                message = (
                    "❌ 점검 필요: INVALID 상태의 컨트롤 파일이 감지되었습니다.\n"
                    f"- 감지된 경로 수: {len(unique_paths)}\n"
                    f"- 감지된 경로: {', '.join(unique_paths)}\n"
                    "- INVALID 감지 라인:\n"
                    + "\n".join([f"  {line}" for line in invalid_lines])
                )
                result = message
                return is_success, is_pass, result, message

            current_info = "감지됨" if has_current else "미검출(출력 포맷상 생략 가능)"
            is_pass = 1
            message = (
                "✅ 정상: 서로 다른 2개 이상의 컨트롤 파일 경로가 확인되었고 INVALID 상태가 없습니다.\n"
                f"- STATUS CURRENT: {current_info}\n"
                f"- 감지된 경로 수: {len(unique_paths)}\n"
                f"- 감지된 경로: {', '.join(unique_paths)}"
            )
            
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 이중화 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
