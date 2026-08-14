class DiskFilter:
    def __init__(self, params):
        self.cmd_id = params.get('cmd_id')
        self.host = params.get('host')
        self.host_name = params.get('host_name')
        self.name = params.get('name')
        self.command = params.get('command')
        self.report_type = params.get('report_type')
        self.system = params.get('system')
        self.inspection_criteria = float(params.get('inspection_criteria'))
        self.file_path = ""

    def evaluate(self, stdout_data):
        try:
            lines = stdout_data.strip().splitlines()
            
            # sar 명령어 출력인지 확인
            if any(keyword in lines[0] for keyword in ['Linux', 'Average', 'sar']):
                # sar 출력 처리
                warnings = self._parse_sar_output(lines)
            else:
                # 기존 df 명령어 출력 처리
                warnings = self._parse_df_output(lines)

            is_pass = 0 if warnings else 1
            is_success = 1

            result_msg = f"{stdout_data.strip()}\n\n"
            if warnings:
                result_msg += "❌ 디스크 점검 필요:\n" + "\n".join(f" - {w}" for w in warnings)
            else:
                result_msg += "✅ 디스크 사용량 정상"

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

    def _parse_df_output(self, lines):
        """df 명령어 출력에서 디스크 사용률 추출"""
        warnings = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6 and '%' in parts[4]:
                usage = float(parts[4].replace('%', ''))
                mount = parts[5]
                if usage >= self.inspection_criteria:
                    warnings.append(f"{mount}: {usage:.1f}% 사용 (기준 {self.inspection_criteria}% 초과)")
        return warnings

    def _parse_sar_output(self, lines):
        """sar 명령어 출력에서 디스크 I/O 정보 추출"""
        warnings = []
        # sar -d 출력에서 디스크별 I/O 통계 확인
        for line in lines:
            if 'Average:' in line or '평균:' in line:
                parts = line.split()
                if len(parts) >= 4:
                    device = parts[0]
                    # %util (디스크 사용률) 확인
                    if len(parts) >= 8:
                        try:
                            util = float(parts[7])
                            if util >= self.inspection_criteria:
                                warnings.append(f"{device}: I/O 사용률 {util:.1f}% (기준 {self.inspection_criteria}% 초과)")
                        except ValueError:
                            continue
        return warnings

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
            'result': f"{stdout.strip()}\n\n❌ 디스크 평가 실패: {err}"
        }
