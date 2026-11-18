import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import normalize_os, parse_passwd, result, split_marker_sections


class ServerAccountSeparationRule:
    RULE_KEY = "sec_srv_account_separation"
    CRITERIA_TEXT = "관리자 계정과 유지보수 계정이 분리되어 있고 유지보수 계정에 관리자 권한을 부여하지 않을 것"

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

        if os_type in ("linux", "linux5", "aix", "hpux", "solaris") and ("passwd" in command or "/etc/passwd" in stdout_data):
            return cls._run_passwd(os_type, stdout_data)

        if os_type == "windows" and "get-localuser" in command:
            return result(
                True,
                cls.CRITERIA_TEXT,
                ["Windows 계정 목록 확인. 관리자 그룹 권한 여부는 별도 그룹 출력 필요"],
            )

        return build_unsupported_command(params)

    @classmethod
    def _run_passwd(cls, os_type, stdout_data):
        sections = split_marker_sections(stdout_data)
        passwd_text = sections.get("PASSWD") or stdout_data
        passwd_lines = [line.strip() for line in passwd_text.splitlines() if line.strip()]

        if passwd_lines and not any(":" in line for line in passwd_lines):
            admins = cls._extract_uid_zero_accounts(passwd_text)
            detail = [
                f"UID 0 계정: {', '.join(admins) if admins else '미검출'}",
                "유지보수/일반 계정 확인 불가: /etc/passwd 전체 출력 필요",
            ]
            return result(False, cls.CRITERIA_TEXT, detail)

        accounts = parse_passwd(passwd_text)
        admin_accounts = [name for name, item in accounts.items() if item.get("uid") == 0]
        user_accounts = cls._maintenance_accounts(os_type, accounts)
        extra_admins = [name for name in admin_accounts if name != "root"]
        separated = bool(admin_accounts) and bool(user_accounts)

        detail = [
            f"관리자 계정: {', '.join(admin_accounts) if admin_accounts else '미검출'}",
            f"유지보수/일반 계정 후보: {', '.join(user_accounts) if user_accounts else '미검출'}",
        ]
        if not separated:
            detail.append("관리자 계정과 유지보수/일반 계정 분리 확인 불가")
        if extra_admins:
            detail.append(f"root 외 UID 0 계정 확인: {', '.join(extra_admins)}")

        return result(separated and not extra_admins, cls.CRITERIA_TEXT, detail)

    @classmethod
    def _maintenance_accounts(cls, os_type, accounts):
        min_uid = 1000 if os_type in ("linux", "linux5") else 100
        max_uid = 59999
        users = []
        for name, item in accounts.items():
            uid = item.get("uid")
            shell = str(item.get("shell") or "").strip().lower()
            if uid is None or uid == 0:
                continue
            if uid < min_uid or uid > max_uid:
                continue
            if cls._is_disabled_shell(shell):
                continue
            users.append(name)
        return users

    @staticmethod
    def _is_disabled_shell(shell):
        if not shell:
            return False
        disabled_shells = {
            "false",
            "nologin",
            "/sbin/nologin",
            "/usr/sbin/nologin",
            "/bin/false",
            "/usr/bin/false",
        }
        return shell in disabled_shells or shell.endswith("/false") or shell.endswith("/nologin")

    @staticmethod
    def _extract_uid_zero_accounts(raw):
        accounts = []
        skip_tokens = (
            "TASK ",
            "PLAY ",
            "ok:",
            "changed:",
            "msg:",
            "[INFO]",
            "Last ",
            "Could not",
            "successful",
            "unsuccessful",
            "chdir",
            "결과",
        )
        for line in (raw or "").splitlines():
            stripped = line.strip()
            if not stripped or any(token in stripped for token in skip_tokens):
                continue
            # Some UNIX outputs include '결과: root'
            if stripped.startswith("root") or re.match(r"^[A-Za-z_][A-Za-z0-9_.-]*$", stripped):
                account = stripped.split()[-1]
                if account not in accounts:
                    accounts.append(account)
        return accounts


RULE_KEY = ServerAccountSeparationRule.RULE_KEY
RULE_CLASS = ServerAccountSeparationRule
