import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class UnusedInterfaceRule:
    RULE_KEY = "sec_unused_interface"
    CRITERIA_TEXT = "사용하지 않는 인터페이스의 Shutdown 설정"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def allow_empty_output(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return cls.CRITERIA_TEXT

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = cls._normalize_os(params.get("os"))

        if os_type == "alteonl4":
            return cls._run_alteon(params, command, stdout_data)
        if os_type == "arista":
            return cls._run_show_ip_interface(params, command, stdout_data)
        if os_type == "citrix":
            return cls._run_citrix(params, command, stdout_data)
        if os_type in ("cisco",):
            return cls._run_show_ip_interface(params, command, stdout_data)
        if os_type in ("piolink",):
            return cls._run_piolink(params, command, stdout_data)

        return build_unsupported_command(params)

    @classmethod
    def _run_alteon(cls, params, command, stdout_data):
        if command != "info":
            return build_unsupported_command(params)
        return build_not_applicable("인터페이스 상태 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        interfaces = cls._parse_citrix_interfaces(stdout_data)
        return cls._build_result(interfaces)

    @classmethod
    def _run_show_ip_interface(cls, params, command, stdout_data):
        if "show ip interface" not in command:
            return build_unsupported_command(params)
        interfaces = cls._parse_show_ip_interface(stdout_data)
        return cls._build_result(interfaces)

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        interfaces = cls._parse_piolink_interfaces(stdout_data)
        return cls._build_result(interfaces)

    @classmethod
    def _build_result(cls, interfaces):
        if not interfaces:
            return build_not_applicable("인터페이스 상태 설정 라인이 확인되지 않습니다.")

        failed = []
        detail_lines = []
        checked = 0

        for item in interfaces:
            name = item["name"]
            status = item["status"]
            unused = item["unused"]
            if not unused:
                continue
            checked += 1
            if item["shutdown"]:
                detail_lines.append(f"{name} {status}")
            else:
                failed.append(f"{name} {status}")
                detail_lines.append(f"비정상 미사용 인터페이스 활성화: {name} {status}")

        if checked == 0:
            detail_lines.append("미사용 인터페이스 대상 미검출")
        elif not failed:
            detail_lines.append("미사용 인터페이스 Shutdown 설정 기준 이내")

        return {
            "is_success": 1,
            "is_pass": 0 if failed else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed else "기준 이내",
            "detail_lines": detail_lines,
        }

    @staticmethod
    def _parse_show_ip_interface(raw):
        interfaces = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            match = re.match(r"^(\S+)\s+.*\s+(administratively down|up|down)\s+(up|down)$", stripped)
            if match:
                name = match.group(1)
                status = f"status={match.group(2)} protocol={match.group(3)}"
                shutdown = "administratively down" in lowered
                unused = "unassigned" in lowered or shutdown
                interfaces.append({"name": name, "status": status, "unused": unused, "shutdown": shutdown})
                continue
            match = re.match(r"^(\S+)\s+is\s+(administratively down|up|down),\s+line protocol is\s+(up|down)", stripped, re.IGNORECASE)
            if match:
                name = match.group(1)
                status = f"status={match.group(2)} protocol={match.group(3)}"
                shutdown = match.group(2).lower() == "administratively down"
                unused = shutdown or "internet protocol processing disabled" in lowered
                interfaces.append({"name": name, "status": status, "unused": unused, "shutdown": shutdown})
        return interfaces

    @staticmethod
    def _parse_citrix_interfaces(raw):
        interfaces = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^set\s+interface\s+(\S+)\s+(.+)$", stripped, re.IGNORECASE)
            if not match:
                continue
            body = match.group(2).lower()
            disabled = "-hamonitor off" in body and "-throughput 0" in body
            interfaces.append(
                {
                    "name": match.group(1),
                    "status": "haMonitor=OFF throughput=0" if disabled else "상태 정보 확인 필요",
                    "unused": disabled,
                    "shutdown": disabled,
                }
            )
        return interfaces

    @staticmethod
    def _parse_piolink_interfaces(raw):
        interfaces = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^interface\s+(\S+)\s+status\s+(\S+)", stripped, re.IGNORECASE)
            if not match:
                continue
            name = match.group(1)
            state = match.group(2).lower()
            unused = name.lower() == "default" or state == "down"
            interfaces.append(
                {
                    "name": name,
                    "status": f"status={state}",
                    "unused": unused,
                    "shutdown": state == "down",
                }
            )
        return interfaces

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = UnusedInterfaceRule.RULE_KEY
RULE_CLASS = UnusedInterfaceRule
