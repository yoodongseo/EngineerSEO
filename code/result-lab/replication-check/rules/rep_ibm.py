import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command


class IBMRemoteCopyRule:
    RULE_KEY = "rep_ibm"
    NORMAL_STATES = ("consistent_copying", "consistent_synchronized", "idling")
    STATE_DESCRIPTIONS = {
        "consistent_copying": "일치 복제 중",
        "inconsistent_stopped": "불일치 중지 상태",
        "inconsistent_copying": "불일치 복제 중",
        "consistent_stopped": "일치 중지 상태",
        "consistent_synchronized": "일치 복제 완료",
        "idling": "유휴 상태",
        "idling_disconnected": "유휴 복제 끊김 상태",
        "inconsistent_disconnected": "불일치 복제 끊김 상태",
        "consistent_disconnected": "일치 복제 끊김 상태",
        "empty": "복제 관계가 비어있는 상태",
    }

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def allow_empty_output(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, str) and criteria.strip():
            return criteria.strip()
        return "IBM 복제 상태가 consistent_copying, consistent_synchronized, idling 중 하나일 것"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        if not any(token in command for token in ("lsrcconsistgrp", "attache_dr", "cat")):
            return build_unsupported_command(params)

        raw = stdout_data or ""
        if not raw.strip():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "IBM 복제 상태 명령 결과가 없습니다.",
            }

        states = cls._parse_states(raw)
        if not states:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "IBM 복제 상태값을 찾을 수 없습니다.",
            }

        failed = [state for state in states if state not in cls.NORMAL_STATES]
        ip_value = cls._host_value(params)
        detail_lines = [cls._summary_line(len(failed))]
        detail_lines.extend(
            f"  - {state}: {cls.STATE_DESCRIPTIONS.get(state, '알 수 없는 상태')}"
            for state in states
        )

        return {
            "is_success": 1,
            "is_pass": 0 if failed else 1,
            "check_target": "IBM 복제 상태",
            "criteria_items": [cls.build_check_rules(params)],
            "judgement_text": (
                f"IBM 복제 상태 {len(failed)}건이 비정상입니다."
                if failed
                else "IBM 복제 상태가 정상입니다."
            ),
            "detail_lines": detail_lines,
            "before_data": ip_value,
            "after_data": ip_value,
            "check_rules": cls.build_check_rules(params),
        }

    @classmethod
    def _parse_states(cls, raw):
        known_states = set(cls.STATE_DESCRIPTIONS)
        states = []
        for line in raw.replace("\r", "").splitlines():
            for token in re.findall(r"[A-Za-z_]+", line):
                value = token.strip().lower()
                if value in known_states:
                    states.append(value)
        return states

    @staticmethod
    def _host_value(params):
        for key in ("real_host_name", "host_name", "host", "inventory_hostname"):
            value = str(params.get(key) or "").strip()
            if value:
                return value
        return ""

    @staticmethod
    def _summary_line(failed_count):
        if failed_count:
            return "IBM 복제 상태 점검 필요"
        return "IBM 복제 상태 정상"


RULE_KEY = IBMRemoteCopyRule.RULE_KEY
RULE_CLASS = IBMRemoteCopyRule
