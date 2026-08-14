import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import normalize_os, result, split_marker_sections


class ServerLogRetentionRule:
    RULE_KEY = "sec_srv_log_retention"
    CRITERIA_TEXT = "접근기록, 정책변경 로그 보관기간이 180일 이상일 것"

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
        if os_type in ("linux", "linux5") and ("logrotate" in command or "LOGROTATE" in stdout_data):
            return cls._run_linux(stdout_data)
        if os_type == "windows" and "wevtutil" in command:
            return cls._run_windows(stdout_data)
        if os_type == "aix" and ("syslog.conf" in command or "rotate" in stdout_data):
            return cls._run_aix(stdout_data)
        if os_type == "solaris" and ("logadm" in command or "LOGADM" in stdout_data):
            return cls._run_solaris_logadm(stdout_data)
        if os_type in ("hpux", "solaris") and ("find" in command or "mtime +180" in command):
            return cls._run_find_mtime(stdout_data, os_type.upper())
        return build_unsupported_command(params)

    @classmethod
    def _run_linux(cls, raw):
        sections = split_marker_sections(raw)
        policy = "\n".join(value for key, value in sections.items() if key.startswith("LOGROTATE"))
        days = cls._estimate_retention_days(policy)
        if days is None:
            # If policy estimation fails, fallback to checking if any mtime files were captured
            if "mtime +180" in raw.lower() and cls._has_find_mtime_results(raw):
                return result(True, cls.CRITERIA_TEXT, ["정책 설정 미검출이나 180일 초과 로그 파일 실물 확인"])
            return result(False, cls.CRITERIA_TEXT, ["logrotate 보관기간 산정 정보 미검출"])
        if days >= 180:
            return result(True, cls.CRITERIA_TEXT, [f"로그 보관기간 정책 확인: 약 {days}일 ({cls._get_frequency_desc(policy)})"])
        return result(False, cls.CRITERIA_TEXT, [f"로그 보관기간 정책 기준 미달: 약 {days}일"])

    @classmethod
    def _run_solaris_logadm(cls, raw):
        sections = split_marker_sections(raw)
        logadm_conf = sections.get("LOGADM") or raw
        max_days = 0
        found_policy = False
        
        for line in logadm_conf.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # logadm.conf usually has options like -C count -a period
            count_match = re.search(r"-C\s+(\d+)", line)
            period_match = re.search(r"-a\s+([\d\w]+)", line)
            if count_match and period_match:
                found_policy = True
                count = int(count_match.group(1))
                period = period_match.group(1).lower()
                multiplier = 1
                if "w" in period: multiplier = 7
                elif "m" in period: multiplier = 30
                elif "y" in period: multiplier = 365
                elif "d" in period: 
                    p_days = re.search(r"(\d+)d", period)
                    if p_days: multiplier = int(p_days.group(1))
                
                max_days = max(max_days, count * multiplier)

        if not found_policy:
            if cls._has_find_mtime_results(raw):
                 return result(True, cls.CRITERIA_TEXT, ["Solaris logadm 정책 미검출이나 180일 초과 로그 파일 실물 확인"])
            return result(False, cls.CRITERIA_TEXT, ["Solaris logadm 로그 보관 정책 미검출"])

        if max_days >= 180:
            return result(True, cls.CRITERIA_TEXT, [f"Solaris logadm 정책 확인: 최대 {max_days}일 보관"])
        return result(False, cls.CRITERIA_TEXT, [f"Solaris logadm 정책 기준 미달: {max_days}일"])

    @classmethod
    def _run_find_mtime(cls, raw, label):
        data_lines = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("[", "TASK ", "PLAY ", "ok:", "changed:", "msg:", "-", "'")):
                continue
            if "결과" in stripped or "寃" in stripped or "Could not chdir" in stripped or "Last " in stripped:
                continue
            if re.search(r"\s/var/", stripped):
                data_lines.append(stripped)
        if data_lines:
            return result(True, cls.CRITERIA_TEXT, [f"{label} 180일 초과 로그 파일 실물 확인: {len(data_lines)}개"])
        return result(False, cls.CRITERIA_TEXT, [f"{label} 180일 이상 보관 로그 파일 및 정책 미검출 (신규 서버인 경우 설정 파일 확인 필요)"])

    @staticmethod
    def _has_find_mtime_results(raw):
        # Quick check if find results are present in the raw output
        return "/var/log" in raw and re.search(r"\s+\d+\s+[A-Z][a-z]{2}\s+", raw)

    @staticmethod
    def _get_frequency_desc(policy):
        for freq in ("daily", "weekly", "monthly", "yearly"):
            if freq in policy.lower(): return freq
        return "period"

    @classmethod
    def _run_windows(cls, raw):
        lowered = (raw or "").lower()
        if "retention: true" in lowered:
            return result(True, cls.CRITERIA_TEXT, ["Security 이벤트 로그 보존 설정 확인"])
        return result(False, cls.CRITERIA_TEXT, ["Security 이벤트 로그 180일 이상 보관 설정 미확인"])

    @staticmethod
    def _estimate_retention_days(raw):
        frequency = None
        rotate = None
        for line in (raw or "").splitlines():
            stripped = line.strip().lower()
            if stripped in ("daily", "weekly", "monthly", "yearly"):
                frequency = stripped
            match = re.match(r"rotate\s+(\d+)", stripped)
            if match:
                rotate = int(match.group(1))
        if not frequency or rotate is None:
            return None
        multiplier = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}.get(frequency, 0)
        return rotate * multiplier

    @staticmethod
    def _estimate_aix_syslog_days(raw):
        match = re.search(r"rotate\s+files\s+(\d+)\s+time\s+(\d+)([dwmy])", raw or "", re.IGNORECASE)
        if not match:
            return None
        files = int(match.group(1))
        amount = int(match.group(2))
        unit = match.group(3).lower()
        multiplier = {"d": 1, "w": 7, "m": 30, "y": 365}.get(unit, 0)
        return files * amount * multiplier


RULE_KEY = ServerLogRetentionRule.RULE_KEY
RULE_CLASS = ServerLogRetentionRule
