from .base_filter import BaseFilter, filter_result

class TimedatectlFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "timedatectl" in self.command:
            is_success, is_pass, result, message = self.linux_type1(stdout_data)
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

    def _extract_value(self, stdout_data, candidate_keys):
        for raw_line in stdout_data.splitlines():
            line = raw_line.strip()
            if not line or ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = " ".join(key.strip().lower().split())
            normalized_value = " ".join(value.strip().lower().split())
            for candidate_key in candidate_keys:
                if normalized_key == candidate_key:
                    return normalized_value
        return None

    def linux_type1(self, stdout_data):
        try:
            is_success = 1
            output_lower = stdout_data.lower()

            if "not found" in output_lower or "no such file or directory" in output_lower:
                is_pass = 0
                message = "❌ 점검 필요: timedatectl 명령어가 없습니다"
                result = message
                return is_success, is_pass, result, message

            sync_value = self._extract_value(stdout_data, ["system clock synchronized", "ntp synchronized"])
            ntp_value = self._extract_value(stdout_data, ["ntp service", "ntp enabled"])

            sync_ok = sync_value == "yes"
            ntp_ok = ntp_value in ["active", "yes"]

            detail = (
                "- 점검 항목: 동기화 상태\n"
                f" 출력값: {sync_value if sync_value is not None else '미검출'}\n"
                "  기준값: yes\n"
                "- 점검 항목: 서비스 상태\n"
                f"-  출력값: {ntp_value if ntp_value is not None else '미검출'}\n"
                "  기준값: active 또는 yes"
            )

            if sync_ok and ntp_ok:
                is_pass = 1
                message = "✅ 정상: timedatectl NTP 동기화 상태가 정상입니다.\n" + detail
            else:
                is_pass = 0
                message = "❌ 점검 필요: timedatectl NTP 동기화 상태 점검 필요\n" + detail

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ timedatectl NTP 상태 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
