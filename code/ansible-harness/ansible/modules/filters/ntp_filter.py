from .base_filter import BaseFilter, filter_result

class NtpFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        is_pass = 1  # Default to pass
        message = ""
        result = ""

        try:
            lines = stdout_data.strip().splitlines()
            # Skip header lines
            data_lines = lines[2:]

            if not data_lines:
                is_pass = 0
                message = "❌ NTP 동기화 정보가 없습니다."
                result = message
            else:
                failing_offsets = []
                for line in data_lines:
                    parts = line.split()
                    if len(parts) >= 9:
                        try:
                            offset = float(parts[-2])
                            if abs(offset) > 1000:
                                is_pass = 0
                                failing_offsets.append(f"remote: {parts[0]}, offset: {offset}")
                        except (ValueError, IndexError):
                            continue # Skip lines that don't parse correctly
                
                if is_pass:
                    message = "✅ NTP offset이 모두 정상 범위입니다."
                    result = message
                else:
                    message = f"❌ NTP offset이 기준값을 초과했습니다: {', '.join(failing_offsets)}"
                    result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ NTP 평가 실패: {str(e)}"
            result = message

        return {
            'message': message,
            'inspection_criteria': "offset <= 1000",
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }
