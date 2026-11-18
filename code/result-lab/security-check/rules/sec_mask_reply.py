import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class MaskReplyRule:
    RULE_KEY = "sec_mask_reply"
    CRITERIA_TEXT = "Mask-reply 차단 여부 확인"

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
        return build_not_applicable("Mask-reply 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_show_ip_interface(cls, params, command, stdout_data):
        if "show ip interface" not in command:
            return build_unsupported_command(params)
        return cls._build_result(stdout_data)

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        return cls._build_result(stdout_data)

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(stdout_data)

    @classmethod
    def _build_result(cls, stdout_data):
        enabled_lines = cls._extract_enabled_lines(stdout_data)
        evidence_lines = cls._extract_evidence_lines(stdout_data)

        if enabled_lines:
            detail_lines = [f"비정상 Mask-reply 활성화: {line}" for line in enabled_lines]
        elif evidence_lines:
            detail_lines = evidence_lines
        else:
            detail_lines = ["Mask-reply 활성화 설정 미검출"]

        return {
            "is_success": 1,
            "is_pass": 0 if enabled_lines else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if enabled_lines else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _extract_enabled_lines(cls, raw):
        enabled_lines = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or cls._is_disabled_line(lowered):
                continue
            if re.search(r"\bip\s+mask-reply\b", lowered):
                enabled_lines.append(stripped)
            elif re.search(r"\bmask[- ]reply\b.*\b(enable|enabled)\b", lowered):
                enabled_lines.append(stripped)
            elif "mask replies are sent" in lowered:
                enabled_lines.append(stripped)
        return enabled_lines

    @classmethod
    def _extract_evidence_lines(cls, raw):
        lines = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped:
                continue
            if "mask replies" in lowered or "mask-reply" in lowered or "mask reply" in lowered:
                lines.append(stripped)
        return lines[:10]

    @staticmethod
    def _is_disabled_line(line):
        return (
            "no ip mask-reply" in line
            or "mask replies are never sent" in line
            or re.search(r"\bmask[- ]reply\b.*\b(disable|disabled)\b", line)
        )

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = MaskReplyRule.RULE_KEY
RULE_CLASS = MaskReplyRule
