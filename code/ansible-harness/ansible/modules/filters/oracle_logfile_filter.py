from .base_filter import BaseFilter, filter_result
import re

class OracleLogfileFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "oracle_ansible.sh" in self.command:
            is_success, is_pass, result, message = self.oracle_type1(stdout_data)
        else:
            is_pass = 0
            is_success = 0
            message = f"❌ 지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def _path_prefix(self, path_text):
        path = path_text.strip()
        if path.startswith("+"):
            return path.split("/", 1)[0]
        if path.startswith("/"):
            parts = path.split("/")
            if len(parts) > 1 and parts[1]:
                return "/" + parts[1]
            return "/"
        return path

    def oracle_type1(self, stdout_data):
        try:
            is_success = 1
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]

            fail_statuses = []
            if isinstance(self.inspection_criteria, str):
                fail_statuses = [s.strip().upper() for s in self.inspection_criteria.split(",") if s.strip()]
            elif isinstance(self.inspection_criteria, (list, tuple, set)):
                fail_statuses = [str(s).strip().upper() for s in self.inspection_criteria if str(s).strip()]

            if not fail_statuses:
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria에 불량 STATUS(예: INVALID,STALE)를 선어해야 합니다."
                result = message
                return is_success, is_pass, result, message

            groups = {}
            current_group = None

            for line in lines:
                upper_line = line.upper()

                if upper_line.startswith("ELAPSED:"):
                    continue
                if "GROUP#" in upper_line and "STATUS" in upper_line:
                    continue
                if upper_line in {"MEMBER", "IS_"}:
                    continue
                if set(line) <= {"-", "_"}:
                    continue

                group_match = re.match(r'^(\d+)\s+([A-Za-z_]+)(?:\s+([A-Za-z_]+))?$', line)
                if group_match:
                    group_id = group_match.group(1)
                    status = group_match.group(2).upper()
                    current_group = group_id
                    if group_id not in groups:
                        groups[group_id] = {"status": status, "members": []}
                    else:
                        groups[group_id]["stats"] = status
                    continue

                if (line.startswith("+") or line.startswith("/")) and current_group is not None:
                    groups[current_group]["members"].append(line)
                    continue

            if not groups:
                is_pass = 0
                message = "❌ 점검 필요: 로그파일 정보를 파싱하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            bad_status = []
            missing_duplex = []
            missing_path_duplex = []

            for group_id, info in sorted(groups.items(), key=lambda x: int(x[0])):
                status = info.get("status", "")
                members = list(dict.fromkeys(info.get("members", [])))
                prefixes = list(dict.fromkeys([self._path_prefix(p) for p in members]))

                if status in fail_statuses:
                    bad_status.append(f"group {group_id}={status}")
                if len(members) < 2:
                    missing_duplex.append(f"group {group_id} members={len(members)}")
                if len(prefixes) < 2:
                    missing_path_duplex.append(
                        f"group {group_id} paths={', '.join(prefixes) if prefixes else '없음'}"
                    )

            if bad_status or missing_duplex or missing_path_duplex:
                is_pass = 0
                detail = []
                if bad_status:
                    detail.append("- STATUS 이상: " + ", ".join(bad_status))
                if missing_duplex:
                    detail.append("- 파일 이중화 미흡: " + ", ".join(missing_duplex))
                if missing_path_duplex:
                    detail.append("- 경로 이중화 미흡: " + ", ".join(missing_path_duplex))
                message = "❌ 점검 필요: 로그파일 상태/이중화 기준을 확인하세요.\n" + "\n".join(detail)
            else:
                is_pass = 1
                message = f"✅ 정상: 로그파일 STATUS가 정상이며, 그룹 이중화/경로 이중화가 확인되었습니다. (group count: {len(groups)})"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 로그파일  평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
