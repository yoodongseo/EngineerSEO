import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class PathRedundancyStatusRule:
    RULE_KEY = "path_redundancy_status"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, str) and criteria.strip():
            return f"Multipath 상태 {criteria.strip()}"
        return "Path 이중화 상태 정상"

    @classmethod
    def allow_empty_output(cls, command):
        return True

    @classmethod
    def allow_not_found(cls, command):
        return True

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        # 타사 솔루션 사용 또는 패키지 미설치로 인한 명령어 실패 감지 (VIP 통과된 에러 메시지)
        missing_markers = ["command not found", "not found", "no such", "is not recognized", "찾을 수 없습니다"]
        low_out = (stdout_data or "").lower()
        if any(marker in low_out for marker in missing_markers):
            return build_not_applicable(
                [
                    "기본 OS 이중화 명령어 미존재 (타사 솔루션 구성 확인 요망)",
                    f"  세부 내용: {stdout_data.strip()}",
                ]
            )

        if "multipath -ll" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_multipath_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "mpathadm list lu" in command and "mpathadm show lu" in command:
            if os_type == "Solaris":
                return cls._run_mpathadm_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if command == "lspath":
            if os_type == "Aix":
                return cls._run_lspath_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "scsimgr lun_map" in command:
            if os_type == "Hpux":
                return cls._run_scsimgr_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "get-mpiopath" in command:
            if os_type == "Windows":
                return cls._run_mpio_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "Path 이중화 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _run_multipath_linux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "multipath 대상 장치가 없습니다.")

        criteria = params.get("inspection_criteria") or {}
        min_active_groups = cls._to_int(criteria.get("min_active_groups"), 1)
        allowed_group_status = [str(item).lower() for item in criteria.get("allowed_group_status", [])]
        required_path_tokens = [str(item).lower() for item in criteria.get("required_path_tokens", [])]
        banned_tokens = [str(item).lower() for item in criteria.get("banned_tokens", [])]
        require_same_policy = bool(criteria.get("require_same_policy"))
        policy_contains = [str(item).lower() for item in criteria.get("require_policy_contains", [])]

        criteria_items = ["모든 multipath 장치의 경로 그룹/경로 상태가 정상일 것"]
        blocks = cls._split_linux_blocks(raw)
        if not blocks:
            return cls._build_not_applicable(params, "multipath 대상 장치가 없습니다.")

        detail_lines = []
        failed_lines = []

        for block in blocks:
            header = block[0].strip()
            group_lines = []
            path_lines = []

            for line in block[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith("|-+-") or stripped.startswith("`-+-"):
                    group_lines.append(stripped)
                elif stripped.startswith("| `-") or stripped.startswith("`-"):
                    path_lines.append(stripped)

            group_statuses = []
            policies = []
            active_groups = 0

            for line in group_lines:
                lower = line.lower()
                status = cls._extract_linux_group_status(lower)
                policy = cls._extract_linux_policy(lower)
                if status:
                    group_statuses.append(status)
                if policy:
                    policies.append(policy)
                if status == "active":
                    active_groups += 1

            detail_lines.append(
                f"{header} 그룹 {len(group_lines)}개, 경로 {len(path_lines)}개, 활성 그룹 {active_groups}개"
            )

            if min_active_groups and active_groups < min_active_groups:
                failed_lines.append(f"비정상 Path 장치 {header} 활성 그룹 수 부족 ({active_groups}개)")

            for status in group_statuses:
                if allowed_group_status and status not in allowed_group_status:
                    failed_lines.append(f"비정상 Path 장치 {header} 그룹 상태 {status}")

            if require_same_policy and policies:
                unique_policies = {policy for policy in policies}
                if len(unique_policies) > 1:
                    failed_lines.append(f"비정상 Path 장치 {header} 그룹 정책 불일치 ({', '.join(sorted(unique_policies))})")

            for token in policy_contains:
                if policies and not all(token in policy for policy in policies):
                    failed_lines.append(f"비정상 Path 장치 {header} 정책에 '{token}' 없음")

            for line in path_lines:
                lower = line.lower()
                path_label = cls._extract_linux_path_label(line)

                for token in required_path_tokens:
                    if token not in lower:
                        failed_lines.append(f"비정상 Path 경로 {header} {path_label} 필수 상태 '{token}' 누락")
                        break

                for token in banned_tokens:
                    if token in lower:
                        failed_lines.append(f"비정상 Path 경로 {header} {path_label} 금지 상태 '{token}' 검출")
                        break

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_mpathadm_solaris(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "mpathadm 대상 LU가 없습니다.")

        expected_state = str(params.get("inspection_criteria") or "CONNECTED").strip().upper()
        criteria_items = [f"모든 LU 경로 상태가 {expected_state} 일 것"]
        blocks = cls._split_solaris_lu_blocks(raw)
        if not blocks:
            return cls._build_not_applicable(params, "mpathadm 대상 LU가 없습니다.")

        detail_lines = []
        failed_lines = []

        for lu_name, block_lines in blocks:
            path_count = 0
            current_status = ""
            for line in block_lines:
                stripped = line.strip()
                lower = stripped.lower()

                if lower.startswith("operational path count:"):
                    path_count = cls._to_int(stripped.split(":", 1)[1], 0)

                if lower.startswith("path state:"):
                    current_status = stripped.split(":", 1)[1].strip().upper()
                    if current_status and current_status != expected_state:
                        failed_lines.append(f"비정상 LU 경로 {lu_name} 상태 {current_status}")

            detail_lines.append(f"{lu_name} 운영 경로 {path_count}개")

            if path_count == 0:
                failed_lines.append(f"비정상 LU {lu_name} 운영 경로 없음")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_lspath_aix(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "lspath 대상 디스크가 없습니다.")

        expected_state = str(params.get("inspection_criteria") or "Available").strip().lower()
        criteria_items = [f"모든 경로 상태가 {expected_state} 일 것"]
        detail_lines = []
        failed_lines = []
        path_count = 0

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            parts = stripped.split()
            if len(parts) < 4:
                continue

            path_count += 1
            disk = parts[1].strip()
            parent = parts[2].strip()
            status = parts[3].strip()
            detail_lines.append(f"{disk} 경로 {parent} 상태 {status}")

            if status.lower() != expected_state:
                failed_lines.append(f"비정상 경로 {disk}/{parent} 상태 {status}")

        if path_count == 0:
            return cls._build_not_applicable(params, "lspath 대상 디스크가 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_scsimgr_hpux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "점검 대상 LUN 경로가 없습니다.")

        criteria = params.get("inspection_criteria") or {}
        min_paths = cls._to_int(criteria.get("min_paths"), 2)
        fail_states = [str(item).strip().upper() for item in criteria.get("fail_state", [])]
        criteria_items = [f"모든 LUN 경로가 {min_paths}개 이상이고 비정상 상태가 아닐 것"]

        sections = cls._split_hpux_lun_sections(raw)
        if not sections:
            return cls._build_not_applicable(params, "점검 대상 LUN 경로가 없습니다.")

        detail_lines = []
        failed_lines = []
        checked_luns = 0

        for lun_name, lun_content in sections:
            if not cls._is_hpux_fc_san_lun(lun_name, lun_content):
                continue

            checked_luns += 1
            lun_paths = cls._split_hpux_lun_paths(lun_content)
            detail_lines.append(f"{lun_name} 경로 {len(lun_paths)}개")

            if len(lun_paths) < min_paths:
                failed_lines.append(f"비정상 LUN {lun_name} 경로 수 부족 ({len(lun_paths)}개)")

            for path_name, path_content in lun_paths:
                state_value = cls._extract_key_value(path_content, "State").upper()
                if state_value and state_value in fail_states:
                    failed_lines.append(f"비정상 LUN 경로 {lun_name}/{path_name} 상태 {state_value}")

        if checked_luns == 0:
            return cls._build_not_applicable(params, "FC/SAN LUN 경로가 확인되지 않았습니다.")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_mpio_windows(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "MPIO 경로 정보가 없습니다.")

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("NOT_APPLICABLE="):
                return cls._build_not_applicable(params, stripped.split("=", 1)[1].strip())

        blocks = cls._parse_repeated_key_blocks(raw)
        if not blocks:
            return cls._build_not_applicable(params, "MPIO 경로 정보가 없습니다.")

        criteria_items = ["구성된 MPIO 디스크의 활성 경로가 2개 이상이고 상태가 Up/Active 일 것"]
        detail_lines = []
        failed_lines = []

        for block in blocks:
            name = (block.get("name") or "-").strip()
            path_count = cls._to_int(block.get("pathcount"), 0)
            active_count = cls._to_int(block.get("activepaths"), path_count)
            state = (block.get("state") or "-").strip()
            detail_lines.append(f"{name} 경로 {path_count}개, 활성 {active_count}개, 상태 {state}")

            if path_count < 2:
                failed_lines.append(f"비정상 MPIO 디스크 {name} 경로 수 부족 ({path_count}개)")
            if active_count < 1:
                failed_lines.append(f"비정상 MPIO 디스크 {name} 활성 경로 없음")
            if state.lower() not in ["up", "active", "online", "ok"]:
                failed_lines.append(f"비정상 MPIO 디스크 {name} 상태 {state}")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _build_not_applicable(cls, params, detail):
        return build_not_applicable(
            [
                "Path 이중화 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @staticmethod
    def _split_linux_blocks(stdout_data):
        blocks = []
        current = []

        for line in stdout_data.splitlines():
            stripped = line.strip()
            if stripped and " dm-" in stripped and not stripped.startswith(("size=", "|", "`")):
                if current:
                    blocks.append(current)
                current = [line]
            elif current:
                current.append(line)

        if current:
            blocks.append(current)

        return blocks

    @staticmethod
    def _extract_linux_group_status(text):
        status_part = text.split("status=", 1)[-1] if "status=" in text else ""
        if not status_part:
            return ""
        return status_part.split()[0].strip(",")

    @staticmethod
    def _extract_linux_policy(text):
        if "policy=" not in text:
            return ""
        policy_part = text.split("policy=", 1)[1]
        return policy_part.split("prio=", 1)[0].strip()

    @staticmethod
    def _extract_linux_path_label(line):
        stripped = line.replace("|", " ").replace("`", " ").replace("-", " ")
        parts = [part for part in stripped.split() if part]
        return "/".join(parts[:3]) if len(parts) >= 3 else (parts[0] if parts else "-")

    @staticmethod
    def _split_solaris_lu_blocks(stdout_data):
        blocks = []
        current_name = ""
        current_lines = []

        for line in stdout_data.splitlines():
            stripped = line.strip()
            if stripped.startswith("/dev/rdsk/"):
                if current_name:
                    blocks.append((current_name, current_lines))
                current_name = stripped
                current_lines = []
                continue
            if current_name:
                current_lines.append(line)

        if current_name:
            blocks.append((current_name, current_lines))

        return blocks

    @staticmethod
    def _split_hpux_lun_sections(stdout_data):
        parts = stdout_data.split("LUN PATH INFORMATION FOR LUN : ")
        sections = []
        for part in parts[1:]:
            lines = part.splitlines()
            if not lines:
                continue
            lun_name = lines[0].strip()
            lun_content = "\n".join(lines[1:])
            sections.append((lun_name, lun_content))
        return sections

    @staticmethod
    def _split_hpux_lun_paths(lun_content):
        parts = re.split(r"LUN\s+path\s*:\s*", lun_content)
        paths = []
        for part in parts[1:]:
            lines = part.splitlines()
            if not lines:
                continue
            path_name = lines[0].strip()
            path_content = "\n".join(lines[1:])
            paths.append((path_name, path_content))
        return paths

    @staticmethod
    def _is_hpux_fc_san_lun(lun_name, lun_content):
        name = str(lun_name or "").strip().lower()
        if name.startswith("/dev/pt/"):
            return False

        content = str(lun_content or "").lower()
        if "scsi transport protocol       = sas" in content:
            return False
        if "scsi transport protocol       = sata" in content:
            return False

        return "scsi transport protocol       = fibre_channel" in content or "scsi transport protocol       = fc" in content

    @staticmethod
    def _extract_key_value(text, key):
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                return stripped.split("=", 1)[1].strip()
        return ""

    @staticmethod
    def _parse_repeated_key_blocks(stdout_data):
        blocks = []
        current = {}

        for raw_line in (stdout_data or "").splitlines():
            line = raw_line.strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            normalized_key = key.strip().lower()
            normalized_value = value.strip()

            if normalized_key in current:
                blocks.append(current)
                current = {}

            current[normalized_key] = normalized_value

        if current:
            blocks.append(current)

        return blocks

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @staticmethod
    def _dedupe(items):
        seen = set()
        result = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result

RULE_KEY = PathRedundancyStatusRule.RULE_KEY
RULE_CLASS = PathRedundancyStatusRule
