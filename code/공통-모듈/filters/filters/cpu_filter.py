import re

class CPUFilter:
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
            lines = stdout_data.strip().split('\n')
            
            # sar 명령어 출력인지 확인 (첫 번째 줄에 "Linux" 또는 "Average" 포함)
            if any(keyword in lines[0] for keyword in ['Linux', 'Average', 'sar']):
                # sar 출력 처리
                usage = self._parse_sar_output(lines)
            else:
                # 기존 top 명령어 출력 처리
                usage = self._parse_top_output(lines[0])
            
            is_pass = 1 if usage < self.inspection_criteria else 0
            is_success = 1

            summary = (
                f"✅ CPU 사용률: {usage:.1f}% (기준 {self.inspection_criteria}%) 정상"
                if is_pass else
                f"❌ CPU 사용률: {usage:.1f}% (기준 {self.inspection_criteria}%) 초과"
            )

            result_msg = f"{stdout_data.strip()}\n\n{summary}"

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

    def _parse_top_output(self, line):
        """top 명령어 출력에서 CPU 사용률 추출"""
        values = re.findall(r"\d+\.\d+", line)
        user = float(values[0])
        system = float(values[1])
        return user + system

    def _parse_sar_output(self, lines):
        """sar 명령어 출력에서 CPU 사용률 추출"""
        # sar -u 출력에서 마지막 Average 라인 찾기
        for line in reversed(lines):
            if 'Average:' in line or '평균:' in line:
                parts = line.split()
                # sar -u 출력 형식: Average: CPU %user %nice %system %iowait %steal %idle
                if len(parts) >= 7:
                    user = float(parts[1])
                    system = float(parts[3])
                    return user + system
                break
        
        # Average 라인이 없으면 마지막 데이터 라인 사용
        for line in reversed(lines):
            if line.strip() and not line.startswith('Linux') and not line.startswith('sar'):
                parts = line.split()
                if len(parts) >= 4 and parts[0].replace('.', '').isdigit():
                    user = float(parts[1])
                    system = float(parts[3])
                    return user + system
        
        raise ValueError("sar 출력에서 CPU 사용률을 추출할 수 없습니다")

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
            'result': f"{stdout.strip()}\n\n❌ CPU 평가 실패: {err}"
        }
