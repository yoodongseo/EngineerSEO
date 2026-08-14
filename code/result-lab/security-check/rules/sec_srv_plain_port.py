from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import find_ports, normalize_os, result


class ServerPlainPortRule:
    RULE_KEY = "sec_srv_plain_port"
    CRITERIA_TEXT = "FTP(20,21), Telnet(23), Rlogin(513), Rshell/Rcp(514), Rexec(512) 등 평문 서비스 포트 제거"
    TARGET_PORTS = (20, 21, 23, 512, 513, 514)
    PORT_NAMES = {
        20: "FTP-DATA",
        21: "FTP",
        23: "Telnet",
        512: "Rexec",
        513: "Rlogin",
        514: "Rshell/Rcp",
    }

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
        if os_type in ("linux", "linux5", "windows", "aix", "hpux", "solaris") and any(
            token in command for token in ("ss ", "netstat", "get-nettcpconnection")
        ):
            failed = find_ports(stdout_data, cls.TARGET_PORTS)
            detail = [cls._format_plain_port(item) for item in failed]
            if not detail:
                detail = ["평문 서비스 포트 미검출"]
            return result(not failed, cls.CRITERIA_TEXT, detail)
        return build_unsupported_command(params)

    @classmethod
    def _format_plain_port(cls, item):
        port = item.get("port")
        proto = str(item.get("proto") or "").upper()
        service_name = cls.PORT_NAMES.get(port, "평문 서비스")
        if proto:
            return f"{service_name} {port}번 평문 서비스 포트 활성 ({proto})"
        return f"{service_name} {port}번 평문 서비스 포트 활성"


RULE_KEY = ServerPlainPortRule.RULE_KEY
RULE_CLASS = ServerPlainPortRule
