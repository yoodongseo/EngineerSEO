class PathFilter:
    def __init__(self, params):
        self.cmd_id = params.get('cmd_id')
        self.host = params.get('host')
        self.host_name = params.get('host_name')
        self.name = params.get('name')
        self.command = params.get('command')
        self.report_type = params.get('report_type')
        self.system = params.get('system')
        self.inspection_criteria = params.get('inspection_criteria')
        self.file_path = ""

    def evaluate(self, stdout_data):
        is_success = 1
        try:
            lines = stdout_data.strip().splitlines()
            path_line = next((line for line in lines if "PATH=" in line or line.startswith("/")), "")
            path_str = path_line.split('=')[-1] if "=" in path_line else path_line
            path_str = path_str.strip()

            # "." 또는 "::"가 PATH 문자열의 맨 앞이나 중간에 포함되어 있는지 검사
            is_bad_path = (
                path_str.startswith(".:") or
                ":.:" in path_str or
                ":." in path_str and not path_str.endswith(":.") or
                "::" in path_str
            )

            is_pass = 0 if is_bad_path else 1
            message = f"PATH 설정: {path_str}"
            result = "취약" if is_bad_path else "양호"

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"PATH 점검 실패: {str(e)}"
            result = message

        return {
            'cmd_id': self.cmd_id,
            'host': self.host,
            'host_name': self.host_name,
            'name': self.name,
            'command': self.command,
            'report_type': self.report_type,
            'system': self.system,
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'file_path': self.file_path,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }