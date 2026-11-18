import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class PlainServicePortRule:
    RULE_KEY = "sec_plain_service"
    CRITERIA_TEXT = "FTP(20,21), Telnet(23), Rlogin(513), Rshell/Rcp(514), Rexec(512) 등 제거"

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
            return cls._run_arista(params, command, stdout_data)
        if os_type == "citrix":
            return cls._run_citrix(params, command, stdout_data)
        if os_type in ("cisco",):
            return cls._run_router(params, command, stdout_data)
        if os_type in ("piolink",):
            return cls._run_piolink(params, command, stdout_data)

        return build_unsupported_command(params)

    @classmethod
    def _run_alteon(cls, params, command, stdout_data):
        if command != "info":
            return build_unsupported_command(params)
        return build_not_applicable("평문 서비스 포트 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_generic_enabled_lines(stdout_data))

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_cisco_enabled_lines(stdout_data))

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_generic_enabled_lines(stdout_data))

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_piolink_enabled_lines(stdout_data))

    @classmethod
    def _build_result(cls, failed_lines):
        detail_lines = [f"비정상 평문 서비스 활성화: {line}" for line in failed_lines]
        if not detail_lines:
            detail_lines = ["평문 서비스 활성화 설정 미검출"]

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _extract_cisco_enabled_lines(cls, raw):
        failed = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or lowered.startswith("no "):
                continue
            if re.search(r"\btransport\s+input\b.*\b(telnet|all)\b", lowered):
                failed.append(stripped)
            elif re.search(r"\bip\s+ftp\s+server\b", lowered):
                failed.append(stripped)
            elif cls._contains_plain_service_port(lowered):
                failed.append(stripped)
        return failed

    @classmethod
    def _extract_piolink_enabled_lines(cls, raw):
        failed = []
        service_status = {}
        service_port = {}

        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            status_match = re.match(r"^(telnet|ftp|rlogin|rshell|rcp|rexec)\s+status\s+(\S+)", lowered)
            port_match = re.match(r"^(telnet|ftp|rlogin|rshell|rcp|rexec)\s+port\s+(\d+)", lowered)
            if status_match:
                service_status[status_match.group(1)] = status_match.group(2)
                if status_match.group(2) == "enable":
                    failed.append(stripped)
            elif port_match:
                service_port[port_match.group(1)] = port_match.group(2)

        for service, status in service_status.items():
            if status == "enable" and service in service_port:
                failed.append(f"{service} port {service_port[service]}")
        return failed

    @classmethod
    def _extract_generic_enabled_lines(cls, raw):
        failed = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or lowered.startswith(("no ", "#", "!")):
                continue
            if cls._contains_plain_service_name(lowered) or cls._contains_plain_service_port(lowered):
                failed.append(stripped)
        return failed

    @staticmethod
    def _contains_plain_service_name(line):
        return bool(re.search(r"\b(telnet|ftp|rlogin|rshell|rcp|rexec)\b", line))

    @staticmethod
    def _contains_plain_service_port(line):
        return bool(re.search(r"\b(port|tcp|udp)\s+(20|21|23|512|513|514)\b", line))

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = PlainServicePortRule.RULE_KEY
RULE_CLASS = PlainServicePortRule
