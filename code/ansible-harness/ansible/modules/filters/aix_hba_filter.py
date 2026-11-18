from .base_filter import BaseFilter, filter_result
import re

class AixHbaFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "fcstat" in self.command:
            is_success, is_pass, result, message = self._aix_type1(stdout_data)
        else:
            is_success = 0
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

    def _aix_type1(self, stdout_data):
        is_success = 1

        try:
            if not self.inspection_criteria or not isinstance(self.inspection_criteria, str):
                is_pass = 0
                message = f"❌ inspection_criteria가 유효한 문자열(정상 상태 값)이 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            blocks = re.split(r'(\[fcs\d+\])', stdout_data)
            if not blocks or len(blocks) <= 1:
                is_pass = 0
                message = "❌ 출력에서 HBA 장치 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            failures = []

            for i in range(1, len(blocks), 2):
                device_name = blocks[i].strip()
                device_info = blocks[i+1].strip() if (i + 1) < len(blocks) else ""
                full_block = f"{device_name}\n{device_info}"

                if "Error opening device" in device_info:
                    failures.append(full_block)
                    continue

                attention_type = None
                attention_type_found = False
                for line in device_info.splitlines():
                    if "Attention Type:" in line:
                        attention_type_found = True
                        parts = line.split(':', 1)
                        if len(parts) > 1:
                            attention_type = parts[1].strip()
                        break

                if attention_type_found and attention_type != self.inspection_criteria:
                    failures.append(full_block)
                elif not attention_type_found and device_info:
                    failures.append(f"{full_block}\n(점검 실패: 'Attention Type' 라인을 찾을 수 없음)")

            if failures:
                is_pass = 0
                fail_summary = "\n\n".join(failures)
                message = f"❌ HBA 연결 상태 점검 실패:\n{fail_summary}"
            else:
                is_pass = 1
                message = f"✅ 모든 HBA 연결이 정상 상태('{self.inspection_criteria}') 입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ AIX HBA 필터 처리 중 예외 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
