import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class NetworkLinkStatusRule:
    RULE_KEY = "network_link_status"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        return "NIC 링크 상태 정상"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "ip link" in command or "ifconfig" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_ip_link_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "dladm show-dev" in command:
            if os_type == "Solaris":
                return cls._run_dladm_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc adapter" in command and "entstat -d" in command:
            if os_type == "Aix":
                return cls._run_entstat_aix(params, stdout_data)
            return build_unsupported_command(params)

        if command == "lanscan":
            if os_type == "Hpux":
                return cls._run_lanscan_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic nic" in command:
            if os_type == "Windows":
                return cls._run_windows_wmic(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "NW 링크 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _run_ip_link_linux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        targets = []
        match_type = "exact"

        if isinstance(criteria, dict):
            match_type = str(criteria.get("match_type", "exact")).strip().lower()
            values = criteria.get("values", [])
            if isinstance(values, list):
                targets = [str(value).strip().lower() for value in values if str(value).strip()]
        elif isinstance(criteria, list):
            targets = [str(value).strip().lower() for value in criteria if str(value).strip()]

        if not targets:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "점검 대상 NIC 기준값이 선언되지 않았습니다.",
            }

        parsed = {}
        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            iface, flags, state = cls._parse_ip_link_header(stripped)
            if iface:
                parsed[iface.lower()] = {"iface": iface, "flags": flags, "state": state}

        if not parsed:
            parsed = cls._parse_ifconfig_linux(stdout_data)

        selected_keys = []
        if match_type == "prefix":
            for key in parsed:
                if any(key.startswith(target) for target in targets):
                    selected_keys.append(key)
        else:
            for target in targets:
                if target in parsed:
                    selected_keys.append(target)

        if not selected_keys:
            target_text = ", ".join(targets)
            return build_not_applicable([
                f"점검 기준에 명시된 NIC({match_type}: {target_text})가 ip link 결과에 없습니다."
            ])

        criteria_items = ["점검 대상 NIC state가 UP이고 flags에 UP/LOWER_UP 이 있을 것"]
        detail_lines = []
        failed_lines = []

        for key in selected_keys:
            info = parsed[key]
            iface = info["iface"]
            flags = info["flags"]
            state = info["state"]
            detail_lines.append(f"{iface} state={state} flags={','.join(flags)}")

            if state != "UP":
                failed_lines.append(f"비정상 NIC {iface} state={state}")
            if "UP" not in flags:
                failed_lines.append(f"비정상 NIC {iface} flags에 UP 없음")
            if "LOWER_UP" not in flags:
                failed_lines.append(f"비정상 NIC {iface} flags에 LOWER_UP 없음")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_dladm_solaris(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        link_ok = str(criteria.get("link_ok", "up")).strip().lower() if isinstance(criteria, dict) else "up"

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        data_lines = []
        for line in lines:
            lower = line.lower()
            if lower.startswith("link ") or set(line) == {"-"}:
                continue
            data_lines.append(line)

        if not data_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dladm show-dev 결과에서 NIC 데이터를 찾을 수 없습니다.",
            }

        criteria_items = [f"모든 NIC STATE가 {link_ok} 일 것"]
        detail_lines = []
        failed_lines = []

        for line in data_lines:
            match = re.match(
                r"^(?P<link>\S+)\s+link:\s+(?P<state>\S+)\s+speed:\s+(?P<speed>\S+)\s+\S+\s+duplex:\s+(?P<duplex>\S+)$",
                line,
                re.IGNORECASE,
            )
            if not match:
                continue
            link_name = match.group("link")
            state = match.group("state").lower()
            speed = match.group("speed")
            duplex = match.group("duplex").lower()
            detail_lines.append(f"{link_name} state={state} speed={speed}Mbps duplex={duplex}")
            if state != link_ok:
                failed_lines.append(f"비정상 NIC {link_name} state={state}")

        if not detail_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dladm show-dev 결과에서 유효한 NIC 라인을 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_entstat_aix(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "AIX 점검 기준값은 dict 형식이어야 합니다.",
            }

        physical_target = str(criteria.get("physical", "Up")).strip()
        logical_target = str(criteria.get("logical", "Down")).strip()

        blocks = {}
        current_device = ""

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                current_device = stripped[1:-1].strip()
                blocks.setdefault(current_device, {"physical": [], "logical": []})
                continue
            if current_device:
                if "Physical Port Link Status:" in stripped:
                    blocks[current_device]["physical"].append(stripped.split(":", 1)[1].strip())
                elif "Logical Port Link Status:" in stripped:
                    blocks[current_device]["logical"].append(stripped.split(":", 1)[1].strip())

        if not blocks:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "AIX 네트워크 링크 상태 블록을 찾을 수 없습니다.",
            }

        criteria_items = [f"Physical={physical_target} 이고 Logical={logical_target} 인 포트 조합이 없을 것"]
        detail_lines = []
        failed_lines = []
        valid_pairs = 0
        up_up_pairs = 0

        for device, data in blocks.items():
            physical_list = data.get("physical", [])
            logical_list = data.get("logical", [])
            pair_count = min(len(physical_list), len(logical_list))

            if pair_count == 0:
                detail_lines.append(f"{device} 링크 정보 없음")
                continue

            for index in range(pair_count):
                physical = physical_list[index]
                logical = logical_list[index]
                valid_pairs += 1
                if physical == physical_target and logical == logical_target:
                    detail_lines.append(f"{device} Physical={physical} Logical={logical}")
                    failed_lines.append(f"비정상 NIC {device} Physical={physical} Logical={logical}")
                    break
                if physical.lower() == "up" and logical.lower() == "up":
                    up_up_pairs += 1
                    detail_lines.append(f"{device} Physical={physical} Logical={logical}")

        if valid_pairs == 0:
            return build_not_applicable(["AIX 네트워크 링크 상태를 확인할 수 있는 포트 정보가 없습니다."])

        if up_up_pairs == 0 and not failed_lines:
            return build_not_applicable(["AIX 네트워크 링크가 UP 상태인 점검 대상 포트가 없습니다."])

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_lanscan_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or []
        target_names = []
        if isinstance(criteria, list):
            target_names = [str(item).strip().lower() for item in criteria if str(item).strip()]

        lines = (stdout_data or "").splitlines()
        data_started = False
        detail_lines = []
        failed_lines = []
        matched_count = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if not data_started and stripped.startswith("Hardware"):
                data_started = True
                continue
            if not data_started:
                continue

            parts = stripped.split()
            if len(parts) < 6:
                continue

            state = parts[3].upper()
            if state == "STATE" or parts[4].lower() == "nameppa":
                continue

            path_or_linkagg = parts[0]
            name = parts[4]
            lowered_name = name.lower()
            lowered_path = path_or_linkagg.lower()

            if target_names and lowered_name not in target_names and lowered_path not in target_names:
                continue

            matched_count += 1
            detail_lines.append(f"{name} state={state}")
            if state != "UP":
                failed_lines.append(f"비정상 NIC {name} state={state}")

        if matched_count == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lanscan 결과에서 점검 대상 NIC를 찾을 수 없습니다.",
            }

        return cls._build_result(["점검 대상 NIC 상태가 UP 일 것"], detail_lines, failed_lines)

    @classmethod
    def _run_windows_wmic(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        min_speed_mbps = None
        if isinstance(criteria, dict) and criteria.get("min_speed_mbps") is not None:
            try:
                min_speed_mbps = float(criteria.get("min_speed_mbps"))
            except Exception:
                min_speed_mbps = None

        blocks = cls._parse_repeated_key_blocks(stdout_data)
        detail_lines = []
        failed_lines = []
        checked = 0
        for block in blocks:
            name = (block.get("name") or block.get("netconnectionid") or "(unknown)").strip()
            adapter_type = (block.get("adaptertype") or "").strip().lower()
            physical = (block.get("physicaladapter") or "").strip().lower()
            if physical not in ["true", "1"]:
                continue
            if adapter_type and "ethernet 802.3" not in adapter_type and "ethernet" not in adapter_type:
                continue

            net_enabled = (block.get("netenabled") or "").strip().lower()
            status_code = (block.get("netconnectionstatus") or "").strip()
            speed_mbps = cls._resolve_speed_from_text(block.get("speed"))
            checked += 1

            if net_enabled == "true" or status_code == "2":
                normalized_state = "UP"
            elif net_enabled == "false" or status_code in ["0", "7"]:
                normalized_state = "DOWN"
            else:
                normalized_state = "UNKNOWN"
            speed_text = "-" if speed_mbps is None else f"{speed_mbps:.1f}Mbps"
            detail_lines.append(f"{name} state={normalized_state} speed={speed_text}")

            if normalized_state != "UP":
                failed_lines.append(f"비정상 NIC {name} state={normalized_state}")
            elif speed_mbps is None:
                failed_lines.append(f"비정상 NIC {name} speed 미확인")
            elif min_speed_mbps is not None and speed_mbps < min_speed_mbps:
                failed_lines.append(f"비정상 NIC {name} speed={speed_mbps:.1f}Mbps")

        if checked == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Windows NIC 상태 결과에서 점검 대상 인터페이스를 찾을 수 없습니다.",
            }

        criteria_items = ["물리 NIC state가 UP 이고 속도가 확인될 것"]
        if min_speed_mbps is not None:
            criteria_items.append(f"속도 {min_speed_mbps:.1f}Mbps 이상일 것")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @staticmethod
    def _parse_ip_link_header(line):
        if not line or ": " not in line or "<" not in line or ">" not in line:
            return "", [], ""

        first_colon = line.find(":")
        second_colon = line.find(":", first_colon + 1)
        if second_colon == -1:
            return "", [], ""

        iface = line[first_colon + 1:second_colon].strip()
        flag_start = line.find("<", second_colon)
        flag_end = line.find(">", flag_start + 1)
        if flag_start == -1 or flag_end == -1:
            return "", [], ""

        flags = [flag.strip().upper() for flag in line[flag_start + 1:flag_end].split(",") if flag.strip()]
        state_index = line.find(" state ", flag_end)
        if state_index != -1:
            state_value = line[state_index + len(" state "):].split()[0].strip().upper()
        elif "UP" in flags and "LOWER_UP" in flags and "NO-CARRIER" not in flags:
            state_value = "UP"
        else:
            state_value = "DOWN"
        return iface, flags, state_value

    @staticmethod
    def _parse_ifconfig_linux(stdout_data):
        parsed = {}
        current_iface = ""
        current_flags = []

        for raw_line in (stdout_data or "").splitlines():
            line = raw_line.rstrip()
            if not line:
                continue

            if line[0] not in (" ", "\t") and not line.startswith("\t"):
                current_iface = line.split()[0].split(":", 1)[0].strip()
                current_flags = []
                parsed[current_iface.lower()] = {
                    "iface": current_iface,
                    "flags": current_flags,
                    "state": "DOWN",
                }
                continue

            if current_iface:
                tokens = [token.strip().upper() for token in line.strip().split() if token.strip()]
                current_flags.extend(tokens)
                if "UP" in tokens:
                    parsed[current_iface.lower()]["state"] = "UP"
                if "RUNNING" in tokens and "LOWER_UP" not in parsed[current_iface.lower()]["flags"]:
                    parsed[current_iface.lower()]["flags"].append("LOWER_UP")

        for info in parsed.values():
            if "UP" in info["flags"]:
                info["state"] = "UP"

        return parsed

    @staticmethod
    def _resolve_speed_from_text(speed_text):
        speed_text = str(speed_text or "").strip()
        if not speed_text:
            return None

        try:
            speed_bps = float(speed_text)
        except Exception:
            return None

        if speed_bps <= 0:
            return None

        return speed_bps / 1000000.0

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

RULE_KEY = NetworkLinkStatusRule.RULE_KEY
RULE_CLASS = NetworkLinkStatusRule
