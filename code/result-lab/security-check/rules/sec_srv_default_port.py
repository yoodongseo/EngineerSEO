from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules.security.sec_srv_common import find_ports, normalize_os, result


class ServerDefaultPortRule:
    RULE_KEY = "sec_srv_default_port"
    CRITERIA_TEXT = "DB 기본포트, SSH/RDP/X11 등 원격접속 기본포트 변경 및 관리자 IP 접근제한 설정"
    TARGET_PORTS = (22, 1521, 1522, 1523, 1433, 1434, 3306, 3389, 6000)
    PORT_NAMES = {
        22: "SSH",
        1521: "Oracle",
        1522: "Oracle",
        1523: "Oracle",
        1433: "MS-SQL",
        1434: "MS-SQL",
        3306: "MySQL",
        3389: "RDP",
        6000: "X11",
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
            detail = [cls._format_default_port(item) for item in failed]
            if not detail:
                detail = ["DB/원격접속 기본포트 미검출"]
            return result(not failed, cls.CRITERIA_TEXT, detail)
        return build_unsupported_command(params)

    @classmethod
    def _format_default_port(cls, item):
        port = item.get("port")
        proto = str(item.get("proto") or "").upper()
        service_name = cls.PORT_NAMES.get(port, "기본 서비스")
        if proto:
            return f"{service_name} {port}번 기본 포트 활성 ({proto})"
        return f"{service_name} {port}번 기본 포트 활성"


RULE_KEY = ServerDefaultPortRule.RULE_KEY
RULE_CLASS = ServerDefaultPortRule
