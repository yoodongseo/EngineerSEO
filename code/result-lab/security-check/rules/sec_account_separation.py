import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class AccountPrivilegeSeparationRule:
    RULE_KEY = "sec_account_separation"
    CRITERIA_TEXT = "관리자 계정과 유지보수 계정 분리 / 유지보수 계정에 관리자 권한 부여 금지"
    ADMIN_NAME_TOKENS = ("admin", "root", "manager")

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
        return build_not_applicable("계정 권한 설정 라인이 확인되지 않습니다.")

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_username_accounts(stdout_data)
        return cls._build_result(accounts)

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_username_accounts(stdout_data)
        return cls._build_result(accounts)

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_citrix_accounts(stdout_data)
        return cls._build_result(accounts)

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_piolink_accounts(stdout_data)
        return cls._build_result(accounts)

    @classmethod
    def _build_result(cls, accounts):
        if not accounts:
            return build_not_applicable("계정 권한 설정 라인이 확인되지 않습니다.")

        failed = []
        detail_lines = []
        for account in accounts:
            name = account["name"]
            privilege = account.get("privilege") or "권한 정보 미검출"
            if account["admin_privilege"] and not cls._is_admin_account(name):
                failed.append(f"{name} {privilege}")
                detail_lines.append(f"비정상 유지보수 계정 관리자 권한: {name} {privilege}")
            else:
                detail_lines.append(f"{name} {privilege}")

        if not failed:
            detail_lines.append("비관리자 계정 관리자 권한 부여 설정 미검출")

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
            name = match.group(1)
            body = match.group(2)
            privilege_match = re.search(r"\bprivilege\s+(\d+)\b", body, re.IGNORECASE)
            role_match = re.search(r"\brole\s+(\S+)\b", body, re.IGNORECASE)
            privilege_parts = []
            admin_privilege = False
            if privilege_match:
                value = privilege_match.group(1)
                privilege_parts.append(f"privilege {value}")
                admin_privilege = admin_privilege or value == "15"
            if role_match:
                value = role_match.group(1)
                privilege_parts.append(f"role {value}")
                admin_privilege = admin_privilege or value.lower() in ("network-admin", "admin")
            accounts.append(
                {
                    "name": name,
                    "privilege": ", ".join(privilege_parts),
                    "admin_privilege": admin_privilege,
                }
            )
        return accounts

    @staticmethod
    def _parse_citrix_accounts(raw):
        accounts = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^(?:set|add)\s+system\s+user\s+(\S+)\b", stripped, re.IGNORECASE)
            if match:
                accounts.append(
                    {
                        "name": match.group(1),
                        "privilege": "시스템 사용자",
                        "admin_privilege": False,
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
                current = {"name": user_match.group(1), "privilege": "", "admin_privilege": False}
                accounts.append(current)
                continue
            if current is None:
                continue
            level_match = re.match(r"^level\s+(\S+)$", stripped, re.IGNORECASE)
            if level_match:
                level = level_match.group(1)
                current["privilege"] = f"level {level}"
                current["admin_privilege"] = level.lower() in ("superuser", "admin")
            elif stripped == "apply":
                current = None
        return accounts

    @classmethod
    def _is_admin_account(cls, name):
        lowered = str(name or "").lower()
        return any(token in lowered for token in cls.ADMIN_NAME_TOKENS)

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = AccountPrivilegeSeparationRule.RULE_KEY
RULE_CLASS = AccountPrivilegeSeparationRule
