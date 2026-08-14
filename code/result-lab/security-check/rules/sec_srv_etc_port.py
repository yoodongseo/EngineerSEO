from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import find_ports, normalize_os, result


class ServerEtcPortRule:
    RULE_KEY = "sec_srv_etc_port"
    CRITERIA_TEXT = "랜섬웨어 포트 137, 138, 139, 445 등 제거"
    TARGET_PORTS = (137, 138, 139, 445)

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
        if os_type in ("linux", "linux5", "windows", "aix", "hpux", "solaris") and any(token in command for token in ("ss ", "netstat", "get-nettcpconnection")):
            failed = find_ports(stdout_data, cls.TARGET_PORTS)
            detail = [f"랜섬웨어 관련 포트 활성: {item['proto']}/{item['port']} {item['line']}" for item in failed]
            if not detail:
                detail = ["랜섬웨어 관련 포트 미검출"]
            return result(not failed, cls.CRITERIA_TEXT, detail)
        return build_unsupported_command(params)


RULE_KEY = ServerEtcPortRule.RULE_KEY
RULE_CLASS = ServerEtcPortRule
