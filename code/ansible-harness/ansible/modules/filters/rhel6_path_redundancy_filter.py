from .base_filter import BaseFilter, filter_result
import re

class RHEL6PathRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "multipath" in self.command:
            is_success, is_pass, result, message = self.multipath_type1(stdout_data)
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

    def multipath_type1(self, stdout_data):
        try:
            is_success = 1
            message_list = []
            is_pass = 1

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌점검 기준이 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            c= self.inspection_criteria
            min_active_groups = int(c.get("min_active_groups", 1))
            allowed_group_status = set([str(x).lower() for x in c.get("allowed_group_status", ["active", "enabled"])])
            required_path_tokens = [str(x).lower() for x in c.get("required_path_tokens", ["running"])]
            banned_tokens = [str(x).lower() for x in c.get("banned_tokens", ["failed", "faulty", "offline"])]
            require_same_policy = bool(c.get("require_same_policy", True))
            require_policy_contains = [str(x).lower() for x in c.get("require_policy_contains", [])]

            low = stdout_data.lower()
            if any(bt in low for bt in banned_tokens):
                is_pass = 0
                bad_lines = []
                for line in stdout_data.splitlines():
                    s = line.strip()
                    if any(bt in s.lower() for bt in banned_tokens):
                        bad_lines.append(s)
                message_list.append(f"비정상 상태 감지(banned_tokens): {banned_tokens}")
                if bad_lines:
                    message_list.append("문제 라인: \n" + "\n".join(bad_lines[:20]))
  
            lun_header_re = re.compile(r"^(\S+)\s+\(([^)]+)\)\s+(\S+)\s+(.+)$")
            policy_re = re.compile(r"policy='([^']+)'")
            group_status_re = re.compile(r"status=(\w+)")

            luns = []
            cur = None

            for raw in stdout_data.splitlines():
                s = raw.strip()
                if not s:
                    continue

                m = lun_header_re.match(s)
                if m:
                    if cur is not None:
                        luns.append(cur)

                    cur = {
                        "name": m.group(1),
                        "wwid": m.group(2), 
                        "policies": set(),
                        "group_statuses": [],
                        "path_lines": [], 
                    }
                    continue

                if cur is None:
                    continue

                if "policy=" in s and "status=" in s:
                    pm = policy_re.search(s)
                    if pm:
                        cur["policies"].add(pm.group(1).strip())

                    gm = group_status_re.search(s)
                    if gm:
                        cur["group_statuses"].append(gm.group(1).lower())
                    continue

                if re.search(r"\b\d+:\d+:\d+:\d+\b", s):
                    cur["path_lines"].append(s)
                    continue

            if cur is not None:
                luns.append(cur)

            # -------- host 블록 미존재
            if not luns:
                is_pass = 0
                message = "❌멀티패스 디바이스 블록을 찾을 수 없습니다.(multipath 출력 형식 확인 필요)"
                result = message
                return is_success, is_pass, result, message

            ok_lun = 0

            for lun in luns:
                name = lun["name"]
                wwid = lun["wwid"]
                lun_reasons = []

                reasons = []

                active_cnt = sum(1 for st in lun["group_statuses"] if st == "active")
                if active_cnt < min_active_groups:
                    lun_reasons.append(f"active 경로 그룹 부족({active_cnt} < {min_active_groups})")

            bad_group = [st for st in lun["group_statuses"] if st not in allowed_group_status]
            if bad_group:
                lun_reasons.append(f"비정상 그룹 status 존재: {sorted(set(bad_group))}")

            if not lun["path_lines"]:
                lun_reasons.append("path 라인 없음(장치 인식/출력 비정상 가능성)")
            else:
                for pl in lun["path_lines"]:
                    pl_low = pl.lower()
                    if any(bt in pl_low for bt in banned_tokens):
                        lun_reasons.append(f"비정상 path 상태, 라인: {pl}")
                        continue

                    missing = [t for t in required_path_tokens if t not in pl_low]
                    if missing:
                        lun_reasons.append(f"path 필수 토큰 누락{missing}: {pl}")

            if require_same_policy:
                if len(lun["policies"]) == 0:
                    lun_reasons.append("policy 정보 없음")
                elif len(lun["policies"]) > 1:
                    lun_reasons.append(f"policy 혼재: {sorted(lun['policies'])}")

            if require_policy_contains and lun["policies"]:
                one_policy = next(iter(lun['policies']))
                one_policy_low = one_policy.lower()
                missing = [t for t in require_policy_contains if t not in one_policy_low]
                if missing:
                    lun_reasons.append(f"policy 필수 토큰 누락{missing}: {one_policy}")

            if lun_reasons:
                is_pass = 0
                message_list.append(f"{name} ({wwid}):" + "; ".join(lun_reasons))
            else:
                ok_lun += 1

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
