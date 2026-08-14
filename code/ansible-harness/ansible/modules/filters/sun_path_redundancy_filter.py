from .base_filter import BaseFilter, filter_result
import re

class SunPathRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "mpathadm" in self.command:
            is_success, is_pass, result, message = self.mpath_type1(stdout_data)
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

    def mpath_type1(self, stdout_data):
        try:
            is_success = 1
            message_list = []
            is_pass = 1

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria.strip():
                is_pass = 0
                message = f"❌점검 기준이 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            ok = self.inspection_criteria.strip().upper()

            if not stdout_data or not str(stdout_data).strip():
                message = "✅ LU 결과 없음 > PATH 이중화 미구성 상태"
                result = message
                return is_success, is_pass, result, message

            blocks = []
            cur = None

            for line in stdout_data.splitlines():
                s = line.strip()
                if not s:
                    continue

                if s.startswith("*** "):
                    if cur:
                        blocks.append(cur)
                    cur = {"lu": s[4:], "stms": "", "cpath": "", "pstatus": "", "paths": []}
                    continue

                if not cur:
                    continue

                sl = s.lower()
                if sl.startswith("stms state:"):
                    cur["stms"] = s.split(":", 1)[-1].strip()
                elif sl.startswith("current path:"):
                    cur["cpath"] = s.split(":", 1)[-1].strip()
                elif sl.startswith("path status:"):
                    cur ["pstatus"] = s.split(":", 1)[-1].strip()
                elif sl.startswith("path "):
                    m = re.match(r"^Path\s+(.+?):\s*(\S+)", s, re.IGNORECASE)
                    if m:
                        cur["paths"].append((m.group(1), m.group(2)))

            if cur:
                blocks.append(cur)

            if not blocks:
                message = "✅ LU 결과 없음 > PATH 이중화 미구성 상태"


            ok_cnt = 0
            
            for b in blocks:
                lu = b["lu"] or "unknown_lu"
                reasons = []

                if not b["stms"] or b["stms"].upper() != "ENABLED":
                    reasons.append(f"Stms State({b['stms'] or '미출력'})")

                if not b["cpath"]:
                    reasons.append("Current Path(미출력)")

                if not b["pstatus"] or b["pstatus"].upper() != ok_status:
                    reasons.append(f"Path Status({b['pstatus'] or '미출력'})")
                    
                bad_path = [f"{p}: {st}" for p, st in b["paths"] if st.upper() != ok_status]
                if not b["paths"]:
                    reasons.append("path 라인(미출력)")
                elif bad_paths:
                    reasons.append("비정상 Path=" + ", ".join(bad_paths))

                if reasons:
                    is_pass = 0
                    message_list.append(f"❌ {lu}: " + ", ".join(reasons))
                else:
                    ok_cnt += 1

            if is_pass == 1:
                message = f"✅ Path 이중화 정상"
            else:
                message = "\n".join(message_list) if message_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message
  
        
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Path 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
