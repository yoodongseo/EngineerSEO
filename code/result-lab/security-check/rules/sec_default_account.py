import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_not_applicable, build_unsupported_command


class DefaultAccountDeletionRule:
    RULE_KEY = "sec_default_account"
    CRITERIA_TEXT = "디폴트 계정 삭제 / 잠금 / 비활성화"
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
        accounts, disabled_accounts = cls._parse_user_blocks(stdout_data)
        return cls._build_result(accounts, disabled_accounts)

    @classmethod
    def _run_arista(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_username_accounts(stdout_data)
        return cls._build_result(accounts, disabled_accounts=[])

    @classmethod
    def _run_router(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_username_accounts(stdout_data)
        return cls._build_result(accounts, disabled_accounts=[])

    @classmethod
    def _run_citrix(cls, params, command, stdout_data):
        if "show ns runningconfig" not in command:
            return build_unsupported_command(params)
        accounts = cls._parse_citrix_accounts(stdout_data)
        return cls._build_result(accounts, disabled_accounts=[])

    @classmethod
    def _run_piolink(cls, params, command, stdout_data):
        if "show running-config" not in command:
            return build_unsupported_command(params)
        accounts, disabled_accounts = cls._parse_user_blocks(stdout_data)
        if not accounts:
            accounts = cls._parse_piolink_accounts(stdout_data)
            disabled_accounts = cls._parse_piolink_disabled_accounts(stdout_data)
        return cls._build_result(accounts, disabled_accounts)

    @classmethod
    def _build_result(cls, accounts, disabled_accounts):
        if not accounts:
            return build_not_applicable("디폴트 계정 설정 라인이 확인되지 않습니다.")

        disabled = {name.lower() for name in disabled_accounts}
        default_accounts = [account for account in accounts if cls._is_default_account(account["name"])]
        failed = [account for account in default_accounts if account["name"].lower() not in disabled]

        detail_lines = []
        for account in accounts:
            name = account["name"]
            status = account.get("status") or "상태 정보 미검출"
            if not cls._is_default_account(name):
                continue
            if name.lower() in disabled:
                detail_lines.append(f"디폴트 계정 비활성화 확인: {name} {status}")
            else:
                detail_lines.append(f"비정상 디폴트 계정 존재: {name} {status}")

        if not default_accounts:
            detail_lines.append("디폴트 계정 미검출")
        elif not failed:
            detail_lines.append("활성 디폴트 계정 미검출")

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
            match = re.match(r"^username\s+(\S+)\b", stripped, re.IGNORECASE)
            if match:
                accounts.append({"name": match.group(1), "status": "계정 설정 존재"})
        return accounts

    @staticmethod
    def _parse_citrix_accounts(raw):
        accounts = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^(?:set|add)\s+system\s+user\s+(\S+)\b", stripped, re.IGNORECASE)
            if match:
                accounts.append({"name": match.group(1), "status": "시스템 사용자"})
        return accounts

    @staticmethod
    def _parse_piolink_accounts(raw):
        accounts = []
        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^user\s+(\S+)$", stripped, re.IGNORECASE)
            if match:
                accounts.append({"name": match.group(1), "status": "계정 설정 존재"})
        return accounts

    @staticmethod
    def _parse_user_blocks(raw):
        accounts = []
        disabled = []
        current = None

        def flush():
            if not current:
                return
            name = current["name"]
            log_state = current.get("log")
            level = current.get("level")
            status_parts = []
            if log_state:
                status_parts.append(f"log {log_state}")
            if level:
                status_parts.append(f"level {level}")
            accounts.append({"name": name, "status": ", ".join(status_parts) or "계정 설정 존재"})
            if log_state == "disable":
                disabled.append(name)

        for line in (raw or "").splitlines():
            stripped = line.strip()
            match = re.match(r"^user\s+(\S+)$", stripped, re.IGNORECASE)
            if match:
                flush()
                current = {"name": match.group(1)}
                continue
            if not current:
                continue
            match = re.match(r"^log\s+(enable|disable)$", stripped, re.IGNORECASE)
            if match:
                current["log"] = match.group(1).lower()
                continue
            match = re.match(r"^level\s+(.+)$", stripped, re.IGNORECASE)
            if match:
                current["level"] = match.group(1).strip()
                continue
            if stripped.lower() == "apply":
                flush()
                current = None

        flush()
        return accounts, disabled

    @staticmethod
    def _parse_piolink_disabled_accounts(raw):
        disabled = []
        explicit_user_root = False
        for line in (raw or "").splitlines():
            lowered = line.strip().lower()
            if lowered == "user root":
                explicit_user_root = True
            if lowered == "root-authentication disable" and not explicit_user_root:
                disabled.append("root")
        return disabled

    @classmethod
    def _is_default_account(cls, name):
        return str(name or "").lower() in cls.DEFAULT_ACCOUNT_NAMES

    @staticmethod
    def _normalize_os(value):
        return str(value or "").strip().lower().replace("_", "").replace("-", "")


RULE_KEY = DefaultAccountDeletionRule.RULE_KEY
RULE_CLASS = DefaultAccountDeletionRule
