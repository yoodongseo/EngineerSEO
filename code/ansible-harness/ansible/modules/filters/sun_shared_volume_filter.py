from .base_filter import BaseFilter, filter_result
import re

class SunSharedVolumeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "mount" in self.command:
            is_success, is_pass, result, message = self.mount_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def mount_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_lines = []

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ 'inspection_criteria'가 유효한 문자열이 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            shared_path = self.inspection_criteria.strip()
            
            lines = stdout_data.splitlines()

            matched_lines = []
            for line in lines:
                if f" on {shared_path} " in line:
                    matched_lines.append(line.strip())

            if not matched_lines:
                message = f"✅mount 경로에 '{shared_path}'을(를) 포함하는 점검 대상 공유 볼륨이 없습니다."
                result = message
                return is_success, is_pass, result, message

            for mline in matched_lines:
                if "(" in mline and ")" in mline:
                    opts = mline.split("(", 1)[-1].rsplit(")", 1)[0].lower()
                else:
                    is_pass = 0
                    message_lines.append(f"❌ {shared_path}: mount 옵션 파싱 실패({mline})")
                    continue

                opt_tokens = [o.strip() for o in opts.split(",")]

                if "read/only" in opt_tokens:
                    is_pass = 0
                    message_lines.append(f"❌{shared_path}: Read-only(ro)로 마운트 상태 ({opts})")
                elif "read/write" in opt_tokens:
                    pass
                else:
                    is_pass = 0
                    message_lines.append(f"❌{shared_path}: rw/ro 옵션 확인 불가 ({opts})")

            if is_pass == 1:
                message = f"✅공유 볼륨 상태 정상"
            else:
                message = "\n".join(message_list)
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"공유 볼륨 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
