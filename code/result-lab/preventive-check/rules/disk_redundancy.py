from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class DiskRedundancyRule:
    RULE_KEY = "disk_redundancy"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "RAID 구성 및 State 정상"

    @classmethod
    def allow_empty_output(cls, command):
        return True

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "mdadm --detail" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_mdadm_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "lsvg -l rootvg" in command:
            if os_type == "Aix":
                return cls._run_lsvg_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "ioscan -fnc fc" in command:
            if os_type == "Hpux":
                return cls._run_ioscan_fc_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "metastat" in command:
            if os_type == "Solaris":
                return cls._run_metastat_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "get-virtualdisk" in command:
            if os_type == "Windows":
                return cls._run_virtualdisk_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        lines = list(detail_lines)
        lines.extend(failed_lines)

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "DISK 이중화 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": lines,
        }

    @classmethod
    def _run_mdadm_linux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        criteria_items = ["구성된 RAID 장치가 모두 정상 상태일 것"]

        if not raw:
            name = params.get("name", "점검 항목")
            os_type = params.get("os", "Linux")
            return build_not_applicable(
                [
                    "DISK 이중화 구성이 확인되지 않았습니다.",
                    f"  점검 항목: {name}",
                    f"  OS 유형: {os_type}",
                    "  세부 내용: mdadm 대상 RAID 장치가 없습니다.",
                ]
            )

        if "does not appear to be active" in raw:
            return build_not_applicable(
                [
                    "비활성 상태의 RAID 장치가 발견되었습니다.",
                    "  세부 내용: mdadm: does not appear to be active",
                ]
            )

        if "MDADM_UNAVAILABLE" in raw:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "md RAID 장치가 확인되었으나 mdadm 명령어가 없어 DISK 이중화 상태를 확인할 수 없습니다.",
            }

        device_blocks = raw.split("/dev/md")
        detail_lines = []
        failed_lines = []
        found_devices = 0

        for block in device_blocks:
            stripped = block.strip()
            if not stripped or ":" not in stripped.splitlines()[0]:
                continue

            found_devices += 1
            lines = stripped.splitlines()
            device_name = f"/dev/md{lines[0].split(':', 1)[0].strip()}"
            state = ""
            failed_devices = 0
            raid_devices = 0
            active_devices = 0
            working_devices = 0
            spare_devices = 0

            for line in lines[1:]:
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "state":
                    state = value
                elif key == "failed devices":
                    failed_devices = cls._to_int(value, 0)
                elif key == "raid devices":
                    raid_devices = cls._to_int(value, 0)
                elif key == "active devices":
                    active_devices = cls._to_int(value, 0)
                elif key == "working devices":
                    working_devices = cls._to_int(value, 0)
                elif key == "spare devices":
                    spare_devices = cls._to_int(value, 0)

            detail_lines.append(
                f"{device_name} State={state or '-'} Active={active_devices}/{raid_devices} Working={working_devices} Failed={failed_devices} Spare={spare_devices}"
            )

            device_errors = []
            if "clean" not in (state or "").lower():
                device_errors.append(f"State={state or '-'}")
            if failed_devices > 0:
                device_errors.append(f"Failed={failed_devices}")
            if raid_devices > 0 and active_devices != raid_devices:
                device_errors.append(f"Active={active_devices}/{raid_devices}")
            if raid_devices > 0 and working_devices != raid_devices:
                device_errors.append(f"Working={working_devices}/{raid_devices}")

            if device_errors:
                failed_lines.append(f"비정상 RAID 장치 {device_name} " + ", ".join(device_errors))

        if found_devices == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "mdadm 출력에서 RAID 장치 정보를 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_lsvg_aix(cls, params, stdout_data):
        expected_state = str(params.get("inspection_criteria") or "syncd").strip().lower()
        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]

        header_index = -1
        state_index = -1

        for index, line in enumerate(lines[:5]):
            if "LV STATE" in line:
                header_index = index
                state_index = line.find("LV STATE")
                break

        if header_index == -1 or state_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lsvg -l rootvg 결과에서 LV STATE 컬럼을 찾을 수 없습니다.",
            }

        criteria_items = [f"모든 논리 볼륨 상태가 {expected_state} 일 것"]
        detail_lines = []
        failed_lines = []
        total_lvs = 0

        for line in lines[header_index + 1:]:
            stripped = line.strip()
            if not stripped:
                continue

            parts = stripped.split()
            if not parts:
                continue

            lv_name = parts[0]
            if len(line) <= state_index:
                continue

            lv_state = line[state_index:].strip().split()[0]
            total_lvs += 1
            detail_lines.append(f"{lv_name} 상태 {lv_state}")

            if "open/" in lv_state and expected_state not in lv_state.lower():
                failed_lines.append(f"비정상 논리 볼륨 {lv_name} 상태 {lv_state}")

        if total_lvs == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lsvg -l rootvg 결과에서 논리 볼륨 정보를 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_ioscan_fc_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or []
        abnormal_states = []
        if isinstance(criteria, list):
            abnormal_states = [str(item).upper() for item in criteria]

        lines = (stdout_data or "").splitlines()
        data_started = False
        fc_count = 0
        detail_lines = []
        failed_lines = []

        for line in lines:
            stripped = line.strip()
            if not data_started and stripped.startswith("========="):
                data_started = True
                continue
            if not data_started or not stripped:
                continue

            fc_match = cls._match_prefix(stripped, "fc")
            if not fc_match:
                continue

            fc_count += 1
            detail_lines.append(stripped)

            if "CLAIMED" not in stripped:
                failed_lines.append(f"비정상 FC 포트 {fc_match} CLAIMED 아님")

            for abnormal_state in abnormal_states:
                if abnormal_state in stripped.upper():
                    failed_lines.append(f"비정상 FC 포트 {fc_match} 상태 {abnormal_state}")
                    break

        if fc_count < 2:
            failed_lines.append(f"FC 포트 수 부족 ({fc_count}개)")

        if fc_count == 0 and not detail_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "ioscan -fnC fc 결과에서 FC 포트 정보를 찾을 수 없습니다.",
            }

        return cls._build_result(
            ["FC 포트 2개 이상 인식되고 모두 CLAIMED 상태일 것"],
            [f"FC 포트 {fc_count}개 인식"] + detail_lines,
            failed_lines,
        )

    @classmethod
    def _run_metastat_solaris(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        criteria_items = ["확인 가능한 RAID 디바이스 상태가 okay 일 것"]

        if not raw:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "metastat 결과가 비어 있습니다.",
            }

        lowered = raw.lower()
        if "ksh: metastat" in lowered or "metastat: not found" in lowered or "command not found" in lowered:
            return build_not_applicable(["DISK 이중화 구성이 확인되지 않았습니다."])

        no_db_keywords = ["there are no existing databases", "기존 데이터베이스 없음"]
        if any(keyword in lowered for keyword in no_db_keywords):
            name = params.get("name", "점검 항목")
            os_type = params.get("os", "Solaris")
            return build_not_applicable(
                [
                    "DISK 이중화 구성이 확인되지 않았습니다.",
                    f"  점검 항목: {name}",
                    f"  OS 유형: {os_type}",
                    "  세부 내용: 확인 가능한 RAID 이중화 구성이 없습니다.",
                ]
            )

        blocks = cls._split_named_blocks(raw)
        if not blocks:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "metastat 결과에서 RAID 디바이스 블록을 찾을 수 없습니다.",
            }

        detail_lines = []
        failed_lines = []

        for name, block_lines in blocks:
            state_value = ""
            for line in block_lines:
                stripped = line.strip()
                lower = stripped.lower()
                if lower.startswith("state:") or lower.startswith("상태:"):
                    state_value = stripped.split(":", 1)[1].strip()
                    break

            detail_lines.append(f"{name} 상태 {state_value or '-'}")

            if state_value and state_value.lower() not in ["okay", "정상"]:
                failed_lines.append(f"비정상 RAID 디바이스 {name} 상태 {state_value}")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_virtualdisk_windows(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return build_not_applicable(
                [
                    "DISK 이중화 구성이 확인되지 않았습니다.",
                    f"  점검 항목: {params.get('name', '점검 항목')}",
                    f"  OS 유형: {params.get('os', '-')}",
                    "  세부 내용: Storage Spaces/Virtual Disk 정보가 없습니다.",
                ]
            )

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("NOT_APPLICABLE="):
                return build_not_applicable(
                    [
                        "DISK 이중화 구성이 확인되지 않았습니다.",
                        f"  점검 항목: {params.get('name', '점검 항목')}",
                        f"  OS 유형: {params.get('os', '-')}",
                        f"  세부 내용: {stripped.split('=', 1)[1].strip()}",
                    ]
                )

        blocks = cls._parse_repeated_key_blocks(raw)
        if not blocks:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-VirtualDisk 결과에서 디스크 정보를 찾을 수 없습니다.",
            }

        criteria_items = ["모든 Virtual Disk가 이중화(Mirror/Parity) 구성이고 상태가 정상일 것"]
        detail_lines = []
        failed_lines = []
        parsed_count = 0

        for block in blocks:
            name = (block.get("name") or "-").strip()
            resiliency = (block.get("resiliency") or "-").strip()
            health = (block.get("healthstatus") or "-").strip()
            oper = (block.get("operationalstatus") or "-").strip()

            if name == "-" and resiliency == "-" and health == "-" and oper == "-":
                continue

            parsed_count += 1
            detail_lines.append(f"{name} Resiliency={resiliency} Health={health} Operational={oper}")

            if resiliency.lower() not in ["mirror", "parity"]:
                failed_lines.append(f"비정상 Virtual Disk {name} Resiliency={resiliency}")
            if health.lower() not in ["healthy", "ok"]:
                failed_lines.append(f"비정상 Virtual Disk {name} Health={health}")
            if oper.lower() not in ["ok", "online", "healthy"]:
                failed_lines.append(f"비정상 Virtual Disk {name} Operational={oper}")

        if parsed_count == 0:
            return build_not_applicable(
                [
                    "DISK 이중화 구성이 확인되지 않았습니다.",
                    f"  점검 항목: {params.get('name', '점검 항목')}",
                    f"  OS 유형: {params.get('os', '-')}",
                    "  세부 내용: Storage Spaces/Virtual Disk 구성이 없습니다.",
                ]
            )

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @staticmethod
    def _to_int(text, default=0):
        try:
            return int(str(text).strip())
        except Exception:
            return default

    @staticmethod
    def _match_prefix(text, prefix):
        parts = text.split()
        if len(parts) >= 2 and parts[0] == prefix and parts[1].isdigit():
            return f"{prefix} {parts[1]}"
        return ""

    @staticmethod
    def _split_named_blocks(stdout_data):
        blocks = []
        current_name = ""
        current_lines = []

        for line in stdout_data.splitlines():
            if line and not line.startswith((" ", "\t")) and ":" in line:
                if current_name:
                    blocks.append((current_name, current_lines))
                current_name = line.split(":", 1)[0].strip()
                current_lines = [line]
                continue

            if current_name:
                current_lines.append(line)

        if current_name:
            blocks.append((current_name, current_lines))

        return blocks

    @staticmethod
    def _parse_repeated_key_blocks(stdout_data):
        blocks = []
        current = {}

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
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
    def _to_gb_text(size_text):
        try:
            size_value = int(str(size_text).strip())
        except Exception:
            return "-"

        return f"{round(size_value / (1024 ** 3), 1)} GB"

RULE_KEY = DiskRedundancyRule.RULE_KEY
RULE_CLASS = DiskRedundancyRule
