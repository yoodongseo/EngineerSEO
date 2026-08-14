import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class RansomwarePortRule:
    RULE_KEY = "sec_ransomware_port"
    CRITERIA_TEXT = "랜섬웨어 관련 포트 137, 138, 139, 445 등 제거"
    TARGET_PORTS = ("137", "138", "139", "445")

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
        return build_not_applicable("랜섬웨어 관련 포트 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_failed_lines(stdout_data))

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_failed_lines(stdout_data))

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_failed_lines(stdout_data))

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._extract_failed_lines(stdout_data))

    @classmethod
    def _build_result(cls, failed_lines):
        detail_lines = [f"비정상 랜섬웨어 관련 포트 설정: {line}" for line in failed_lines]
        if not detail_lines:
            detail_lines = ["랜섬웨어 관련 포트 설정 미검출"]

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _extract_failed_lines(cls, raw):
        failed = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or lowered.startswith(("no ", "#", "!")):
                continue
            if cls._contains_target_port(lowered):
                failed.append(stripped)
        return failed

    @classmethod
    def _contains_target_port(cls, line):
        for port in cls.TARGET_PORTS:
            if re.search(rf"\b(port|tcp|udp|eq|range)\s+{port}\b", line):
                return True
            if re.search(rf"\b{port}\b", line) and any(token in line for token in ("smb", "netbios", "cifs")):
                return True
        return False

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = RansomwarePortRule.RULE_KEY
RULE_CLASS = RansomwarePortRule
