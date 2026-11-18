from datetime import datetime, timedelta

from .base_filter import BaseFilter, filter_result

class InactiveAccountLockFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        try:
            lines = stdout_data.strip().splitlines()
            header_skipped = lines[1:] if "Username" in lines[0] else lines
            today = datetime.now()
            inactive_users = []

            for line in header_skipped:
                # 예시: root    pts/0        192.0.2.1     Fri Apr 19 14:22:33 +0900 2024
                parts = line.split()
                if len(parts) < 8:
                    continue

                username = parts[0]
                date_str = " ".join(parts[-6:])
                try:
                    last_login = datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
                except Exception:
                    continue

                days_inactive = (today - last_login.replace(tzinfo=None)).days
                if days_inactive > self.inspection_criteria:
                    inactive_users.append((username, days_inactive))

            if inactive_users:
                is_pass = 0
                result = f"[U-14] 미사용 계정 {len(inactive_users)}개 감지"
                message = "\n".join([f"{u} - {d}일 미사용" for u, d in inactive_users])
            else:
                is_pass = 1
                result = "[U-14] 장기 미사용 계정 없음"
                message = result

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"계정 점검 실패: {str(e)}"
            result = message

        # return {
        #     'cmd_id': self.cmd_id,
        #     'host': self.host,
        #     'host_name': self.host_name,
        #     'name': self.name,
        #     'command': self.command,
        #     'report_type': self.report_type,
        #     'system': self.system,
        #     'message': message,
        #     'inspection_criteria': str(self.inspection_criteria),
        #     'file_path': self.file_path,
        #     'is_pass': is_pass,
        #     'is_success': is_success,
        #     'result': result
        # }
        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }

