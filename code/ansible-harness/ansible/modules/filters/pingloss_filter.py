from .base_filter import BaseFilter, filter_result
import re

class PingLossFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        if "ping" in self.command:
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
        try:
            is_success = 1
            is_pass = 1
            message_list = []
            result = ""

            if isinstance(self.inspection_criteria, dict):
                max_loss = self.inspection_criteria.get('max_loss', 0)
                max_avg_rtt = self.inspection_criteria.get('max_avg_rtt', None)
            else:
                try:
                    max_loss = int(self.inspection_criteria)
                except (ValueError, TypeError):
                    max_loss = 0
                max_avg_rtt = None

            loss_percentage = -1
            loss_match = re.search(r'(\d+)% packet loss', stdout_data)

            if loss_match:
                loss_percentage = int(loss_match.group(1))
                if loss_percentage > max_loss:
                    is_pass = 0
                    message_list.append(f"❌패킷 손실률({loss_percentage})이 허용치({max_loss})를 초과했습니다.")
            else:
                if '100% packet loss' not in stdout_data:
                    is_pass = 0
                    message_list.append("❌ PING 결과에서 패킷 손실률 정보를 찾을 수 없습니다.")

            rtt_match = re.search(r'min/avg/max.=* ([\d.]+)/([\d.]+)/([\d.]+)', stdout_data, re.IGNORECASE)
            if rtt_match:
                rtt_min, rtt_avg, rtt_max = rtt_match.groups()
                if max_avg_rtt is not None and float(rtt_avg) > max_avg_rtt:
                    is_pass = 0
                    message_list.append(f"❌평균 응답 시간 ({rtt_avg}ms)이 허용치({max_avg_rtt}ms)를 초과했습니다.")
            elif loss_percentage < 100 and loss_percentage != -1:
                message_list.append("❌PING 결과에서 RTT(응답 시간) 정보를 찾을 수 없습니다.")

            if is_pass == 1:
                message = "✅PING 통신 상태가 정상입니다."
            else:
                message = "\n".join(message_list) if message_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ PING 상태 평가 실패: {str(e)}"
            result = message
        return is_success, is_pass, result, message
