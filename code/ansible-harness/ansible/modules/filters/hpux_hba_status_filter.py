from .base_filter import BaseFilter, filter_result
import re

class HPUXHbaStatusFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "fcmsutil" in self.command:
            is_success, is_pass, result, message = self.fcmsutil_hba_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def fcmsutil_hba_type1(self, stdout_data):
        try:
            is_success = 1
            message_list = []
            is_pass = 1

            ok_states = ["ONLINE", "LINK_UP"]
            if isinstance(self.inspection_criteria, list):
                ok_states = [str(item).upper() for item in self.inspection_criteria]

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "Link Speed" not in stdout_data:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Link Speed' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
  
            ports = []
            cur = None

            for raw in lines:
                line = raw.strip()
                if not line:
                    continue

                if re.search(r"^Link\s*Speed\s*=", line, re.IGNORECASE):
                    if cur is not None:
                        ports.append(cur)

                    cur = {
                        "link_speed_raw": line,
                        "link_speed_gb": None, 
                        "port_name": None, 
                        "driver_state": None,
                    }
                  
                    if "UNKNOWN" in line.upper():
                        cur["link_speed_unknown"] = True
                    else:
                      m = re.search(r"=\s*([0-9]+(?:\.[0-9]+)?)\s*G", line, re.IGNORECASE)
                      if m:
                          try:
                              cur["link_speed_gb"] = float(m.group(1))
                          except Exception:
                              cur["link_speed_gb"] = None
                    continue

                if cur is None:
                    cur = {"link_speed_raw": None, "link_speed_gb": None, "port_name": None, "driver_state": None}

                if re.search(r"Port\s*Name\s*=", line, re.IGNORECASE):
                    cur["port_name"] = line.split("=", 1)[-1].strip()
                    continue

                if re.search(r"Driver\s*state\s*=", line, re.IGNORECASE):
                    cur["driver_state"] = line.split("=", 1)[-1].strip()
                    continue

            if cur is not None:
                ports.append(cur)

            has_any_speed_line = any(p.get("link_speed_raw") for p in ports)
            if not ports or not has_any_speed_line:
                is_pass = 0
                message = "HBA 출력 파싱 실패: Link Speed 블록이 없습니다."
                result = message
                return is_success, is_pass, result, message

            ok_count = 0
            total_count = len(ports)

            for idx, p in enumerate(ports, start=1):
                port_name = p["port_name"] or f"port#{idx}"
                driver_state_raw = p["driver_state"] or ""
                driver_state = driver_state_raw.upper()
                speed_gb = p.get("link_speed_gb")
                speed_unknown = p.get("link_speed_unknown", False)

                state_ok = bool(driver_state_raw) and any(s.upper() in driver_state for s in ok_states)

                speed_ok = (speed_gb is not None) and (speed_gb != 0) and not speed_unknown

                if state_ok and speed_ok:
                    ok_count += 1
                else:
                    is_pass = 0
                    reasons = []

                    if not driver_state_raw:
                        reasons.append(f"Driver state 미출력")
                    elif not state_ok:
                        reasons.append(f"Driver state 비정상({dirver_state_raw})")
                    
                    if speed_unknown:
                        reasons.append(f"Link Speed=UNKNWON")
                    elif speed_gb is None:
                        reasons.append(f"Link Speed 미출력/파싱불가")
                    elif speed_gb == 0:
                        reasons.append("Link Speed = 0")

                    message_list.append(f"❌ {port_name}:" + ", ".join(reasons))

            if is_pass == 1:
                message = f"✅모든 HBA 포트의 상태가 정상입니다."

            else:
                header = f"HBA 연결 비정상: {ok_count}/{total_count} 포트 정상"
                details = "\n".join(message_list) if message_list else f"(출력값:{str(stdout_data).strip()[:200]}...)"
                message = header + "\n" + details

            result = message
  
        
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ HBA 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
