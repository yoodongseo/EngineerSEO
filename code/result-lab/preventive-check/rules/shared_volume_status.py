from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class SharedVolumeStatusRule:
    RULE_KEY = "shared_volume_status"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "공유 볼륨 Read/Write 및 마운트 정상"

    @classmethod
    def allow_empty_output(cls, command):
        return True

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if command == "mount":
            if os_type in ("Linux", "Linux5"):
                return cls._run_mount_linux(params, stdout_data)
            if os_type == "Aix":
                return cls._run_mount_aix(params, stdout_data)
            if os_type == "Solaris":
                return cls._run_mount_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "scsimgr lun_map" in command:
            if os_type == "Hpux":
                return cls._run_scsimgr_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "get-clustersharedvolume" in command:
            if os_type == "Windows":
                return cls._run_cluster_shared_volume_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "공유 볼륨 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _run_mount_linux(cls, params, stdout_data):
        criteria = cls._normalize_shared_keyword(params.get("inspection_criteria"))
        if not criteria:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "공유 볼륨 식별 문자열(inspection_criteria)이 선언되지 않았습니다.",
            }

        criteria_items = ["공유 볼륨이 read-write 상태로 마운트되어 있을 것"]
        matched_lines = []
        failed_lines = []

        for raw_line in (stdout_data or "").splitlines():
            line = raw_line.strip()
            if " on " not in line or " (" not in line or ")" not in line:
                continue

            mount_path = cls._extract_mount_path_linux_solaris(line)
            if not mount_path or criteria not in mount_path.lower():
                continue

            options = line.split("(", 1)[1].rsplit(")", 1)[0].strip()
            option_tokens = [token.strip().lower() for token in options.split(",") if token.strip()]
            matched_lines.append(f"{mount_path} 옵션 {options}")

            if "ro" in option_tokens:
                failed_lines.append(f"비정상 공유 볼륨 {mount_path} Read-only(ro)")
            elif "rw" not in option_tokens:
                failed_lines.append(f"비정상 공유 볼륨 {mount_path} rw/ro 옵션 확인 불가 ({options})")

        if not matched_lines:
            return cls._build_not_applicable_mount(params, "mount 결과에서 점검 대상 공유 볼륨이 없습니다.")

        return cls._build_result(criteria_items, matched_lines, failed_lines)

    @classmethod
    def _run_mount_solaris(cls, params, stdout_data):
        criteria = cls._normalize_shared_keyword(params.get("inspection_criteria"))
        if not criteria:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "공유 볼륨 식별 문자열(inspection_criteria)이 선언되지 않았습니다.",
            }

        criteria_items = ["공유 볼륨이 read-write 상태로 마운트되어 있을 것"]
        matched_lines = []
        failed_lines = []

        for raw_line in (stdout_data or "").splitlines():
            line = raw_line.strip()
            if " on " not in line or " type " not in line:
                continue

            mount_path = cls._extract_mount_path_solaris(line)
            if not mount_path or criteria not in mount_path.lower():
                continue

            options = cls._extract_mount_options_solaris(line)
            matched_lines.append(f"{mount_path} 옵션 {options}")

            lower_options = options.lower()
            if "read/only" in lower_options:
                failed_lines.append(f"비정상 공유 볼륨 {mount_path} Read-only(read/only)")
            elif "read/write" not in lower_options:
                failed_lines.append(f"비정상 공유 볼륨 {mount_path} read/write 옵션 확인 불가 ({options})")

        if not matched_lines:
            return cls._build_not_applicable_mount(params, "mount 결과에서 점검 대상 공유 볼륨이 없습니다.")

        return cls._build_result(criteria_items, matched_lines, failed_lines)

    @classmethod
    def _run_mount_aix(cls, params, stdout_data):
        criteria = cls._normalize_shared_keyword(params.get("inspection_criteria"))
        if not criteria:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "공유 볼륨 식별 문자열(inspection_criteria)이 선언되지 않았습니다.",
            }

        lines = [line.rstrip("\n") for line in (stdout_data or "").splitlines()]
        header_line = ""
        header_index = -1

        for index, line in enumerate(lines):
            if line.strip().lower().startswith("node") and "mounted over" in line.lower():
                header_line = line
                header_index = index
                break

        if header_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "mount 결과에서 AIX 헤더 라인을 찾을 수 없습니다.",
            }

        criteria_items = ["공유 볼륨이 read-write 상태로 마운트되어 있을 것"]
        matched_lines = []
        failed_lines = []

        for line in lines[header_index + 1:]:
            stripped = line.strip()
            if not stripped or stripped.startswith("---"):
                continue

            parts = stripped.split()
            if len(parts) < 3:
                continue

            mounted_over = parts[1].strip()
            if not mounted_over or criteria not in mounted_over.lower():
                continue

            options = parts[-1].strip()
            option_tokens = [token.strip().lower() for token in options.split(",") if token.strip()]
            matched_lines.append(f"{mounted_over} 옵션 {options}")

            if "ro" in option_tokens:
                failed_lines.append(f"비정상 공유 볼륨 {mounted_over} Read-only(ro)")
            elif "rw" not in option_tokens:
                failed_lines.append(f"비정상 공유 볼륨 {mounted_over} rw/ro 옵션 확인 불가 ({options})")

        if not matched_lines:
            return cls._build_not_applicable_mount(params, "mount 결과에서 점검 대상 공유 볼륨이 없습니다.")

        return cls._build_result(criteria_items, matched_lines, failed_lines)

    @classmethod
    def _run_scsimgr_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or []
        abnormal_states = []
        if isinstance(criteria, list):
            abnormal_states = [str(item).strip().upper() for item in criteria if str(item).strip()]

        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable_hpux(params, "scsimgr lun_map 결과가 없습니다.")

        sections = cls._split_hpux_lun_sections(raw)
        if not sections:
            return cls._build_not_applicable_hpux(params, "점검 대상 공유 볼륨 경로가 없습니다.")

        criteria_items = ["공유 볼륨 경로 상태가 FAILED/OFFLINE/ERROR 가 아닐 것"]
        detail_lines = []
        failed_lines = []
        path_count = 0

        for lun_name, lun_content in sections:
            lun_paths = cls._split_hpux_lun_paths(lun_content)
            for path_name, path_content in lun_paths:
                path_count += 1
                state_value = cls._extract_key_value(path_content, "State")
                last_state_value = cls._extract_key_value(path_content, "Last Open or Close state")
                detail_lines.append(
                    f"LUN {lun_name} 경로 {path_name} State={state_value or '-'} LastOpenClose={last_state_value or '-'}"
                )

                if state_value and state_value.upper() in abnormal_states:
                    failed_lines.append(f"비정상 공유 볼륨 경로 {path_name} 상태 {state_value}")
                if (last_state_value or "").strip().upper() == "INACTIVE":
                    failed_lines.append(f"비정상 공유 볼륨 경로 {path_name} Last Open or Close state {last_state_value}")

        if path_count == 0:
            return cls._build_not_applicable_hpux(params, "점검 대상 공유 볼륨 경로가 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_cluster_shared_volume_windows(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable_windows(params, "클러스터 공유 볼륨 결과가 없습니다.")

        not_applicable_prefix = "NOT_APPLICABLE="
        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith(not_applicable_prefix):
                return cls._build_not_applicable_windows(params, stripped[len(not_applicable_prefix):].strip())

        blocks = cls._parse_repeated_key_blocks(raw)
        if not blocks:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "클러스터 공유 볼륨 결과에서 유효한 블록을 찾을 수 없습니다.",
            }

        criteria_items = ["클러스터 공유 볼륨 상태가 Online 일 것"]
        detail_lines = []
        failed_lines = []
        parsed_count = 0

        for block in blocks:
            name = (block.get("name") or "-").strip()
            state = (block.get("state") or "-").strip()
            path = (block.get("path") or "-").strip()

            if name == "-" and state == "-" and path == "-":
                continue

            parsed_count += 1
            detail_lines.append(f"{name} 상태 {state} 경로 {path}")

            if (state or "").strip().lower() not in ["online", "up", "ok"]:
                failed_lines.append(f"비정상 공유 볼륨 {name} 상태 {state or '-'}")

        if parsed_count == 0:
            return cls._build_not_applicable_windows(params, "점검 대상 클러스터 공유 볼륨이 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _build_not_applicable_mount(cls, params, detail):
        return build_not_applicable(
            [
                "공유 볼륨 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @classmethod
    def _build_not_applicable_hpux(cls, params, detail):
        return build_not_applicable(
            [
                "공유 볼륨 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @classmethod
    def _build_not_applicable_windows(cls, params, detail):
        return build_not_applicable(
            [
                "공유 볼륨 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @staticmethod
    def _normalize_shared_keyword(value):
        text = str(value or "").strip().lower()
        if text == "sheard":
            return "shared"
        return text

    @staticmethod
    def _extract_mount_path_linux_solaris(line):
        marker = " on "
        type_marker = " type "
        start = line.find(marker)
        end = line.find(type_marker, start + len(marker))
        if start == -1 or end == -1:
            return ""
        return line[start + len(marker):end].strip()

    @staticmethod
    def _extract_mount_path_solaris(line):
        marker = " on "
        type_marker = " type "
        start = line.find(marker)
        end = line.find(type_marker, start + len(marker))
        if start == -1 or end == -1:
            return ""
        return line[start + len(marker):end].strip()

    @staticmethod
    def _extract_mount_options_solaris(line):
        type_marker = " type "
        type_index = line.find(type_marker)
        if type_index == -1:
            return ""

        tail = line[type_index + len(type_marker):].strip()
        tail_parts = tail.split(None, 1)
        if len(tail_parts) < 2:
            return ""

        options_text = tail_parts[1]
        date_marker = " on "
        date_index = options_text.rfind(date_marker)
        if date_index != -1:
            return options_text[:date_index].strip()
        return options_text.strip()

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
        parts = lun_content.split("LUN path     : ")
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
    def _extract_key_value(text, key):
        prefix = f"{key}"
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix) and "=" in stripped:
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

RULE_KEY = SharedVolumeStatusRule.RULE_KEY
RULE_CLASS = SharedVolumeStatusRule
