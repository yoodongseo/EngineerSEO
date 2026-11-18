from .base_filter import BaseFilter, filter_result
import re

class SunHbaStatusFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "fcinfo" in self.command:
            is_success, is_pass, result, message = self.fcinfo_type1(stdout_data)
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

    def fcinfo_type1(self, stdout_data):
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
            if not stdout_data or "HBA" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'HBA' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria.strip():
                is_pass = 0
                message = f"❌ 점검 기준 (inspection_criteria) 이(가) 누락되었거나 문자열이 아닙니다."
                result = message
                return is_success, is_pass, result, message

            ok_state = self.inspection_criteria.strip().lower()
            low = stdout_data.lower()
            ports = []
            cur = None

            for raw in stdout_data.splitlines():
                line = raw.strip()
                if not line:
                    continue

                if line.lower().startswith("hba port wwn:"):
                    if cur is not None:
                        ports.append(cur)

                    cur = {
                        "wwn": line.split(":", 1)[-1].strip(),
                        "state": None, 
                        "speed_raw": None, 
                    }
                    continue
                  
                if cur is None:
                    continue

                if line.lower().startswith("state:"):
                    cur["state"] = line.split(":", 1)[-1].strip()
                    continue

                if line.lower().startswith("current speed:"):
                    cur["speed_raw"] = line.split(":", 1)[-1].strip()
                    continue

            if cur is not None:
                ports.append(cur)

            # -------- host 블록 미존재
            if not ports:
                is_pass = 0
                message = "❌HBA Port 블록을 찾을 수 없습니다.(장치 미 인식 상태)"
                result = message
                return is_success, is_pass, result, message

            ok_count = 0
            total_count = len(ports)

            for idx, p in enumerate(ports, start=1):
                wwn = p.get("wwn") or f"port#{idx}"

                state_raw = (p.get("state") or "").strip()
                state = state_raw.lower()

                speed_raw = (p.get("speed_raw") or "").strip()
                speed_low = speed_raw.lower()

                reasons = []

                if not state_raw:
                    reasons.append("state 미출력")
                elif state != ok_state:
                    reasons.append(f"state 비정상({state_raw})")

                if not speed_raw:
                    reasons.append("Current speed 미출력")
                elif "unknown" in speed_low:
                    reasons.append("Current speed = unknown")
                elif re.search(r"\b0\s*gn\b", speed_low):
                    reasons.append(f"Current speed = 0 Gb")

                if reasons:
                    is_pass = 0
                    message_list.append(f"❌ {wwn}: " + ", ".join(reasons))
                else:
                    ok_count += 1

            if is_pass == 1:
                message = f"✅HBA FC 연결 정상: {ok_count}/{total_count} 포트 정상: online"
            else:
                header = f"❌HBA 연결 비정상: {ok_count}/{total_count} 포트 정상"
                details = "\n".join(message_list)
                message = header + "\n" + details

            result = message
  
        
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ HBA 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
