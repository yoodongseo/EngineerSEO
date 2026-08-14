import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command


class DirectedBroadcastRule:
    RULE_KEY = "sec_directed_broadcast"
    CRITERIA_TEXT = "Directed-broadcast 차단 여부"

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
        evidence = cls._extract_evidence_lines(stdout_data, ("layer 3", "route"), limit=6)
        return cls._build_result(stdout_data, evidence)

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show ip interface" not in command:
            return build_unsupported_command(params)
        evidence = cls._extract_evidence_lines(
            stdout_data,
            ("directed broadcast forwarding", "directed-broadcast", "ip directed-broadcast"),
        )
        return cls._build_result(stdout_data, evidence)

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        evidence = cls._extract_evidence_lines(
            stdout_data,
            ("enable ns mode", "add ns ip"),
            limit=6,
        )
        return cls._build_result(stdout_data, evidence)

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show ip interface" not in command:
            return build_unsupported_command(params)
        evidence = cls._extract_evidence_lines(
            stdout_data,
            ("directed broadcast forwarding", "directed-broadcast", "ip directed-broadcast"),
        )
        return cls._build_result(stdout_data, evidence)

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        evidence = cls._extract_evidence_lines(
            stdout_data,
            ("interface ", " rpf ", "arp-ignore", "arp-announce"),
            limit=12,
        )
        return cls._build_result(stdout_data, evidence)

    @classmethod
    def _build_result(cls, stdout_data, evidence_lines):
        failed_lines = cls._extract_enabled_lines(stdout_data)
        detail_lines = evidence_lines[:]

        if failed_lines:
            detail_lines = [f"비정상 Directed-broadcast 활성화: {line}" for line in failed_lines]
        elif not detail_lines:
            detail_lines = ["Directed-broadcast 활성화 설정 미검출"]
        elif not any(cls._is_disabled_line(line) for line in detail_lines):
            detail_lines.append("Directed-broadcast 활성화 설정 미검출")

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _extract_enabled_lines(cls, raw):
        enabled_lines = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped or cls._is_disabled_line(stripped):
                continue
            if re.search(r"\bdirected[- ]broadcast\b.*\benabled?\b", lowered):
                enabled_lines.append(stripped)
            elif re.search(r"\bip\s+directed-broadcast\b", lowered):
                enabled_lines.append(stripped)
        return enabled_lines

    @staticmethod
    def _extract_evidence_lines(raw, keywords, limit=10):
        lines = []
        lowered_keywords = tuple(keyword.lower() for keyword in keywords)
        for line in (raw or "").splitlines():
            stripped = line.strip()
            lowered = stripped.lower()
            if not stripped:
                continue
            if any(keyword in lowered for keyword in lowered_keywords):
                lines.append(stripped)
            if len(lines) >= limit:
                break
        return lines

    @staticmethod
    def _is_disabled_line(line):
        lowered = line.lower()
        return (
            "directed broadcast forwarding is disabled" in lowered
            or "no ip directed-broadcast" in lowered
            or re.search(r"\bdirected[- ]broadcast\b.*\bdisabled?\b", lowered)
        )

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = DirectedBroadcastRule.RULE_KEY
RULE_CLASS = DirectedBroadcastRule
