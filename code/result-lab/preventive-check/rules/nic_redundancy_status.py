from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command

class NicRedundancyStatusRule:
    RULE_KEY = "nic_redundancy_status"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "NIC 이중화 및 Daemon 상태 정상"

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
                    "OS 자체 레벨의 NIC 이중화가 구성되지 않았습니다.",
                    f"  세부 내용: {stdout_data.strip()}",
                ]
            )

        if "cat /proc/net/bonding/bond0" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_bonding_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "ipmpstat -i" in command:
            if os_type == "Solaris":
                return cls._run_ipmpstat_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc adapter" in command and "state" in command:
            if os_type == "Aix":
                return cls._run_aix_adapter_state(params, stdout_data)
            return build_unsupported_command(params)

        if "lanadmin -g" in command:
            if os_type == "Hpux":
                return cls._run_lanadmin_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "get-netlbfoteam" in command:
            if os_type == "Windows":
                return cls._run_windows_teaming(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_items, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "NIC 이중화 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _build_linux_bonding_result(cls, criteria_items, detail_lines, failed_lines):
        if failed_lines:
            detail_lines = detail_lines + [f"비정상 사유: {', '.join(failed_lines)}"]
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "NIC 이중화 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_bonding_linux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Linux bonding 기준값은 dict 형식이어야 합니다.",
            }

        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "bonding 구성이 확인되지 않았습니다.")

        require_bond_mii_up = bool(criteria.get("require_bond_mii_up", True))
        require_current_active_slave = bool(criteria.get("require_current_active_slave", True))
        require_min_up_slaves = int(criteria.get("require_min_up_slaves", 1))
        link_failure_limit = int(criteria.get("link_failure_count_fail_over", 0))

        bond_mode = ""
        bond_mii = ""
        active_slave = ""
        slaves = []
        current_slave = None

        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            lowered = stripped.lower()
            if lowered.startswith("bonding mode:"):
                bond_mode = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("mii status:") and current_slave is None:
                bond_mii = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("currently active slave:"):
                active_slave = stripped.split(":", 1)[1].strip()
                continue
            if lowered.startswith("slave interface:"):
                if current_slave is not None:
                    slaves.append(current_slave)
                current_slave = {
                    "name": stripped.split(":", 1)[1].strip(),
                    "mii": "",
                    "speed": "",
                    "duplex": "",
                    "link_failure_count": None,
                }
                continue

            if current_slave is not None:
                if lowered.startswith("mii status:"):
                    current_slave["mii"] = stripped.split(":", 1)[1].strip()
                elif lowered.startswith("speed:"):
                    current_slave["speed"] = stripped.split(":", 1)[1].strip()
                elif lowered.startswith("duplex:"):
                    current_slave["duplex"] = stripped.split(":", 1)[1].strip()
                elif lowered.startswith("link failure count:"):
                    value = stripped.split(":", 1)[1].strip()
                    try:
                        current_slave["link_failure_count"] = int(value)
                    except Exception:
                        current_slave["link_failure_count"] = None

        if current_slave is not None:
            slaves.append(current_slave)

        criteria_items = ["bonding mode, bond 상태, slave 상태가 모두 정상일 것"]
        detail_lines = []
        failed_lines = []

        mode_token = ""
        if bond_mode:
            if "(" in bond_mode and ")" in bond_mode:
                mode_token = bond_mode.split("(", 1)[1].split(")", 1)[0].strip().lower()
            else:
                mode_token = bond_mode.lower()
            detail_lines.append(f"Bonding Mode={mode_token}")
        else:
            detail_lines.append("Bonding Mode=-")

        if require_bond_mii_up:
            detail_lines.append(f"Bond MII Status={bond_mii or '-'}")
            if not bond_mii or bond_mii.lower() != "up":
                failed_lines.append(f"비정상 Bond MII Status {bond_mii or '-'}")

        if require_current_active_slave:
            detail_lines.append(f"Current Active Slave={active_slave or '-'}")
            if not active_slave or active_slave.lower() in ["none", "-"]:
                failed_lines.append("Currently Active Slave 없음")

        if not slaves:
            return cls._build_not_applicable(params, "bonding slave 정보가 없습니다.")

        up_slaves = 0
        for slave in slaves:
            name = slave["name"] or "-"
            mii = (slave["mii"] or "-").strip()
            speed = (slave["speed"] or "-").strip()
            duplex = (slave["duplex"] or "-").strip()
            link_fail = slave["link_failure_count"]
            detail_lines.append(
                f"Slave {name} MII={mii} Speed={speed} Duplex={duplex} LinkFailureCount={link_fail if link_fail is not None else '-'}"
            )

            if mii.lower() == "up":
                up_slaves += 1
            else:
                failed_lines.append(f"비정상 Slave {name} MII={mii}")

            if link_fail is None:
                failed_lines.append(f"비정상 Slave {name} Link Failure Count 미출력")
            elif link_fail > link_failure_limit:
                failed_lines.append(f"비정상 Slave {name} Link Failure Count={link_fail}")

        if up_slaves < require_min_up_slaves:
            failed_lines.append(f"UP Slave 부족 {up_slaves}개")

        detail_lines.append(f"UP Slave 수={up_slaves}개")
        return cls._build_linux_bonding_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_ipmpstat_solaris(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Solaris IPMP 기준값은 dict 형식이어야 합니다.",
            }

        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "IPMP 구성이 확인되지 않았습니다.")

        min_ifaces = int(criteria.get("min_ifaces_per_group", 2))
        required_active = str(criteria.get("required_active", "yes")).strip().lower()
        required_link = str(criteria.get("required_link", "up")).strip().lower()
        required_state = str(criteria.get("required_state", "ok")).strip().lower()

        lines = [line.strip() for line in raw.splitlines() if line.strip()]
        parsed = []

        for line in lines:
            lower = line.lower()
            if lower.startswith("ifname") or set(line) == {"-"}:
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            if len(parts) >= 7:
                link_value = parts[-3].lower()
                state_value = parts[-1].lower()
            else:
                link_value = parts[-2].lower()
                state_value = parts[-1].lower()
            parsed.append(
                {
                    "ifname": parts[0],
                    "active": parts[1].lower(),
                    "group": parts[2],
                    "link": link_value,
                    "state": state_value,
                }
            )

        if not parsed:
            return cls._build_not_applicable(params, "IPMP 인터페이스 정보가 없습니다.")

        criteria_items = ["IPMP 그룹 인터페이스 수와 ACTIVE/LINK/STATE 가 정상일 것"]
        detail_lines = []
        failed_lines = []
        group_counts = {}

        for item in parsed:
            iface = item["ifname"]
            group = item["group"]
            active = item["active"]
            link = item["link"]
            state = item["state"]
            group_counts[group] = group_counts.get(group, 0) + 1
            detail_lines.append(f"{iface}({group}) ACTIVE={active} LINK={link} STATE={state}")

            if active != required_active:
                failed_lines.append(f"비정상 IPMP {iface} ACTIVE={active}")
            if link != required_link:
                failed_lines.append(f"비정상 IPMP {iface} LINK={link}")
            if state != required_state:
                failed_lines.append(f"비정상 IPMP {iface} STATE={state}")

        for group, count in group_counts.items():
            if count < min_ifaces:
                failed_lines.append(f"비정상 IPMP 그룹 {group} 인터페이스 수 {count}")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_aix_adapter_state(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "AIX NIC 이중화 기준값은 dict 형식이어야 합니다.",
            }

        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "AIX NIC 이중화 구성이 확인되지 않았습니다.")

        primary_ok = str(criteria.get("primary", "ACTIVE")).strip()
        backup_ok = str(criteria.get("backup", "STANDBY")).strip()

        blocks = {}
        current = ""
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                current = stripped[1:-1].strip()
                blocks.setdefault(current, {"primary": [], "backup": []})
                continue
            if current:
                if "Primary Adapter State:" in stripped:
                    blocks[current]["primary"].append(stripped.split(":", 1)[1].strip())
                elif "Backup Adapter State:" in stripped:
                    blocks[current]["backup"].append(stripped.split(":", 1)[1].strip())

        if not blocks:
            return cls._build_not_applicable(params, "AIX NIC 이중화 블록이 없습니다.")

        criteria_items = [f"Primary={primary_ok}, Backup={backup_ok} 조합이 유지될 것"]
        detail_lines = []
        failed_lines = []
        valid_pairs = 0

        for device, data in blocks.items():
            pair_count = min(len(data["primary"]), len(data["backup"]))
            if pair_count == 0:
                detail_lines.append(f"{device} 상태 정보 없음")
                continue
            for index in range(pair_count):
                valid_pairs += 1
                primary = data["primary"][index]
                backup = data["backup"][index]
                detail_lines.append(f"{device} Primary={primary} Backup={backup}")
                if primary != primary_ok or backup != backup_ok:
                    failed_lines.append(f"비정상 NIC 이중화 {device} Primary={primary} Backup={backup}")
                    break

        if valid_pairs == 0:
            return cls._build_not_applicable(params, "AIX NIC 이중화 상태 정보가 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_lanadmin_hpux(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "LinkAgg 구성이 확인되지 않았습니다.")

        blocks = raw.split("PPA Number")
        parsed_blocks = []
        for block in blocks[1:]:
            text = "PPA Number" + block
            parsed_blocks.append(text)

        if not parsed_blocks:
            return cls._build_not_applicable(params, "LinkAgg PPA 정보를 찾을 수 없습니다.")

        criteria_items = ["Administration/Operation Status 가 UP 이고 에러 카운터가 0 일 것"]
        detail_lines = []
        failed_lines = []

        for block in parsed_blocks:
            ppa = cls._extract_after_equals(block, "PPA Number")
            admin = cls._extract_after_equals(block, "Administration Status")
            oper = cls._extract_after_equals(block, "Operation Status")
            inbound_errors = cls._extract_int_after_equals(block, "Inbound Errors")
            outbound_errors = cls._extract_int_after_equals(block, "Outbound Errors")
            inbound_discards = cls._extract_int_after_equals(block, "Inbound Discards")
            outbound_discards = cls._extract_int_after_equals(block, "Outbound Discards")

            label = f"PPA {ppa or '-'}"
            detail_lines.append(
                f"{label} Admin={admin or '-'} Oper={oper or '-'} InErr={inbound_errors} OutErr={outbound_errors} InDisc={inbound_discards} OutDisc={outbound_discards}"
            )

            if not cls._is_hpux_up(admin):
                failed_lines.append(f"비정상 LinkAgg {label} Administration Status={admin or '-'}")
            if not cls._is_hpux_up(oper):
                failed_lines.append(f"비정상 LinkAgg {label} Operation Status={oper or '-'}")
            if inbound_errors > 0:
                failed_lines.append(f"비정상 LinkAgg {label} Inbound Errors={inbound_errors}")
            if outbound_errors > 0:
                failed_lines.append(f"비정상 LinkAgg {label} Outbound Errors={outbound_errors}")
            if inbound_discards > 0:
                failed_lines.append(f"비정상 LinkAgg {label} Inbound Discards={inbound_discards}")
            if outbound_discards > 0:
                failed_lines.append(f"비정상 LinkAgg {label} Outbound Discards={outbound_discards}")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _run_windows_teaming(cls, params, stdout_data):
        raw = (stdout_data or "").strip()
        if not raw:
            return cls._build_not_applicable(params, "NIC Teaming 결과가 없습니다.")

        for line in raw.splitlines():
            stripped = line.strip()
            if stripped.startswith("NOT_APPLICABLE="):
                return cls._build_not_applicable(params, stripped.split("=", 1)[1].strip())

        blocks = cls._parse_repeated_key_blocks(raw)
        if not blocks:
            return cls._build_not_applicable(params, "NIC Teaming 블록이 없습니다.")

        criteria = params.get("inspection_criteria") or {}
        status_ok = str(criteria.get("status_ok", "Up")).strip().lower()
        min_members = int(criteria.get("min_members", 2))

        criteria_items = [f"NIC Team 상태가 {status_ok} 이고 멤버 수가 {min_members}개 이상일 것"]
        detail_lines = []
        failed_lines = []
        parsed_count = 0

        for block in blocks:
            name = (block.get("name") or "-").strip()
            status = (block.get("status") or "-").strip()
            mode = (block.get("mode") or "-").strip()
            members = cls._to_int(block.get("members"), 0)

            if name == "-" and status == "-" and mode == "-" and members == 0:
                continue

            parsed_count += 1
            detail_lines.append(f"{name} Status={status} Mode={mode} Members={members}")

            if (status or "").lower() != status_ok:
                failed_lines.append(f"비정상 NIC Team {name} Status={status or '-'}")
            if members < min_members:
                failed_lines.append(f"비정상 NIC Team {name} Members={members}")

        if parsed_count == 0:
            return cls._build_not_applicable(params, "NIC Team 구성이 없습니다.")

        return cls._build_result(criteria_items, detail_lines, failed_lines)

    @classmethod
    def _build_not_applicable(cls, params, detail):
        return build_not_applicable(
            [
                "NIC 이중화 구성이 확인되지 않았습니다.",
                f"  점검 항목: {params.get('name', '점검 항목')}",
                f"  OS 유형: {params.get('os', '-')}",
                f"  세부 내용: {detail}",
            ]
        )

    @staticmethod
    def _extract_after_equals(text, key):
        for line in (text or "").splitlines():
            stripped = line.strip()
            if stripped.startswith(key) and "=" in stripped:
                return stripped.split("=", 1)[1].strip()
        return ""

    @staticmethod
    def _extract_int_after_equals(text, key):
        value = NicRedundancyStatusRule._extract_after_equals(text, key)
        return NicRedundancyStatusRule._to_int(value, 0)

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @staticmethod
    def _is_hpux_up(value):
        normalized = str(value or "").strip().lower()
        return normalized == "up" or normalized.startswith("up(")

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

RULE_KEY = NicRedundancyStatusRule.RULE_KEY
RULE_CLASS = NicRedundancyStatusRule
