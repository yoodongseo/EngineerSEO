from .base_filter import BaseFilter, filter_result
import re

class JcmdFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "jcmd " in self.command:
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

    def linux_type1(self, stdout_data):
        try:
            is_success = 1
            output = stdout_data.strip()
            output_lower = output.lower()

            has_pid_header = bool(re.search(r'^\s*\d+\s*;\s*$', output, re.MULTILINE))
            has_xx_options = "-xx:" in output_lower

            if not output or (not has_pid_header and not has_xx_options):
                is_pass = 0
                message = "❌ 점검 필요: JVM 옵션 정보를 조회하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            has_heapdump_on_oom = "-xx:+heapdumponoutofmemoryerror" in output_lower
            heapdump_path_match = re.search(r'-XX:HeapDumpPath=([^\s]+)', output, re.IGNORECASE)
            heapdump_path = heapdump_path_match.group(1) if heapdump_path_match else ""
            has_heapdump_path = heapdump_path_match is not None and len(heapdump_path.strip()) > 0

            if has_heapdump_on_oom and has_heapdump_path:
                is_pass = 1
                message = (
                    "✅ 정상: Heap Dump 관련 JVM 옵션이 설정되어 있습니다.\n"
                    "- HeapDumpOnOutofMemoryError\n"
                    "  기준값: 필수\n"
                    "  출력값: 설정됨\n"
                    "- HeapDumpPath\n"
                    "  기준값: 필수\n"
                    f"  출력값: {heapdump_path}"
                )
            else:
                is_pass = 0
                message = (
                    "❌ 점검 필요: Heap Dump 관련 JVM 옵션이 누락되었습니다.\n"
                    "- HeapDumpOnOutOfMemoryError\n"
                    "  기준값: 필수\n"
                    f"  출력값: {'설정됨' if has_heapdump_on_oom else '미설정'}\n"
                    "- HeapDumpPath\n"
                    "  기준값: 필수\n"
                    f"  출력값: {heapdump_path if has_heapdump_path else '미설정'}\n"
                    "- 조치\n"
                    "  JVM 옵션 추가 후 서버 재기동이 필요합니다."
                )

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ jcmd VM.flags 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
