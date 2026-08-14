from .base_filter import BaseFilter, filter_result
import re

class OracleSgaFilter(BaseFilter):
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

    def _to_bytes(self, value_text):
        text = str(value_text).strip().upper()
        match = re.match(r'^(\d+(?:\.\d+)?)([KMGTP]?)$', text)
        if not match:
            return None
        number = float(match.group(1))
        unit = match.group(2)
        unit_scale = {
            '': 1,
            'K': 1024,
            'M': 1024 ** 2,
            'G': 1024 ** 3,
            'T': 1024 ** 4,
            'P': 1024 ** 5,
        }
        return int(number * unit_scale[unit])

    def oracle_type1(self, stdout_data):
        try:
            is_success = 1

            if isinstance(self.inspection_criteria, bool) or not isinstance(self.inspection_criteria, (int, float)):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(FB 상환)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            max_gb = float(self.inspection_criteria)
            max_bytes = int(max_gb * (1024 ** 3))

            sga_target_raw = None
            sga_max_raw = None

            for line in stdout_data.splitlines():
                parts = line.split()
                if len(parts) < 3:
                    continue
                name = parts[0].strip().lower()
                value = parts[-1].strip()

                if name == "sga_target":
                    sga_target_raw = value
                elif name == "sga_max_size":
                    sga_max_raw = value

            if sga_target_raw is None or sga_max_raw is None:
                is_pass = 0
                message = "❌ 점검 필요: sga_target 또는 sga_max_size 값을 찾지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            target_bytes = self._to_bytes(sga_target_raw)
            max_size_bytes = self._to_bytes(sga_max_raw)
            if target_bytes is None or max_size_bytes is None:
                is_pass = 0
                message = "❌ 점검 필요: SGA 값을 숫자로 변환하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            failed = []
            if target_bytes > max_size_bytes:
                failed_append(f"sga_target 현재값({sga_target_raw})  sga_max_size 현재값({sga_max_raw})보다 큽니다.")
            if max_size_bytes > max_bytes:
                failed.append(f"sga_max_size 현재값({sga_target_raw})이 기준값({max_gb:.2f}G)를 초과합니다.")

            detail = (
                "- sga_target\n"
                f"  출력값: {sga_target_raw}\n"
                "- sga_max_size\n"
                f"  출력값: {sga_max_raw}\n"
                "- 기준\n"
                "  sga_target <= sga_max_size\n"
                f"  sga_max_size <= {max_gb:.2f}G"
            )

            if failed:
                is_pass = 0
                message = "❌ 점검 필요: SGA 파라미터 기준을 확인하세요.\n" + detail + "\n- 점검 항목: " + ", ".join(failed)
            else:
                is_pass = 1
                message = "✅ 정상: SGA 파라미터가 기준 이내입니다.\n" + detail

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle SGA 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
