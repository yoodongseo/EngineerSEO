from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class HbaConnectionStatusRule:
    RULE_KEY = "hba_connection_status"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "HBA 상태 Online 및 속도 정상"
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

        missing_markers = ["command not found", "not found", "no such file or directory", "is not recognized", "찾을 수 없습니다"]
        low_out = (stdout_data or "").lower()
        if any(marker in low_out for marker in missing_markers):
            return build_not_applicable(
                [
                    "HBA 카드가 장착되지 않았거나 관련 명령어가 존재하지 않습니다.",
                    f"  세부 내용: {stdout_data.strip()}",
                ]
            )

        if "port_state" in command and "/sys/class/fc_host/host" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "fcinfo hba-port" in command:
            if os_type == "Solaris":
                return cls._run_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "fcstat" in command:
            if os_type == "Aix":
                return cls._run_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "fcmsutil" in command:
            if os_type == "Hpux":
                return cls._run_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "get-initiatorport" in command:
            if os_type == "Windows":
                return cls._run_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "HBA 연결 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _run_linux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "FC HBA host 정보가 없습니다.")

        criteria_items = ["모든 FC HBA host가 online 상태이고 speed 값이 정상일 것"]
        detail_lines = []
        failed_lines = []
        count = 0

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped.startswith("[host"):
                continue

            count += 1
            parts = stripped.split()
            host = parts[0].strip("[]")
            state = parts[1].strip() if len(parts) > 1 else ""
            speed = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
            detail_lines.append(f"{host} 상태 {state or '-'} 속도 {speed or '-'}")

            if state.lower() != "online":
                failed_lines.append(f"비정상 HBA {host} 상태 {state or '-'}")

            speed_lower = speed.lower()
            if not speed or "unknown" in speed_lower or "0 gbit" in speed_lower:
                failed_lines.append(f"비정상 HBA {host} 속도 {speed or '-'}")

        if count == 0:
            return cls._build_not_applicable(params, "FC HBA host 정보가 없습니다.")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_solaris(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "FC HBA port 정보가 없습니다.")

        expected_state = str(params.get("inspection_criteria") or "online").strip().lower()
        blocks = cls._split_by_prefix(raw, "HBA Port WWN:")
        if not blocks:
            return cls._build_not_applicable(params, "FC HBA port 정보가 없습니다.")

        criteria_items = [f"모든 HBA Port 상태가 {expected_state} 이고 Current speed 값이 정상일 것"]
        detail_lines = []
        failed_lines = []

        for title, lines in blocks:
            wwn = title.split(":", 1)[1].strip() if ":" in title else title.strip()
            state = cls._extract_colon_value(lines, "State")
            speed = cls._extract_colon_value(lines, "Current Speed")
            detail_lines.append(f"{wwn} 상태 {state or '-'} 속도 {speed or '-'}")

            if (state or "").strip().lower() != expected_state:
                failed_lines.append(f"비정상 HBA Port {wwn} 상태 {state or '-'}")

            speed_lower = (speed or "").lower()
            if not speed or "unknown" in speed_lower or "0 gb" in speed_lower or "0g" in speed_lower:
                failed_lines.append(f"비정상 HBA Port {wwn} 속도 {speed or '-'}")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_aix(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "HBA 어댑터 정보가 없습니다.")

        fail_value = str(params.get("inspection_criteria") or "Link Down").strip()
        blocks = cls._split_bracket_blocks(raw, "fcs")
        if not blocks:
            return cls._build_not_applicable(params, "HBA 어댑터 정보가 없습니다.")

        criteria_items = [f"모든 HBA Attention Type 이 {fail_value} 가 아닐 것"]
        detail_lines = []
        failed_lines = []

        for name, lines in blocks:
            joined = "\n".join(lines)
            if "Error opening device" in joined:
                failed_lines.append(f"비정상 HBA {name} 장치 열기 실패")
                continue

            attention = cls._extract_colon_value(lines, "Attention Type")
            detail_lines.append(f"{name} Attention Type {attention or '-'}")

            if not attention:
                failed_lines.append(f"비정상 HBA {name} Attention Type 미출력")
            elif attention.strip().lower() == fail_value.lower():
                failed_lines.append(f"비정상 HBA {name} Attention Type {attention}")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_hpux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "HBA 포트 정보가 없습니다.")

        ok_states = params.get("inspection_criteria") or ["ONLINE", "LINK_UP"]
        ok_states = [str(item).upper() for item in ok_states]
        blocks = cls._split_equals_blocks(raw, "Link Speed")
        if not blocks:
            return cls._build_not_applicable(params, "HBA 포트 정보가 없습니다.")

        criteria_items = ["모든 HBA 포트의 Driver state 와 Link Speed 가 정상일 것"]
        detail_lines = []
        failed_lines = []

        for idx, block in enumerate(blocks, start=1):
            lines = block.splitlines()
            speed_line = next((line for line in lines if "Link Speed" in line), "")
            port_name_line = next((line for line in lines if "Port Name" in line), "")
            driver_state_line = next((line for line in lines if "driver state" in line.lower()), "")

            port_name = port_name_line.split("=", 1)[1].strip() if "=" in port_name_line else f"port#{idx}"
            driver_state = driver_state_line.split("=", 1)[1].strip() if "=" in driver_state_line else ""
            speed = speed_line.split("=", 1)[1].strip() if "=" in speed_line else ""

            detail_lines.append(f"{port_name} 상태 {driver_state or '-'} 속도 {speed or '-'}")

            if not driver_state or not any(token in driver_state.upper() for token in ok_states):
                failed_lines.append(f"비정상 HBA {port_name} 상태 {driver_state or '-'}")

            speed_upper = speed.upper()
            if not speed or "UNKNOWN" in speed_upper or speed_upper.startswith("0"):
                failed_lines.append(f"비정상 HBA {port_name} 속도 {speed or '-'}")

        return cls._build_result(criteria_items, detail_lines, cls._dedupe(failed_lines))

    @classmethod
    def _run_windows(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "Get-InitiatorPort 결과가 없습니다.")

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("NOT_APPLICABLE="):
                return cls._build_not_applicable(params, stripped.split("=", 1)[1].strip())

        blocks = cls._parse_repeated_key_blocks(raw)
        if not blocks:
            return cls._build_not_applicable(params, "Get-InitiatorPort 결과가 없습니다.")

        criteria_items = ["모든 Initiator Port 상태가 Online/Up 일 것"]
        detail_lines = []
        failed_lines = []
        checked_count = 0

        for block in blocks:
            node = (block.get("nodeaddress") or block.get("portaddress") or "-").strip()
            state = (block.get("portstate") or block.get("status") or "-").strip()
            conn = (block.get("connectiontype") or "-").strip()
            if not cls._is_windows_fc_connection(conn):
                continue

            checked_count += 1
            detail_lines.append(f"{node} 상태 {state} 연결형식 {conn}")

            if state.lower() not in ["online", "up", "active", "ok"]:
                failed_lines.append(f"비정상 HBA Port {node} 상태 {state}")

        if checked_count == 0:
            return cls._build_not_applicable(params, "FC HBA Initiator Port 정보가 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _build_not_applicable(cls, params, detail):
        return build_not_applicable(
            [
                "HBA 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @staticmethod
    def _split_by_prefix(stdout_data, prefix):
        blocks = []
        current_title = ""
        current_lines = []

        for raw_line in stdout_data.splitlines():
            line = raw_line.strip()
            if line.startswith(prefix):
                if current_title:
                    blocks.append((current_title, current_lines))
                current_title = line
                current_lines = []
                continue
            if current_title:
                current_lines.append(line)

        if current_title:
            blocks.append((current_title, current_lines))

        return blocks

    @staticmethod
    def _split_bracket_blocks(stdout_data, prefix):
        blocks = []
        current_name = ""
        current_lines = []

        for raw_line in stdout_data.splitlines():
            line = raw_line.strip()
            if line.startswith(f"[{prefix}") and line.endswith("]"):
                if current_name:
                    blocks.append((current_name, current_lines))
                current_name = line.strip("[]")
                current_lines = []
                continue
            if current_name:
                current_lines.append(line)

        if current_name:
            blocks.append((current_name, current_lines))

        return blocks

    @staticmethod
    def _split_equals_blocks(stdout_data, marker):
        blocks = []
        current = []
        for raw_line in stdout_data.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if marker in line and current:
                blocks.append("\n".join(current))
                current = [line]
                continue
            current.append(line)
        if current:
            blocks.append("\n".join(current))
        return blocks

    @staticmethod
    def _extract_colon_value(lines, key):
        key_lower = key.lower()
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith(f"{key_lower}:"):
                return stripped.split(":", 1)[1].strip()
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
    def _is_windows_fc_connection(value):
        normalized = str(value or "").strip().lower()
        return normalized in ["fc", "fibre channel", "fibrechannel", "fiber channel", "fiberchannel"]

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

RULE_KEY = HbaConnectionStatusRule.RULE_KEY
RULE_CLASS = HbaConnectionStatusRule
