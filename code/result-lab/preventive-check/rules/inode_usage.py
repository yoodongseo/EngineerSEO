from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
import re

class InodeUsageRule:
    RULE_KEY = "inode_usage"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        try:
            return f"I-Node 사용률 {float(criteria):.1f}% 이하"
        except Exception:
            return "I-Node 사용률 기준 이내"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip().lower()

        if "df -i" in command:
            if os_type in ("linux", "linux5"):
                return cls._run_df_i_linux(params, stdout_data)            
            if os_type == "aix":
                return cls._run_df_i_aix(params, stdout_data)

        if "bdf -i" in command:
            if os_type == "hpux":
                return cls._run_bdf_i_hpux(params, stdout_data)

        if "df -o" in command:
            if os_type == "solaris":
                return cls._run_df_o_i_solaris(params, stdout_data)            

        if "fsutil dirty query" in command or "get-volume" in command:
            if os_type == "windows":
                return cls._run_windows_dirty_volume(params, stdout_data)            

        return build_unsupported_command(params)

    @classmethod
    def _run_windows_dirty_volume(cls, params, stdout_data):
        output = (stdout_data or "").strip()
        if not output:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-Volume/fsutil dirty query 출력이 비어 있습니다.",
            }

        blocked_phrase = str(params.get("inspection_criteria") or "is Dirty").strip()
        blocked_lower = blocked_phrase.lower()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        error_lines = [
            line
            for line in lines
            if "access is denied" in line.lower() or "error=" in line.lower()
        ]
        if error_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "일부 볼륨의 Dirty 상태 확인 중 접근 오류가 발생했습니다: " + "; ".join(error_lines),
            }

        parsed_rows = []
        for line in lines:
            lowered = line.lower()
            if (
                " is dirty" not in lowered
                and " is not dirty" not in lowered
                and "(dirty)" not in lowered
                and "(not dirty)" not in lowered
            ):
                continue

            matched = re.search(r"volume\s+([a-z]:)\s+is\s+(not\s+)?dirty", line, re.IGNORECASE)
            if not matched:
                matched = re.search(r"([a-z]:)\s+is\s+(not\s+)?dirty", line, re.IGNORECASE)
            if not matched:
                matched = re.search(r"([a-z]:)\s*\(\s*(not\s+)?dirty\s*\)", line, re.IGNORECASE)

            if matched:
                drive = matched.group(1).upper()
                is_not = matched.group(2) is not None
                state = "is NOT Dirty" if is_not else "is Dirty"
                parsed_rows.append((drive, state))
                continue

            state = "is NOT Dirty" if "is not dirty" in lowered else "is Dirty"
            parsed_rows.append(("-", state))

        if not parsed_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dirty 상태 판정 가능한 볼륨 라인을 찾을 수 없습니다.",
            }

        detail_lines = [f"{drive} {state}" for drive, state in parsed_rows]
        failed_lines = []
        for drive, state in parsed_rows:
            if blocked_lower in state.lower():
                failed_lines.append(f"{drive} 볼륨 상태가 금지 상태입니다: {state}")

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "볼륨 Dirty 상태",
            "criteria_items": [f"각 볼륨 '{blocked_phrase}' 미검출"],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines
        }

    @classmethod
    def _run_df_i_linux(cls, params, stdout_data):
        return cls._run_df_i_common(params, stdout_data, fail_on_equal=False)

    @classmethod
    def _run_df_i_aix(cls, params, stdout_data):
        return cls._run_df_i_common(params, stdout_data, fail_on_equal=False)

    @classmethod
    def _run_bdf_i_hpux(cls, params, stdout_data):
        return cls._run_df_i_common(params, stdout_data, fail_on_equal=False)

    @classmethod
    def _run_df_i_common(cls, params, stdout_data, fail_on_equal):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = int(criteria)
        except (TypeError, ValueError):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"I-Node 기준값이 정수가 아닙니다: {criteria}",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        header_line = None
        header_index = -1

        for index, line in enumerate(lines):
            if line.strip().startswith("Filesystem"):
                header_line = line.strip()
                header_index = index
                break

        if header_index == -1 or not header_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -i 출력에서 'Filesystem' 헤더를 찾을 수 없습니다.",
            }

        header_parts = header_line.split()
        inode_column_index = cls._find_inode_column(header_parts)
        if inode_column_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -i 헤더에서 I-Node 사용률 컬럼(IUse%, %Iused 등)을 찾을 수 없습니다.",
            }

        detail_lines = []
        failed_lines = []
        criteria_operator = "미만" if fail_on_equal else "이하"

        for line in lines[header_index + 1 :]:
            parts = line.split()
            if not parts or not parts[0].startswith("/"):
                continue

            try:
                inode_value = int(parts[inode_column_index].strip("%"))
            except (IndexError, ValueError):
                continue

            filesystem = parts[-1] if len(parts) > inode_column_index else parts[0]
            detail_lines.append(f"{filesystem} I-Node 사용률 {inode_value}%")

            exceeds = inode_value >= criteria_value if fail_on_equal else inode_value > criteria_value
            if exceeds:
                comparator = "<" if fail_on_equal else "<="
                failed_lines.append(f"{filesystem} I-Node 사용률 {inode_value}% (기준: {comparator} {criteria_value}%)")

        if not detail_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -i 출력에서 점검 가능한 파일시스템 데이터를 찾을 수 없습니다.",
            }

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "I-Node 사용률",
            "criteria_items": [f"파일시스템 I-Node 사용률 {criteria_value}% {criteria_operator}"],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",            
            "detail_lines": failed_lines if failed_lines else detail_lines
        }

    @classmethod
    def _run_df_o_i_solaris(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = int(criteria)
        except (TypeError, ValueError):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"I-Node 기준값이 정수가 아닙니다: {criteria}",
            }

        output = (stdout_data or "").strip()
        if not output:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -o i 출력이 비어있습니다.",
            }

        lines = [line.strip() for line in output.splitlines() if line.strip()]
        ignore_tokens = [
            "operation not applicable for fstype",
            "사용할수 없는",
        ]

        data_lines = []
        ignore_lines = []
        for line in lines:
            line_lower = line.lower()
            if any(token in line_lower for token in ignore_tokens):
                ignore_lines.append(line)
            else:
                data_lines.append(line)

        criteria_items = [f"파일시스템 I-Node 사용률 {criteria_value}% 미만"]

        if not data_lines and ignore_lines:
            return {
                "is_success": 1,
                "is_pass": 1,
                "check_target": "I-Node 사용률",
                "criteria_items": criteria_items,
                "judgement_text": "정상",
                "detail_lines": ["I-Node 점검 대상 파일시스템 미존재: 정상 판단"],
            }

        checked = 0
        detail_lines = []
        failed_lines = []

        for line in data_lines:
            line_lower = line.lower()
            if "%" not in line:
                continue
            if line_lower.startswith("filesystem") or line_lower.startswith("fliesystem") or line.startswith("파일시스템"):
                continue

            parts = line.split()
            pct_token = None
            for part in parts:
                if part.endswith("%"):
                    pct_token = part
                    break

            if not pct_token:
                continue

            try:
                pct_value = int(pct_token.replace("%", ""))
            except ValueError:
                continue

            checked += 1
            filesystem = parts[0]
            mount_point = parts[-1]
            detail_lines.append(f"{filesystem} ({mount_point}) I-Node 사용률 {pct_value}%")

            if pct_value >= criteria_value:
                failed_lines.append(
                    f"{filesystem} ({mount_point}) I-Node 사용률 {pct_value}% (기준: < {criteria_value}%)"
                )

        if checked == 0:
            return {
                "is_success": 1,
                "is_pass": 1,
                "check_target": "I-Node 사용률",
                "criteria_items": criteria_items,
                "judgement_text": "정상",
                "detail_lines": ["I-Node 점검 대상 파일시스템 미존재: 정상 판단"],
            }

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "I-Node 사용률",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @staticmethod
    def _find_inode_column(header_parts):
        normalized = [part.strip().lower() for part in header_parts]
        candidates = {"iuse%", "%iused", "iused%", "%iuse"}

        for index, part in enumerate(normalized):
            if part in candidates:
                return index

        return -1

RULE_KEY = InodeUsageRule.RULE_KEY
RULE_CLASS = InodeUsageRule
