class FingerServiceFilter:
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
            output = stdout_data.strip().lower()

            # 판단 조건: systemctl 결과든, xinetd 설정이든 포함 가능
            is_disabled = False

            if "disabled" in output or "disable = yes" in output:
                is_disabled = True

            if is_disabled:
                is_pass = 1
                result = "[U-19] finger 서비스 비활성화 상태"
                message = output
            else:
                is_pass = 0
                result = "[U-19] finger 서비스 활성화 상태"
                message = output

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"finger 서비스 점검 실패: {str(e)}"
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
