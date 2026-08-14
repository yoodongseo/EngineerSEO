from datetime import datetime, timedelta

class InactiveAccountLockFilter:
    def __init__(self, params):
        self.cmd_id = params.get('cmd_id')
        self.host = params.get('host')
        self.host_name = params.get('host_name')
        self.name = params.get('name')
        self.command = params.get('command')
        self.report_type = params.get('report_type')
        self.system = params.get('system')
        self.inspection_criteria = 90  # 기본 90일
        self.file_path = ""

    def evaluate(self, stdout_data):
        is_success = 1
        try:
            lines = stdout_data.strip().splitlines()
            header_skipped = lines[1:] if "Username" in lines[0] else lines
            today = datetime.now()
            inactive_users = []

            for line in header_skipped:
                # 예시: root    pts/0        192.0.2.10     Fri Apr 19 14:22:33 +0900 2024
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
            'cmd_id': cmd_id,
            'host': host,
            'host_name': hostname,
            'result': result,
            'message': message,
            'report_type': report_type,
            'system': system,
            'id': id,
            'inspection_criteria': inspection_criteria,
            'protocol': protocol,
            'name': name,
            'command': command,
            'file_path': file_path,
            'is_pass': is_passed,
            'is_success': is_success
        }

