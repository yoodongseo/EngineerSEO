from .base_filter import BaseFilter, filter_result
import re

class OracleTablespaceFilter(BaseFilter):
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

            if isinstance(self.inspection_criteria, bool):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(사용률 %)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message
            
            try:
                threshold = float(self.inspection_criteria)
            except Exception:
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(사용률 %)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            rows = []
            for raw_line in stdout_data.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                upper_line = line.upper()

                if "TABLESPACE_NAME" in upper_line and "USAGE_PERCENT" in upper_line:
                    continue
                if upper_line.endswith("ROWS SELECTED."):
                    continue
                if set(line) <= {"-", "_"}:
                    continue

#                match = re.match(r'^([A-Za-z0-9_$#]+)\s+(\d+(?:\.\d+)$', line)
#                if match:
#                    name = match.group(1)
#                    usage = float(match.group(2))
#                    rows.append((name, usage))

                parts = line.split()
                if len(parts) < 2:
                    continue

                name = parts[0].strip()
                usage_text = parts[-1].strip()
                if usage_text.startswith("."):
                    usage_text = "0" + usage_text

                try:
                    usage = float(usage_text)
                except Exception:
                    continue

                if set(name) <= {"-", "_"}:
                    continue
                rows.append((name, usage))

            if not rows:
                is_pass = 0
                message = "❌ 점검 필요: 테이블스페이스 사용률 데이터를 파싱하지 못 했습니다"
                result = message
                return is_success, is_pass, result, message

            exceeded = [(name, usage) for name, usage in rows if usage > threshold]

            if exceeded:
                is_pass = 0
                detail = ", ".join([f"{name}={usage:.2f}%" for name, usage in exceeded])
                message = (
                    "❌ 점검 필요: 테이블스페이스 사용률이 기준값을 초과했습니다.\n"
                    f"- 기준값: {threshold:.2f}%\n"
                    f"- 초과 항목: {detail}"
                )
            else:
                is_pass = 1
                message = (
                    "✅ 정상: 모든 테이블스페이스 사용률이 기준값 이내입니다.\n"
                    f"- 기준값: {threshold:.2f}%\n"
                    f"- 점검 건수: {len(rows)}"
                )

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 테이블스페이스  평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
