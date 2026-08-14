class SUIDSGIDFilter:
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

            # SUID/SGID 파일 존재 여부 판단
            target_lines = [line for line in lines if line.startswith(("-", "d"))]
            count = len(target_lines)

            # 존재하면 취약 (일괄적으로 보고)
            if count > 0:
                is_pass = 0
                result = f"[U-13] SUID/SGID 설정 파일 {count}개 존재"
                message = "\n".join(target_lines[:20])  # 최대 20개만 표시
            else:
                is_pass = 1
                result = "[U-13] SUID/SGID 설정 파일 없음"
                message = result
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"SUID/SGID 점검 실패: {str(e)}"
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
