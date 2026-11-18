import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class PingLossStatusRule:
    RULE_KEY = "ping_loss_status"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, dict):
            return (
                f"패킷 손실률 {float(criteria.get('max_loss', 0)):.0f}% 이하 / "
                f"평균 응답시간 {float(criteria.get('max_avg_rtt', 0)):.1f}ms 이하"
            )
        if isinstance(criteria, str) and criteria.strip():
            return f"ping 결과에 '{criteria.strip()}' 포함"
        return "Default Router Ping 정상"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "ping" in command:
            if os_type in ["Linux", "Linux5", "Aix", "Hpux", "Windows"]:
                return cls._run_loss_rtt_ping(params, stdout_data)
            if os_type == "Solaris":
                return cls._run_solaris_ping(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _run_loss_rtt_ping(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}

        if isinstance(criteria, dict):
            max_loss = cls._to_int(criteria.get("max_loss"), 0)
            max_avg_rtt = cls._to_float(criteria.get("max_avg_rtt"), None)
        else:
            max_loss = cls._to_int(criteria, 0)
            max_avg_rtt = None

        raw = (stdout_data or "").strip()
        lowered = raw.lower()

        if cls._has_exact_marker(raw, "NO_DEFAULT_GATEWAY"):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "기본 게이트웨이를 확인할 수 없어 PingLoss 점검을 수행할 수 없습니다.",
            }

        if "operation not permitted" in lowered or "permission denied" in lowered:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "ping 실행 권한이 제한되어 PingLoss 점검을 수행할 수 없습니다.",
            }

        loss_pct = cls._extract_loss_pct(raw)
        if loss_pct is None:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "ping 결과에서 패킷 손실률 정보를 찾을 수 없습니다.",
            }

        avg_rtt = cls._extract_avg_rtt(raw)

        criteria_items = [f"패킷 손실률 {max_loss}% 이하"]
        if max_avg_rtt is not None:
            criteria_items.append(f"평균 응답 시간 {max_avg_rtt:.1f}ms 이하")

        detail_lines = [f"패킷 손실률 {loss_pct}%"]
        if avg_rtt is not None:
            detail_lines.append(f"평균 응답 시간 {avg_rtt:.1f}ms")

        failed_lines = []
        if loss_pct > max_loss:
            failed_lines.append(f"비정상 Ping 패킷 손실률 {loss_pct}%")
        if max_avg_rtt is not None and avg_rtt is not None and avg_rtt > max_avg_rtt:
            failed_lines.append(f"비정상 Ping 평균 응답 시간 {avg_rtt:.1f}ms")

        return cls._build_result(detail_lines, criteria_items, failed_lines)

    @classmethod
    def _run_solaris_ping(cls, params, stdout_data):
        criteria = str(params.get("inspection_criteria") or "").strip().lower()
        if not criteria:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Solaris Ping 점검 기준값이 선언되지 않았습니다.",
            }

        raw = (stdout_data or "").strip()
        lowered = raw.lower()

        criteria_items = [f"ping 결과에 '{criteria}' 문자열이 포함될 것"]
        detail_lines = [raw.splitlines()[0].strip()] if raw else []
        failed_lines = []

        if "no answer" in lowered:
            failed_lines.append("비정상 Ping 응답 없음")
        elif criteria not in lowered:
            failed_lines.append(f"비정상 Ping 결과 '{criteria}' 문자열 없음")

        return cls._build_result(detail_lines, criteria_items, failed_lines)

    @classmethod
    def _build_result(cls, detail_lines, criteria_items, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "PingLoss 상태",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @staticmethod
    def _extract_loss_pct(raw):
        match = re.search(r"(\d+)% packet loss", raw, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r"lost\s*=\s*\d+\s*\((\d+)%\s*loss\)", raw, re.IGNORECASE)
        if match:
            return int(match.group(1))

        return None

    @staticmethod
    def _has_exact_marker(raw, marker):
        target = str(marker or "").strip().lower()
        for line in (raw or "").splitlines():
            if line.strip().lower() == target:
                return True
        return False

    @staticmethod
    def _extract_avg_rtt(raw):
        match = re.search(r"min/avg/max(?:/[a-z]+)?\s*=\s*[\d.]+/([\d.]+)/[\d.]+", raw, re.IGNORECASE)
        if match:
            return float(match.group(1))

        match = re.search(r"average\s*=\s*(\d+)(?:ms)?", raw, re.IGNORECASE)
        if match:
            return float(match.group(1))

        return None

    @staticmethod
    def _to_int(value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    @staticmethod
    def _to_float(value, default=None):
        try:
            return float(str(value).strip())
        except Exception:
            return default

RULE_KEY = PingLossStatusRule.RULE_KEY
RULE_CLASS = PingLossStatusRule
