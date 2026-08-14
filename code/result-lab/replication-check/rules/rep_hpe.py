from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command


class HPERemoteCopyRule:
    RULE_KEY = "rep_hpe"
    DEFAULT_SYSTEM_STATUSES = ("Started",)
    DEFAULT_SYSTEM_HEALTH_VALUES = ("Normal",)
    DEFAULT_TARGET_STATUSES = ("ready",)
    DEFAULT_LINK_STATUSES = ("Up",)
    DEFAULT_GROUP_STATUSES = ("Started",)
    DEFAULT_ROLES = ("Primary", "Secondary")
    DEFAULT_SYNC_STATUSES = ("Synced",)
    REQUIRE_LAST_SYNC_TIME = True

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
            "Remote Copy System/Target 상태 정상, Link Up, "
            "Group Started, SyncStatus Synced 상태 확인"
        )

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        if "showrcopy" not in command and "cat" not in command:
            return build_unsupported_command(params)

        raw = stdout_data or ""
        if not raw.strip():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "HPE Remote Copy 명령 결과가 없습니다.",
            }

        parsed = cls._parse_remote_copy(raw)
        if not parsed["groups"]:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "HPE Remote Copy Group 정보를 찾을 수 없습니다.",
            }

        criteria = cls._criteria()
        failed = cls._failed_items(parsed, criteria)
        link_count = len(parsed["links"])
        target_count = len(parsed["targets"])
        normal_target_count = cls._normal_count(
            parsed["targets"], "status", criteria["allowed_target_statuses"]
        )
        normal_link_count = cls._normal_count(
            parsed["links"], "status", criteria["allowed_link_statuses"]
        )
        normal_group_count = len(
            [
                group
                for group in parsed["groups"]
                if cls._matches(group["status"], criteria["allowed_group_statuses"])
                and cls._matches(group["role"], criteria["allowed_roles"])
            ]
        )
        volumes = [volume for group in parsed["groups"] for volume in group["volumes"]]
        normal_volume_count = len(
            [
                volume
                for volume in volumes
                if cls._matches(volume["sync_status"], criteria["allowed_sync_statuses"])
                and (not criteria["require_last_sync_time"] or volume["last_sync_time"].strip())
            ]
        )
        system_ok = cls._matches(
            parsed["system_status"], criteria["allowed_system_statuses"]
        ) and cls._matches(
            parsed["system_health"], criteria["allowed_system_health_values"]
        )

        detail_lines = [
            f"Remote Copy 전체 상태 {'정상' if system_ok else '이상'}",
        ]
        detail_lines.extend(
            cls._category_lines("복제 대상", "target", target_count, normal_target_count, failed)
        )
        detail_lines.extend(
            cls._category_lines("복제 링크", "link", link_count, normal_link_count, failed)
        )
        detail_lines.extend(
            cls._category_lines(
                "복제 그룹", "group", len(parsed["groups"]), normal_group_count, failed
            )
        )
        detail_lines.extend(
            cls._category_lines("복제 볼륨", "volume", len(volumes), normal_volume_count, failed)
        )
        system_failed = [item for item in failed if item["category"] == "system"]
        detail_lines.extend(f"  - {item['detail']}" for item in system_failed)

        return {
            "is_success": 1,
            "is_pass": 0 if failed else 1,
            "check_target": "HPE Remote Copy 복제 관계",
            "criteria_items": [cls.build_check_rules(params)],
            "judgement_text": (
                f"비정상 HPE Remote Copy 항목 {len(failed)}건이 확인되었습니다."
                if failed
                else "HPE Remote Copy 복제 관계가 모두 정상 상태입니다."
            ),
            "detail_lines": detail_lines,
            "before_data": ", ".join(cls._source_values(parsed)),
            "after_data": ", ".join(cls._destination_values(parsed)),
            "check_rules": cls.build_check_rules(params),
        }

    @classmethod
    def _criteria(cls):
        return {
            "allowed_system_statuses": list(cls.DEFAULT_SYSTEM_STATUSES),
            "allowed_system_health_values": list(cls.DEFAULT_SYSTEM_HEALTH_VALUES),
            "allowed_target_statuses": list(cls.DEFAULT_TARGET_STATUSES),
            "allowed_link_statuses": list(cls.DEFAULT_LINK_STATUSES),
            "allowed_group_statuses": list(cls.DEFAULT_GROUP_STATUSES),
            "allowed_roles": list(cls.DEFAULT_ROLES),
            "allowed_sync_statuses": list(cls.DEFAULT_SYNC_STATUSES),
            "require_last_sync_time": cls.REQUIRE_LAST_SYNC_TIME,
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
    def _parse_remote_copy(cls, raw):
        parsed = {
            "system_status": "",
            "system_health": "",
            "targets": [],
            "links": [],
            "groups": [],
        }
        section = ""
        current_group = None

        for line in raw.replace("\r", "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            lower = stripped.lower()

            if lower.startswith("remote copy system information"):
                section = "system"
                continue
            if lower.startswith("target information"):
                section = "target"
                continue
            if lower.startswith("link information"):
                section = "link"
                continue
            if lower.startswith("group information"):
                section = "group"
                continue

            if section == "system":
                if lower.startswith("status:"):
                    parts = [part.strip() for part in stripped.split(":", 1)[1].split(",")]
                    parsed["system_status"] = parts[0] if parts else ""
                    parsed["system_health"] = parts[1] if len(parts) > 1 else ""
                continue

            parts = stripped.split()
            if section == "target":
                if lower.startswith("name ") or len(parts) < 5:
                    continue
                parsed["targets"].append(
                    {
                        "name": parts[0],
                        "id": parts[1],
                        "type": parts[2],
                        "status": parts[3],
                        "options": parts[4],
                        "policy": " ".join(parts[5:]) if len(parts) > 5 else "",
                    }
                )
                continue

            if section == "link":
                if lower.startswith("target ") or len(parts) < 5:
                    continue
                parsed["links"].append(
                    {
                        "target": parts[0],
                        "node": parts[1],
                        "address": parts[2],
                        "status": parts[3],
                        "options": parts[4],
                    }
                )
                continue

            if section == "group":
                if lower.startswith("name ") or lower.startswith("localvv"):
                    continue
                if len(parts) >= 6 and not current_group:
                    current_group = {
                        "name": parts[0],
                        "target": parts[1],
                        "status": parts[2],
                        "role": parts[3],
                        "mode": parts[4],
                        "options": " ".join(parts[5:]),
                        "volumes": [],
                    }
                    parsed["groups"].append(current_group)
                    continue
                if current_group and len(parts) >= 6:
                    volume = {
                        "local_vv": parts[0],
                        "local_id": parts[1],
                        "remote_vv": parts[2],
                        "remote_id": parts[3],
                        "sync_status": parts[4],
                        "last_sync_time": " ".join(parts[5:]),
                    }
                    cls._apply_direction(current_group, volume)
                    current_group["volumes"].append(volume)

        return parsed

    @staticmethod
    def _apply_direction(group, volume):
        role = str(group.get("role", "")).strip().lower()
        if role == "primary":
            volume["source_vv"] = volume["local_vv"]
            volume["destination_vv"] = volume["remote_vv"]
        elif role == "secondary":
            volume["source_vv"] = volume["remote_vv"]
            volume["destination_vv"] = volume["local_vv"]
        else:
            volume["source_vv"] = ""
            volume["destination_vv"] = ""

    @classmethod
    def _failed_items(cls, parsed, criteria):
        failed = []
        if not cls._matches(parsed["system_status"], criteria["allowed_system_statuses"]):
            failed.append(
                {
                    "category": "system",
                    "name": "Remote Copy System",
                    "reason": f"System Status={parsed['system_status']}",
                    "detail": f"Remote Copy System: Status {parsed['system_status']}",
                }
            )
        if not cls._matches(parsed["system_health"], criteria["allowed_system_health_values"]):
            failed.append(
                {
                    "category": "system",
                    "name": "Remote Copy System",
                    "reason": f"System Health={parsed['system_health']}",
                    "detail": f"Remote Copy System: Health {parsed['system_health']}",
                }
            )

        for target in parsed["targets"]:
            if not cls._matches(target["status"], criteria["allowed_target_statuses"]):
                failed.append(
                    {
                        "category": "target",
                        "name": target["name"],
                        "reason": f"Target Status={target['status']}",
                        "detail": f"{target['name']}: Target {target['status']}",
                    }
                )

        for link in parsed["links"]:
            if not cls._matches(link["status"], criteria["allowed_link_statuses"]):
                failed.append(
                    {
                        "category": "link",
                        "name": f"{link['target']} {link['address']}",
                        "reason": f"Link Status={link['status']}",
                        "detail": f"{link['target']} {link['address']}: Link {link['status']}",
                    }
                )

        for group in parsed["groups"]:
            if not cls._matches(group["status"], criteria["allowed_group_statuses"]):
                failed.append(
                    {
                        "category": "group",
                        "name": group["name"],
                        "reason": f"Group Status={group['status']}",
                        "detail": f"{group['name']}: Group {group['status']}",
                    }
                )
            if not cls._matches(group["role"], criteria["allowed_roles"]):
                failed.append(
                    {
                        "category": "group",
                        "name": group["name"],
                        "reason": f"Role={group['role']}",
                        "detail": f"{group['name']}: Role {group['role']}",
                    }
                )
            for volume in group["volumes"]:
                if not cls._matches(volume["sync_status"], criteria["allowed_sync_statuses"]):
                    failed.append(
                        {
                            "category": "volume",
                            "name": f"{volume['source_vv']} -> {volume['destination_vv']}",
                            "reason": f"SyncStatus={volume['sync_status']}",
                            "detail": (
                                f"{volume['source_vv']} -> {volume['destination_vv']}: "
                                f"SyncStatus {volume['sync_status']}"
                            ),
                        }
                    )
                if criteria["require_last_sync_time"] and not volume["last_sync_time"].strip():
                    failed.append(
                        {
                            "category": "volume",
                            "name": f"{volume['source_vv']} -> {volume['destination_vv']}",
                            "reason": "LastSyncTime 값 없음",
                            "detail": (
                                f"{volume['source_vv']} -> {volume['destination_vv']}: "
                                "LastSyncTime 값 없음"
                            ),
                        }
                    )
        return failed

    @classmethod
    def _normal_count(cls, items, key, allowed_values):
        return len([item for item in items if cls._matches(item.get(key, ""), allowed_values)])

    @staticmethod
    def _summary_line(label, total_count, normal_count):
        failed_count = total_count - normal_count
        if failed_count:
            return f"{label} {total_count}개 중 일부 이상"
        return f"{label} {total_count}개 정상"

    @classmethod
    def _category_lines(cls, label, category, total_count, normal_count, failed):
        lines = [cls._summary_line(label, total_count, normal_count)]
        lines.extend(
            f"  - {item['detail']}"
            for item in failed
            if item["category"] == category
        )
        return lines

    @staticmethod
    def _source_values(parsed):
        values = []
        for group in parsed["groups"]:
            values.extend(volume["source_vv"] for volume in group["volumes"] if volume["source_vv"])
        return values

    @staticmethod
    def _destination_values(parsed):
        values = []
        for group in parsed["groups"]:
            values.extend(
                volume["destination_vv"]
                for volume in group["volumes"]
                if volume["destination_vv"]
            )
        return values

    @staticmethod
    def _matches(value, allowed_values):
        normalized = str(value).strip().lower()
        return normalized in {str(item).strip().lower() for item in allowed_values}


RULE_KEY = HPERemoteCopyRule.RULE_KEY
RULE_CLASS = HPERemoteCopyRule
