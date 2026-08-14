from .base_filter import BaseFilter, filter_result
import re

class AixPingLossFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        if "ping -c" in self.command:
            is_success, is_pass, result, message = self.ping_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }

    def ping_type1(self, stdout_data):
        is_success = 1
        try:
            packet_loss_line = None
            for line in stdout_data.splitlines():
                if "packet loss" in line:
                    packet_loss_line = line
                    break

            if packet_loss_line is None:
                is_pass = 0
                message = "❌ Ping 출력에서 'packet loss' 라인을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            match = re.search(r'(\d+)% packet loss', packet_loss_line)
            if not match:
                is_pass = 0
                message = f"❌ 'packet loss' 라인에서 손실률(%)을 파싱할 수 없습니다: '{packet_loss_line}'"
                result = message
                return is_success, is_pass, result, message

            actual_loss = int(match.group(1))

            if actual_loss > 0:
                is_pass = 0
                message = f"❌ Ping 실패: 패킷 손실률이 {actual_loss}% 입니다."
            else:
                is_pass = 1
                message = f"✅ Ping 정상: 패킷 손실률 0%."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ PING 상태 평가 실패: {str(e)}"
            result = message
        return is_success, is_pass, result, message
