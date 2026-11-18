from .base_filter import BaseFilter, filter_result
import re

class RHEL6HbaStatusFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "systool" in self.command or "fc_host" in self.command:
            is_success, is_pass, result, message = self.systool_type1(stdout_data)
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

    def systool_type1(self, stdout_data):
        try:
            is_success = 1
            message_list = []
            is_pass = 1


            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌HBA 정보 수집 실패: FC_HBA 디바이스 존재 여부 확인이 필요합니다."
                result = message
                return is_success, is_pass, result, message
            if stdout_data and "not found" in stdout_data.lower() or "찾을 수 없습니다" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "Class" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Class' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message


            lines = stdout_data.splitlines()
  
            hosts = []
            cur = None

            for raw in lines:
                line = raw.strip()
                if not line:
                    continue

                if line.startswith('Class Device ='):
                    if cur is not None:
                        hosts.append(cur)

                    m = re.search(r'"(host\d+)"', line)
                    host_name = m.group(1) if m else "unknown_host"

                    cur = {
                        "host": host_name,
                        "fc_state": None, 
                        "fc_speed_raw": None, 
                    }
                    continue
                  
                if cur is None:
                    continue

                if line.startswith("fc_state"):
                    cur["fc_state"] = line.split("=", 1)[-1].strip().strip('"')
                    continue

                if line.startswith("fc_speed"):
                    cur["fc_speed_raw"] = line.split("=", 1)[-1].strip().strip('"')
                    continue

            if cur is not None:
                hosts.append(cur)

            # -------- host 블록 미존재
            if not hosts:
                is_pass = 0
                message = "❌HBA Host 블록을 찾을 수 없습니다.(장치 미 인식 상태)"
                result = message
                return is_success, is_pass, result, message

            ok_count = 0
            total_count = len(hosts)

            for h in hosts:
                host = h.get("host", "unknown")
                fc_state = (h.get("fc_state") or "").strip()
                fc_speed_raw = (h.get("fc_speed_raw") or "").strip()

                reasons = []

                if not fc_state:
                    reasons.append("fc_state 미출력")
                elif fc_state.lower() != "online":
                    reasons.append(f"fc_state 비정상({fc_state})")

                if not fc_speed_raw:
                    reasons.append("fc_speed 미출력")
                elif "unknown" in fc_speed_raw.lower():
                    reasons.append(f"fc_speed = unknown")
                elif re.search(r"\b0\s*Gbit\b", fc_speed_raw, re.IGNORECASE):
                    reasons.append(f"fc_speed = 0 Gbit")

                if reasons:
                    is_pass = 0
                    message_list.append(f"{host}: " + ", ".join(reasons))
                else:
                    ok_count += 1

            if is_pass == 1:
                message = f"✅HBA FC 연결 정상: {ok_count}/{total_count} host online"
            else:
                header = f"❌HBA 연결 비정상: {ok_count}/{total_count} host 정상"
                details = "\n".join(message_list)
                message = header + "\n" + details

            result = message
  
        
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ HBA 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
