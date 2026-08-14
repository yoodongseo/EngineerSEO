from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class FilesystemUsageRule:
    RULE_KEY = "filesystem_usage"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        try:
            return f"파일시스템 사용률 {float(criteria):.1f}% 초과 시 점검 필요"
        except Exception:
            return "파일시스템 사용률 기준 초과 시 점검 필요"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "df -h" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_df_linux(params, stdout_data)
            if os_type == "Solaris":
                return cls._run_df_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "df -g" in command:
            if os_type == "Aix":
                return cls._run_df_aix(params, stdout_data)
            return build_unsupported_command(params)

        if command == "bdf" or command.startswith("bdf "):
            if os_type == "Hpux":
                return cls._run_bdf_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic logicaldisk" in command:
            if os_type == "Windows":
                return cls._run_wmic_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_usage_result(cls, criteria_value, filesystem_rows):
        failed_rows = [row for row in filesystem_rows if row["used_pct"] > criteria_value]
        if failed_rows:
            detail_lines = [
                f"{row['name']} 사용률 {row['used_pct']:.1f}% (Free {row['free_pct']:.1f}%)"
                for row in failed_rows
            ]
        else:
            detail_lines = [
                f"점검 대상 파일시스템 {len(filesystem_rows)}개 모두 기준 이내"
            ]

        return {
            "is_success": 1,
            "is_pass": 0 if failed_rows else 1,
            "check_target": "파일시스템 사용량",
            "criteria_items": [f"파일시스템 사용률 {criteria_value:.1f}% 초과 시 점검 필요"],
            "judgement_text": "기준 초과" if failed_rows else "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_df_linux(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"파일시스템 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines or "filesystem" not in lines[0].lower():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -h 결과에서 Filesystem 헤더를 찾을 수 없습니다.",
            }

        filesystem_rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6 or "%" not in parts[4]:
                continue

            used_pct = cls._to_float(parts[4].replace("%", ""))
            if used_pct is None:
                continue

            filesystem_rows.append(
                {
                    "name": parts[5],
                    "used_pct": used_pct,
                    "free_pct": round(100.0 - used_pct, 1),
                }
            )

        if not filesystem_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -h 결과에서 파일시스템 사용률 데이터를 찾을 수 없습니다.",
            }

        return cls._build_usage_result(criteria_value, filesystem_rows)

    @classmethod
    def _run_df_solaris(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"파일시스템 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -h 결과가 비어 있습니다.",
            }

        header = lines[0].lower()
        if "filesystem" not in header or "capacity" not in header:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -h 결과에서 Filesystem/Capacity 헤더를 찾을 수 없습니다.",
            }

        filesystem_rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue

            capacity_text = next((part for part in parts if part.endswith("%")), "")
            used_pct = cls._to_float(capacity_text.replace("%", ""))
            if used_pct is None:
                continue

            mount_name = parts[-1]
            filesystem_name = parts[0]
            if mount_name.startswith("/cdrom") or filesystem_name.startswith("/vol/"):
                continue

            filesystem_rows.append(
                {
                    "name": mount_name,
                    "used_pct": used_pct,
                    "free_pct": round(100.0 - used_pct, 1),
                }
            )

        if not filesystem_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -h 결과에서 Solaris 파일시스템 사용률 데이터를 찾을 수 없습니다.",
            }

        return cls._build_usage_result(criteria_value, filesystem_rows)

    @classmethod
    def _run_df_aix(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"파일시스템 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines or "filesystem" not in lines[0].lower():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -g 결과에서 Filesystem 헤더를 찾을 수 없습니다.",
            }

        filesystem_rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 7 or "%" not in parts[3]:
                continue

            used_pct = cls._to_float(parts[3].replace("%", ""))
            if used_pct is None:
                continue

            filesystem_rows.append(
                {
                    "name": parts[6],
                    "used_pct": used_pct,
                    "free_pct": round(100.0 - used_pct, 1),
                }
            )

        if not filesystem_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "df -g 결과에서 AIX 파일시스템 사용률 데이터를 찾을 수 없습니다.",
            }

        return cls._build_usage_result(criteria_value, filesystem_rows)

    @classmethod
    def _run_bdf_hpux(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"파일시스템 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines or "filesystem" not in lines[0].lower():
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "bdf 결과에서 Filesystem 헤더를 찾을 수 없습니다.",
            }

        filesystem_rows = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 6 or "%" not in parts[4]:
                continue

            used_pct = cls._to_float(parts[4].replace("%", ""))
            if used_pct is None:
                continue

            filesystem_rows.append(
                {
                    "name": parts[-1],
                    "used_pct": used_pct,
                    "free_pct": round(100.0 - used_pct, 1),
                }
            )

        if not filesystem_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "bdf 결과에서 HP-UX 파일시스템 사용률 데이터를 찾을 수 없습니다.",
            }

        return cls._build_usage_result(criteria_value, filesystem_rows)

    @classmethod
    def _run_wmic_windows(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"파일시스템 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        items = cls._parse_wmic_blocks(stdout_data)
        if not items:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "wmic LogicalDisk 결과에서 파일시스템 정보를 찾을 수 없습니다.",
            }

        filesystem_rows = []
        for item in items:
            name = (item.get("DeviceID") or "").strip() or "(unknown)"
            size = cls._to_float(item.get("Size"))
            free = cls._to_float(item.get("FreeSpace"))

            if size is None or free is None or size <= 0:
                continue

            used_pct = round(((size - free) / size) * 100.0, 1)
            filesystem_rows.append(
                {
                    "name": name,
                    "used_pct": used_pct,
                    "free_pct": round(100.0 - used_pct, 1),
                }
            )

        if not filesystem_rows:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "wmic LogicalDisk 결과에서 Windows 파일시스템 사용률 데이터를 찾을 수 없습니다.",
            }

        return cls._build_usage_result(criteria_value, filesystem_rows)

    @staticmethod
    def _parse_wmic_blocks(stdout_data):
        items = []
        current_item = {}

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            if key.strip() in current_item and current_item:
                items.append(current_item)
                current_item = {}
            current_item[key.strip()] = value.strip()

        if current_item:
            items.append(current_item)

        return items

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).strip())
        except Exception:
            return None

RULE_KEY = FilesystemUsageRule.RULE_KEY
RULE_CLASS = FilesystemUsageRule
