import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command


class NetAppSnapMirrorRule:
    RULE_KEY = "rep_netapp"
    DEFAULT_MIRROR_STATES = ("Snapmirrored",)
    DEFAULT_RELATIONSHIP_STATUSES = ("InSync", "Idle")
    DEFAULT_HEALTHY_VALUES = ("true",)

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def allow_empty_output(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        criteria_text = cls._criteria_text(params)
        if criteria_text:
            return criteria_text

        return (
            "Mirror State={mirror}, Relationship Status={status}, Healthy={healthy}"
        ).format(
            mirror=", ".join(cls.DEFAULT_MIRROR_STATES),
            status=", ".join(cls.DEFAULT_RELATIONSHIP_STATUSES),
            healthy=", ".join(cls.DEFAULT_HEALTHY_VALUES),
        )

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        if "snapmirror show" not in command and "cat" not in command:
            return build_unsupported_command(params)

        raw = stdout_data or ""
        relationships = cls._parse_relationships(raw)
        if not raw.strip():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "SnapMirror 명령 결과가 없습니다.",
            }
        if not relationships:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "SnapMirror 복제 관계 정보를 찾을 수 없습니다.",
            }

        criteria = cls._criteria()
        failed = []
        for item in relationships:
            reasons = cls._relationship_fail_reasons(item, criteria)
            item["is_pass"] = 0 if reasons else 1
            item["fail_reason"] = "; ".join(reasons)
            if reasons:
                failed.append(item)

        total = len(relationships)
        normal = total - len(failed)
        devices = cls._device_summary(relationships)
        detail_lines = [
            f"복제 장비 {len(devices)}대 확인",
            cls._summary_line("복제 관계", total, normal),
        ]
        detail_lines.extend(
            f"  - {item['source']} -> {item['destination']}: "
            f"{cls._format_fail_reason(item['fail_reason'])}"
            for item in failed
        )

        return {
            "is_success": 1,
            "is_pass": 0 if failed else 1,
            "check_target": "NetApp SnapMirror 복제 관계",
            "criteria_items": [cls.build_check_rules(params)],
            "judgement_text": (
                f"비정상 SnapMirror 복제 관계 {len(failed)}건이 확인되었습니다."
                if failed
                else (
                    f"점검 대상 NetApp 장비 {len(devices)}대의 "
                    "SnapMirror 복제 관계가 모두 정상 상태입니다."
                )
            ),
            "detail_lines": detail_lines,
            "before_data": ", ".join(item["source"] for item in relationships),
            "after_data": ", ".join(item["destination"] for item in relationships),
            "check_rules": cls.build_check_rules(params),
        }

    @classmethod
    def _criteria(cls):
        return {
            "allowed_mirror_states": list(cls.DEFAULT_MIRROR_STATES),
            "allowed_relationship_statuses": list(cls.DEFAULT_RELATIONSHIP_STATUSES),
            "allowed_healthy_values": list(cls.DEFAULT_HEALTHY_VALUES),
        }

    @staticmethod
    def _criteria_text(params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, str):
            return criteria.strip()
        if isinstance(criteria, dict):
            return str(criteria.get("criteria_text") or "").strip()
        return ""

    @classmethod
    def _parse_relationships(cls, raw):
        lines = [line.rstrip() for line in raw.replace("\r", "").splitlines()]
        relationships = []
        current_device = ""
        pending_ip = ""
        device_ip_by_name = {}
        index = 0

        while index < len(lines):
            stripped = lines[index].strip()
            ssh_match = re.search(r"ssh\s+\S+@(?P<ip>\d+(?:\.\d+){3})", stripped)
            if ssh_match:
                pending_ip = ssh_match.group("ip")
                index += 1
                continue

            prompt_match = re.match(
                r"^(?P<device>[A-Za-z0-9_.-]+)::>\s*snapmirror show",
                stripped,
            )
            if prompt_match:
                current_device = prompt_match.group("device")
                if pending_ip:
                    device_ip_by_name[current_device] = pending_ip
                    pending_ip = ""
                index += 1
                continue

            close_match = re.search(r"Connection to (?P<ip>\d+(?:\.\d+){3}) closed", stripped)
            if close_match and current_device and current_device not in device_ip_by_name:
                closed_ip = close_match.group("ip")
                device_ip_by_name[current_device] = closed_ip
                for item in relationships:
                    if item.get("device") == current_device and not item.get("device_ip"):
                        item["device_ip"] = closed_ip
                index += 1
                continue

            if not cls._looks_like_path(stripped):
                index += 1
                continue

            dest_index = cls._next_non_empty(lines, index + 1)
            state_index = cls._next_non_empty(lines, (dest_index or index) + 1)
            status_index = cls._next_non_empty(lines, (state_index or index) + 1)
            if None in (dest_index, state_index, status_index):
                index += 1
                continue

            dest_line = lines[dest_index].strip()
            state_line = lines[state_index].strip()
            status_line = lines[status_index].strip()
            dest_match = re.match(r"^(?P<type>\S+)\s+(?P<destination_path>\S+:\S+)$", dest_line)
            state_parts = state_line.split()
            status_parts = status_line.split()
            if not dest_match or not state_parts or len(status_parts) < 3:
                index += 1
                continue

            source_path = stripped
            destination_path = dest_match.group("destination_path")
            relationships.append(
                {
                    "device": current_device or "unknown",
                    "device_ip": device_ip_by_name.get(current_device, ""),
                    "source": cls._name_from_path(source_path),
                    "destination": cls._name_from_path(destination_path),
                    "source_path": source_path,
                    "destination_path": destination_path,
                    "type": dest_match.group("type"),
                    "mirror_state": state_parts[0],
                    "relationship_status": status_parts[0],
                    "total_progress": status_parts[1],
                    "healthy": status_parts[2],
                    "last_updated": " ".join(status_parts[3:]),
                }
            )
            index = status_index + 1

        return relationships

    @classmethod
    def _relationship_fail_reasons(cls, item, criteria):
        reasons = []
        if not cls._matches(item["mirror_state"], criteria["allowed_mirror_states"]):
            reasons.append(f"Mirror State {item['mirror_state']}")
        if not cls._matches(
            item["relationship_status"], criteria["allowed_relationship_statuses"]
        ):
            reasons.append(f"Relationship Status {item['relationship_status']}")
        if not cls._matches(item["healthy"], criteria["allowed_healthy_values"]):
            reasons.append(f"Healthy {item['healthy']}")
        return reasons

    @staticmethod
    def _device_summary(relationships):
        grouped = {}
        for item in relationships:
            key = item.get("device") or "unknown"
            grouped.setdefault(key, []).append(item)

        lines = []
        for device, items in grouped.items():
            normal = len([item for item in items if item.get("is_pass") == 1])
            ip_values = [item.get("device_ip", "") for item in items if item.get("device_ip")]
            label = f"{device}({ip_values[0]})" if ip_values else device
            lines.append(
                f"{label}: 전체 {len(items)}건 / 정상 {normal}건 / 이상 {len(items) - normal}건"
            )
        return lines

    @staticmethod
    def _summary_line(label, total_count, normal_count):
        failed_count = total_count - normal_count
        if failed_count:
            return f"{label} {total_count}개 중 일부 이상"
        return f"{label} {total_count}개 정상"

    @staticmethod
    def _format_fail_reason(reason):
        return str(reason or "").replace("; ", ", ")

    @staticmethod
    def _looks_like_path(value):
        return bool(re.match(r"^\S+:\S+$", value or "")) and not value.startswith("-")

    @staticmethod
    def _next_non_empty(lines, start):
        for index in range(start, len(lines)):
            if lines[index].strip():
                return index
        return None

    @staticmethod
    def _name_from_path(path):
        return str(path or "").split(":", 1)[-1].strip()

    @staticmethod
    def _matches(value, allowed_values):
        normalized = str(value).strip().lower()
        return normalized in {str(item).strip().lower() for item in allowed_values}


RULE_KEY = NetAppSnapMirrorRule.RULE_KEY
RULE_CLASS = NetAppSnapMirrorRule
