class LogFilter:
    def __init__(self, params):
        self.cmd_id = params.get('cmd_id')
        self.host = params.get('host')
        self.host_name = params.get('host_name')
        self.name = params.get('name')
        self.command = params.get('command')
        self.report_type = params.get('report_type')
        self.system = params.get('system')
        self.file_path = ""

        criteria = params.get('inspection_criteria', [])
        if isinstance(criteria, str):
            self.inspection_criteria = [x.strip().lower() for x in criteria.split(',')]
        else:
            self.inspection_criteria = [x.lower() for x in criteria]

    def evaluate(self, stdout_data):
        try:
            log_lines = stdout_data.strip().splitlines()
            lower_lines = [line.lower() for line in log_lines]

            matched_lines = []
            for keyword in self.inspection_criteria:
                for original, lower in zip(log_lines, lower_lines):
                    if keyword in lower:
                        matched_lines.append(original)

            is_pass = 0 if matched_lines else 1
            is_success = 1

            result_msg = f"{stdout_data.strip()}\n\n"
            result_msg += (
                f"✅ 로그 점검 통과"
                if is_pass else
                f"❌ 위험 로그 발견 (키워드: {', '.join(self.inspection_criteria)}):\n" + "\n".join(matched_lines)
            )

            return {
                'cmd_id': self.cmd_id,
                'host': self.host,
                'host_name': self.host_name,
                'name': self.name,
                'command': self.command,
                'report_type': self.report_type,
                'system': self.system,
                'message': self.name,
                'inspection_criteria': self.inspection_criteria,
                'file_path': self.file_path,
                'is_pass': is_pass,
                'is_success': is_success,
                'result': result_msg
            }
        except Exception as e:
            return self._fail(str(e), stdout_data)

    def _fail(self, err, stdout):
        return {
            'cmd_id': self.cmd_id,
            'host': self.host,
            'host_name': self.host_name,
            'name': self.name,
            'command': self.command,
            'report_type': self.report_type,
            'system': self.system,
            'message': self.name,
            'inspection_criteria': self.inspection_criteria,
            'file_path': self.file_path,
            'is_pass': 0,
            'is_success': 0,
            'result': f"{stdout.strip()}\n\n❌ 로그 평가 실패: {err}"
        }
