import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import (
    account_locked,
    normalize_os,
    parse_passwd,
    parse_shadow,
    result,
    split_marker_sections,
)


class ServerDefaultAccountRule:
    RULE_KEY = "sec_srv_default_account"
    CRITERIA_TEXT = "OS/DB/WAS/기타 디폴트 계정이 삭제, 잠금 또는 비활성화 상태일 것"
    UNIX_DEFAULT_ACCOUNTS = ("lp", "sync", "shutdown", "halt", "news", "uucp", "nfs", "nobody", "guest", "ftp")
    DEFAULT_ACCOUNTS = UNIX_DEFAULT_ACCOUNTS + (
        "admin",
        "scott",
        "system",
        "sys",
        "dbsnmp",
        "tracesvr",
        "sa",
        "mysql",
        "tomcat",
        "role1",
    )

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
        os_type = normalize_os(params.get("os"))
        command = str(params.get("command") or "").lower()
        if os_type in ("linux", "linux5") and ("passwd" in command or "/etc/passwd" in stdout_data):
            return cls._run_linux(stdout_data)
        if os_type == "windows" and ("get-localuser" in command or "localuser" in stdout_data.lower()):
            return cls._run_windows(stdout_data)
        if os_type in ("aix", "hpux", "solaris") and ("passwd" in command or "계정" in stdout_data or "怨" in stdout_data):
            return cls._run_unix_status(stdout_data)
        return build_unsupported_command(params)

    @classmethod
    def _run_linux(cls, raw):
        sections = split_marker_sections(raw)
        passwd_raw = sections.get("PASSWD") or raw
        shadow_raw = sections.get("SHADOW") or ""
        accounts = parse_passwd(passwd_raw)
        shadow = parse_shadow(shadow_raw)

        failed = []
        detail = []
        for name in cls.DEFAULT_ACCOUNTS:
            account = accounts.get(name)
            if not account:
                continue
            if account_locked(account, shadow):
                detail.append(f"디폴트 계정 비활성화 확인: {name} shell={account['shell']}")
            else:
                failed.append(f"{name} shell={account['shell']}")

        if failed:
            detail = [f"비정상 디폴트 계정 존재: {line}" for line in failed]
        else:
            detail = ["활성 디폴트 계정 미검출"]
        return result(not failed, cls.CRITERIA_TEXT, detail)

    @classmethod
    def _run_unix_status(cls, raw):
        failed = []
        detail = []
        text = raw or ""
        for name in cls.UNIX_DEFAULT_ACCOUNTS:
            if not re.search(rf"\b{name}\b", text):
                continue
            if cls._line_says_missing_or_denied(text, name):
                detail.append(f"디폴트 계정 비활성화/미존재 확인: {name}")
            else:
                failed.append(name)
        if failed:
            detail = [f"비정상 디폴트 계정 존재 또는 상태 미확인: {name}" for name in failed]
        elif not detail:
            detail = ["디폴트 계정 상태 라인 미검출"]
        else:
            detail = ["활성 디폴트 계정 미검출"]
        return result(not failed, cls.CRITERIA_TEXT, detail)

    @staticmethod
    def _line_says_missing_or_denied(text, name):
        for line in (text or "").splitlines():
            if not re.search(rf"\b{name}\b", line):
                continue
            parts = line.split()
            if parts and parts[0] == name and len(parts) >= 2:
                status = parts[1].upper()
                if status in ("LK", "NL"):
                    return True
            lowered = line.lower()
            if any(token in lowered for token in ("user unknown", "not exist", "no such", "locked", "disabled")):
                return True
            if "미존" in line or "잠금" in line or "비활성" in line or "권한" in line or "거부" in line or "誘몄" in line or "嫄" in line:
                return True
        return False

    @classmethod
    def _run_windows(cls, raw):
        default_names = {"administrator", "guest", "defaultaccount", "admin", "root", "ftp"}
        failed = []
        detail = []
        current = None
        for line in (raw or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) >= 2 and parts[1].lower() in ("true", "false"):
                current = {"name": parts[0], "enabled": parts[1].lower() == "true"}
            elif stripped.lower().startswith("name") or stripped.startswith("----"):
                current = None
            if current and current["name"].lower() in default_names:
                if current["enabled"]:
                    failed.append(current["name"])
                else:
                    detail.append(f"디폴트 계정 비활성화 확인: {current['name']}")
                current = None
        if failed:
            detail = [f"비정상 디폴트 계정 활성: {name}" for name in failed]
        else:
            detail = ["활성 디폴트 계정 미검출"]
        return result(not failed, cls.CRITERIA_TEXT, detail)


RULE_KEY = ServerDefaultAccountRule.RULE_KEY
RULE_CLASS = ServerDefaultAccountRule
