from .base_filter import BaseFilter, filter_result
import re

class AixRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "lsdev -Cc adapter" in self.command:
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
        try:
            is_success = 1

            device_statuses = {}
            current_device = None

            for line in stdout_data.splitlines():
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                if stripped_line.startswith('[') and stripped_line.endswith(']'):
                    current_device = stripped_line[1:-1]
                    if current_device not in device_statuses:
                        device_statuses[current_device] = {'primary': [], 'backup': []}
                    continue

                if current_device:
                    if "Primary Adapter State:" in stripped_line:
                        parts = stripped_line.split(':')
                        if len(parts) > 1:
                            device_statuses[current_device]['primary'].append(parts[1].strip())
                    elif "Backup Adapter State:" in stripped_line:
                        parts = stripped_line.split(':')
                        if len(parts) > 1:
                            device_statuses[current_device]['backup'].append(parts[1].strip())

            failures = []

            for device, data in device_statuses.items():
                num_primary = len(data['primary'])
                num_backup = len(data['backup'])

                if num_primary > 0 and num_primary == num_backup:
                    for i in range(num_primary):
                        p_status = data['primary'][i]
                        b_status = data['backup'][i]

                        if p_status == self.inspection_criteria['primary'] and \
                           b_status == self.inspection_criteria['backup']:
                               failures.append(f"{device}: Primary Adapter는 '{p_status}' 이지만 Backup Adapter가 '{b_status}' 상태입니다.")
                               break

            if failures:
                is_pass = 0
                fail_summary = "\n- ".join(failures)
                message = f"❌ AIX 네트워크 이중화 상태 점검 필요:\n- {fail_summary}"
            else:
                is_pass = 1
                message = "✅ AIX 모든 네트워크 이중화 상태가 정상입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ AIX 네트워크 이중화 필터 처리 중 예외 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
