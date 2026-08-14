import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class RemoteAccessControlRule:
    RULE_KEY = "sec_remote_access"
    CRITERIA_TEXT = "SSH(22), 원격데스크탑(3389), X11(6000) 등 기본포트 변경 / 관리자 IP 접속 제한"

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
        return build_not_applicable("원격접속 포트 및 접속제한 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)

        lines = cls._significant_lines(stdout_data)
        failed = []
        details = []

        if any(line == "management ssh" for line in lines):
            details.append("SSH 관리 접속 설정 확인")
            if not cls._has_non_default_ssh_port(lines):
                failed.append("SSH 기본 포트(22) 변경 설정 미확인")
            if not cls._has_access_restriction(lines):
                failed.append("관리자 IP 접속 제한 설정 미확인")

        return cls._build_result(failed, details)

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        failed = []
        details = []
        vty_blocks = cls._extract_vty_blocks(lines)

        if vty_blocks:
            details.append(f"VTY 원격접속 설정 {len(vty_blocks)}개 확인")
            if any(cls._block_has_ssh(block) for block in vty_blocks):
                if not cls._has_non_default_ssh_port(lines):
                    failed.append("SSH 기본 포트(22) 변경 설정 미확인")
            if not all(cls._block_has_access_class(block) for block in vty_blocks):
                failed.append("VTY 관리자 IP 접속 제한 설정 미확인")

        return cls._build_result(failed, details)

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        return cls._build_result([], ["SSH/RDP/X11 원격접속 기본 포트 활성화 설정 미검출"])

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)

        lines = cls._significant_lines(stdout_data)
        failed = []
        details = []
        status_map = cls._extract_service_status(lines)
        port_map = cls._extract_service_ports(lines)

        if status_map.get("ssh") == "enable":
            port = port_map.get("ssh")
            details.append(f"SSH status=enable port={port or '미확인'}")
            if port in ("", None, "22"):
                failed.append("SSH 기본 포트(22) 변경 설정 미확인")
        if status_map.get("telnet") == "enable":
            failed.append("Telnet 원격접속 활성화")
        elif "telnet" in status_map:
            details.append(f"Telnet status={status_map['telnet']}")

        return cls._build_result(failed, details)

    @classmethod
    def _build_result(cls, failed_lines, detail_lines):
        details = list(detail_lines)
        if failed_lines:
            details.extend(f"비정상 {line}" for line in failed_lines)
        if not details:
            details = ["원격접속 기본 포트 및 접속제한 위반 설정 미검출"]

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": details,
        }

    @staticmethod
    def _significant_lines(raw):
        return [line.strip() for line in (raw or "").splitlines() if line.strip()]

    @staticmethod
    def _has_non_default_ssh_port(lines):
        for line in lines:
            lowered = line.lower()
            match = re.search(r"\bssh\s+port\s+(\d+)\b", lowered)
            if match and match.group(1) != "22":
                return True
            match = re.search(r"\bip\s+ssh\s+port\s+(\d+)\b", lowered)
            if match and match.group(1) != "22":
                return True
        return False

    @staticmethod
    def _has_access_restriction(lines):
        keywords = ("access-class", "access-group", "acl", "access-list", "control-plane")
        return any(any(keyword in line.lower() for keyword in keywords) for line in lines)

    @staticmethod
    def _extract_vty_blocks(lines):
        blocks = []
        current = None
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("line vty"):
                if current:
                    blocks.append(current)
                current = [stripped]
                continue
            if current is not None:
                if re.match(r"^\S", line) and not line.startswith((" ", "\t")):
                    blocks.append(current)
                    current = None
                else:
                    current.append(stripped)
        if current:
            blocks.append(current)
        return blocks

    @staticmethod
    def _block_has_ssh(block):
        return any("transport input" in line.lower() and "ssh" in line.lower() for line in block)

    @staticmethod
    def _block_has_access_class(block):
        return any("access-class" in line.lower() for line in block)

    @staticmethod
    def _extract_service_status(lines):
        status_map = {}
        for line in lines:
            match = re.match(r"^(ssh|telnet|http|https)\s+status\s+(\S+)", line.lower())
            if match:
                status_map[match.group(1)] = match.group(2)
        return status_map

    @staticmethod
    def _extract_service_ports(lines):
        port_map = {}
        for line in lines:
            match = re.match(r"^(ssh|telnet|http|https)\s+port\s+(\d+)", line.lower())
            if match:
                port_map[match.group(1)] = match.group(2)
        return port_map

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = RemoteAccessControlRule.RULE_KEY
RULE_CLASS = RemoteAccessControlRule
