from .base_filter import BaseFilter, filter_result
import re
import sys

class SunNetworkLinkFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""

        if "dladm" in self.command:
            is_success, is_pass, result, message = self.dladm_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        # # 현재 로직 상 명령어는 필터를 무조건 타야 하므로 단지 실행만 하고 반합하는 필터
        # is_success, is_pass, result, message = self.action(stdout_data)

        return {
            'message': result,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success
        }
    
    def dladm_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌점검 기준{inspection_criteria} 이(가) 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message
            
            if stdout_data and "not found" in stdout_data.lower() or "없음" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = f"❌ 명령어 실패: 명령어 출력이 비어있습니다."
                result = message
                return is_success, is_pass, result, message
            
            link_ok = str(self.inspection_criteria.get("link_ok", "up")).lower()
            duplex_ok = str(self.inspection_criteria.get("duplex_ok", "full")).lower()
            speed_min = int(self.inspection_criteria.get("speed_min_mbps", 1))

            low = stdout_data.lower()

            checked = 0

            for line in stdout_data.splitlines():
                s = line.strip()
                if not s:
                    continue

                iface = s.split()[0].strip()
                if not iface:
                    continue

                sl = s.lower()

                m_link = re.search(r"링크\s*[::]\s*(\w+)", sl)
                m_speed = re.search(r"속도\s*[::]\s*([0-9]+)", sl)
                m_duplex = re.search(r"이중\s*[::]\s*(\w+)", sl)

#                m_link = re.search(r"(?:링크|link)\s*(?:[::=])\s*([^\s]+)", sl, re.IGNORECASE)
#                m_speed = re.search(r"(?:속도|speed)\s*(?:[::=])\s*(([0-9]+)", sl, re.IGNORECASE)
#                m_duplex = re.search(r"(?:이중|duplex)\s*(?:[::=])\s*([^\s]+)", sl, re.IGNORECASE)

                if not (m_link and m_speed and m_duplex):
                    continue

                checked += 1
                link = m_link.group(1)
                speed = int(m_speed.group(1))
                duplex = m_duplex.group(1)

                if link != link_ok:
                    is_pass = 0
                    message_list.append(f"❌ {iface}: 링크={link} (기준{link_ok})")
                if duplex != duplex_ok:
                    is_pass = 0
                    message_list.append(f"❌ {iface}: 이중={duplex} (기준{duplex_ok})")
                if speed < speed_min:
                    is_pass = 0
                    message_list.append(f"❌ {iface}: 속도={speed}Mbps (기준: >= {speed_min}Mbps)")

            if checked == 0:
                is_pass = 0
                message = f"❌점검 가능한 NIC 라인을 찾지 못했습니다."
                result = message
                return is_success, is_pass, result, message

            if is_pass == 1:
                message = f"✅NW 링크 상태 정상: {checked}개 NIC 정상"
            else:
                message = "\n".join(message_list) if message_list else f"❌알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"
            
            result = message
        
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ fail action: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
