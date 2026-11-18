import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class PasswordSettingRule:
    RULE_KEY = "sec_password_setting"
    CRITERIA_TEXT = "디폴트 계정 삭제 불가 시 비밀번호 변경 사용"
    DEFAULT_ACCOUNT_NAMES = ("admin", "root", "ftp", "1", "nsroot", "manager")

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
        return build_not_applicable("계정 비밀번호 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._parse_username_accounts(stdout_data), disabled_accounts=[])

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._parse_username_accounts(stdout_data), disabled_accounts=[])

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        return cls._build_result(cls._parse_citrix_accounts(stdout_data), disabled_accounts=[])

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_piolink_accounts(stdout_data)
        disabled_accounts = cls._parse_piolink_disabled_accounts(stdout_data)
        return cls._build_result(accounts, disabled_accounts)

    @classmethod
    def _build_result(cls, accounts, disabled_accounts):
        if not accounts:
            return build_not_applicable("계정 비밀번호 설정 라인이 확인되지 않습니다.")

        disabled = {name.lower() for name in disabled_accounts}
        default_accounts = [account for account in accounts if cls._is_default_account(account["name"])]
        failed = [
            account
            for account in default_accounts
            if account["name"].lower() not in disabled and not account["password_configured"]
        ]

        detail_lines = []
        for account in accounts:
            name = account["name"]
            status = account.get("status") or "비밀번호 정보 미검출"
            if not cls._is_default_account(name):
                detail_lines.append(f"{name} {status}")
            elif name.lower() in disabled:
                detail_lines.append(f"디폴트 계정 비활성화 확인: {name} {status}")
            elif account["password_configured"]:
                detail_lines.append(f"디폴트 계정 비밀번호 설정 확인: {name} {status}")
            else:
                detail_lines.append(f"비정상 디폴트 계정 비밀번호 설정 미확인: {name}")

        if not default_accounts:
            detail_lines.append("디폴트 계정 미검출")
        elif not failed:
            detail_lines.append("디폴트 계정 비밀번호 설정 기준 이내")

        return {
            "is_success": 1,
            "is_pass": 0 if failed else 1,
            "check_target": cls.CRITERIA_TEXT,
            "criteria_items": [cls.CRITERIA_TEXT],
            "judgement_text": "기준 초과" if failed else "기준 이내",
            "detail_lines": detail_lines,
        }

    @staticmethod
    def _parse_username_accounts(raw):
        accounts = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^username\s+(\S+)\s+(.+)$", stripped, re.IGNORECASE)
            if not match:
                continue
            body = match.group(2)
            configured = bool(re.search(r"\b(secret|password)\b", body, re.IGNORECASE))
            accounts.append(
                {
                    "name": match.group(1),
                    "status": "secret/password 설정" if configured else "비밀번호 정보 미검출",
                    "password_configured": configured,
                }
            )
        return accounts

    @staticmethod
    def _parse_citrix_accounts(raw):
        accounts = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^(?:set|add)\s+system\s+user\s+(\S+)\s+(.+)$", stripped, re.IGNORECASE)
            if not match:
                continue
            configured = "-encrypted" in match.group(2).lower()
            accounts.append(
                {
                    "name": match.group(1),
                    "status": "encrypted password 설정" if configured else "비밀번호 정보 미검출",
                    "password_configured": configured,
                }
            )
        return accounts

    @staticmethod
    def _parse_piolink_accounts(raw):
        accounts = []
        current = None
        for line in (raw or "").splitlines():
            stripped = line.strip()
            user_match = re.match(r"^user\s+(\S+)$", stripped, re.IGNORECASE)
            if user_match:
                current = {"name": user_match.group(1), "status": "", "password_configured": False}
                accounts.append(current)
                continue
            if current is None:
                continue
            lowered = stripped.lower()
            if lowered.startswith(("sha-passwd", "aes-passwd", "password", "passwd")):
                current["password_configured"] = True
                current["status"] = "password hash 설정"
            elif stripped == "apply":
                if not current["status"]:
                    current["status"] = "비밀번호 정보 미검출"
                current = None
        return accounts

    @staticmethod
    def _parse_piolink_disabled_accounts(raw):
        disabled = []
        for line in (raw or "").splitlines():
            if line.strip().lower() == "root-authentication disable":
                disabled.append("root")
        return disabled

    @classmethod
    def _is_default_account(cls, name):
        return str(name or "").lower() in cls.DEFAULT_ACCOUNT_NAMES

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = PasswordSettingRule.RULE_KEY
RULE_CLASS = PasswordSettingRule
