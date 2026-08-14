import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import normalize_os, result, safe_int, split_marker_sections


class ServerPasswordPolicyRule:
    RULE_KEY = "sec_srv_password_policy"
    CRITERIA_TEXT = "비밀번호 최대사용 기간 90일 이하, 9자리 이상 및 복잡도 정책이 설정되어 있을 것"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def allow_empty_output(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        return cls.CRITERIA_TEXT

    @classmethod
    def run(cls, params, stdout_data):
        os_type = normalize_os(params.get("os"))
        command = str(params.get("command") or "").lower()
        if os_type in ("linux", "linux5") and ("login.defs" in command or "LOGIN_DEFS" in stdout_data):
            return cls._run_linux(stdout_data)
        if os_type == "windows" and "net accounts" in command:
            return cls._run_windows(stdout_data)
        if os_type == "aix" and ("lssec" in command or "maxage" in stdout_data or "minlen" in stdout_data):
            return cls._run_aix(stdout_data)
        if os_type == "hpux" and ("default/security" in command or "PASSWORD_" in stdout_data):
            return cls._run_hpux(stdout_data)
        if os_type == "solaris" and ("default/passwd" in command or "MAXWEEKS" in stdout_data or "PASSLENGTH" in stdout_data):
            return cls._run_solaris(stdout_data)
        return build_unsupported_command(params)

    @classmethod
    def _run_linux(cls, raw):
        sections = split_marker_sections(raw)
        login_defs = sections.get("LOGIN_DEFS") or raw
        pam_policy = sections.get("PAM_POLICY") or raw
        max_days = cls._extract_value(login_defs, "PASS_MAX_DAYS")
        min_len = cls._extract_value(login_defs, "PASS_MIN_LEN")
        pam_min_len = cls._extract_pam_minlen(pam_policy)
        effective_min_len = max([value for value in (min_len, pam_min_len) if value is not None] or [0])
        has_complexity = any(token in pam_policy for token in ("pam_pwquality", "pam_cracklib", "ucredit", "lcredit", "dcredit", "ocredit"))
        return cls._build_policy_result(max_days, effective_min_len, has_complexity, "Linux")

    @classmethod
    def _run_aix(cls, raw):
        maxage_weeks = cls._extract_key_value(raw, "maxage")
        min_len = cls._extract_key_value(raw, "minlen")
        max_days = maxage_weeks * 7 if maxage_weeks is not None else None
        return cls._build_policy_result(max_days, min_len, None, "AIX")

    @classmethod
    def _run_hpux(cls, raw):
        max_days = cls._extract_key_value(raw, "PASSWORD_MAXDAYS")
        min_len = cls._extract_key_value(raw, "MIN_PASSWORD_LENGTH")
        has_complexity = all(
            cls._extract_key_value(raw, key, default=0) >= 1
            for key in (
                "PASSWORD_MIN_UPPER_CASE_CHARS",
                "PASSWORD_MIN_LOWER_CASE_CHARS",
                "PASSWORD_MIN_DIGIT_CHARS",
                "PASSWORD_MIN_SPECIAL_CHARS",
            )
        )
        return cls._build_policy_result(max_days, min_len, has_complexity, "HP-UX")

    @classmethod
    def _run_solaris(cls, raw):
        max_weeks = cls._extract_key_value(raw, "MAXWEEKS")
        min_len = cls._extract_key_value(raw, "PASSLENGTH")
        max_days = max_weeks * 7 if max_weeks is not None else None
        return cls._build_policy_result(max_days, min_len, None, "Solaris")

    @classmethod
    def _run_windows(cls, raw):
        max_age = cls._extract_windows_days(raw, "Maximum password age")
        min_len = cls._extract_windows_days(raw, "Minimum password length")
        passed = cls._is_policy_pass(max_age, min_len, None)
        detail = cls._build_detail_lines("Windows", max_age, min_len, None)
        return result(passed, cls.CRITERIA_TEXT, detail)

    @classmethod
    def _build_policy_result(cls, max_days, min_len, has_complexity, label):
        passed = cls._is_policy_pass(max_days, min_len, has_complexity)
        detail = cls._build_detail_lines(label, max_days, min_len, has_complexity)
        return result(passed, cls.CRITERIA_TEXT, detail)

    @staticmethod
    def _is_policy_pass(max_days, min_len, has_complexity):
        if max_days is None or max_days > 90:
            return False
        if min_len is None or min_len < 9:
            return False
        if has_complexity is False:
            return False
        return True

    @staticmethod
    def _build_detail_lines(label, max_days, min_len, has_complexity):
        max_days_text = f"{max_days}일" if max_days is not None else "미검출"
        min_len_text = f"{min_len}자리" if min_len is not None else "미검출"
        detail = [
            f"{label} 최대사용 기간: {max_days_text}",
            f"{label} 최소 길이: {min_len_text}",
        ]
        if has_complexity is True:
            detail.append(f"{label} 복잡도 정책: 확인")
        elif has_complexity is False:
            detail.append(f"{label} 복잡도 정책: 미검출")
        else:
            detail.append(f"{label} 복잡도 정책: 별도 확인 필요")
        return detail

    @staticmethod
    def _extract_value(raw, key):
        match = re.search(rf"^\s*{re.escape(key)}\s+(\d+)\b", raw or "", re.MULTILINE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_key_value(raw, key, default=None):
        found = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Handle cases like MAXWEEKS= or MAXWEEKS=10
            match = re.search(rf"\b{re.escape(key)}\s*=\s*(\d*)", stripped, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                if val:
                    found.append(val)
        if not found:
            return default
        # Return the last valid set value
        return safe_int(found[-1])

    @staticmethod
    def _extract_pam_minlen(raw):
        values = [int(match.group(1)) for match in re.finditer(r"\bminlen\s*=\s*(\d+)", raw or "")]
        return max(values) if values else None

    @staticmethod
    def _extract_windows_days(raw, label):
        match = re.search(rf"{re.escape(label)}[^:]*:\s*(\d+)", raw or "", re.IGNORECASE)
        return int(match.group(1)) if match else None


RULE_KEY = ServerPasswordPolicyRule.RULE_KEY
RULE_CLASS = ServerPasswordPolicyRule
