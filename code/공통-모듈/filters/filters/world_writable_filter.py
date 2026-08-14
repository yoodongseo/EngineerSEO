class WorldWritableFileFilter:
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
            # 파일 출력 줄만 필터링 (파일 정보는 '-', 디렉토리는 'd')
            file_lines = [line for line in lines if line.strip().startswith("-")]

            # world writable: others에 w가 포함됨
            world_writable_files = [
                line for line in file_lines if len(line) > 9 and line[8] == 'w'
            ]

            if world_writable_files:
                is_pass = 0
                result = f"[U-15] World Writable 파일 {len(world_writable_files)}개 발견"
                message = "\n".join(world_writable_files[:20])  # 너무 길면 최대 20개만 출력
            else:
                is_pass = 1
                result = "[U-15] World Writable 파일 없음"
                message = result

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"World Writable 점검 실패: {str(e)}"
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
