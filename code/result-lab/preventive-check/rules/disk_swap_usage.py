from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class DiskSwapUsageRule:
    RULE_KEY = "disk_swap_usage"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, dict) and "max_used_swap" in criteria:
            return f"개별 Swap 사용률 {float(criteria.get('max_used_swap', 0)):.1f}% 이하"
        if isinstance(criteria, list) and len(criteria) >= 2:
            try:
                return f"개별 Swap 사용률 {float(criteria[1]):.1f}% 이하"
            except Exception:
                pass
        try:
            return f"개별 Swap 사용률 {float(criteria):.1f}% 이하"
        except Exception:
            return "개별 Swap 사용률 기준 이내"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "swapon -s" in command:
            if os_type == "Linux":
                return cls._run_swapon_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "/proc/swaps" in command:
            if os_type == "Linux5":
                return cls._run_swapon_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "swap -l" in command:
            if os_type == "Solaris":
                return cls._run_swap_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "lsps -a" in command:
            if os_type == "Aix":
                return cls._run_lsps_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "swapinfo -tam" in command:
            if os_type == "Hpux":
                return cls._run_swapinfo_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic pagefile get name,allocatedbasesize,currentusage,peakusage /value" in command:
            if os_type == "Windows":
                return cls._run_wmic_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_result(cls, criteria_value, detail_lines, failed_lines):
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "Disk Swap 사용률",
            "criteria_items": [f"Disk Swap 사용률 {criteria_value:.1f}% 초과 시 점검 필요"],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": failed_lines if failed_lines else detail_lines,
        }

    @classmethod
    def _run_swap_solaris(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Disk Swap 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swap -l 결과를 분석할 수 없습니다.",
            }

        area_lines = []
        failed_lines = []
        found = 0

        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue

            name = parts[0]
            blocks = cls._to_int(parts[3])
            free = cls._to_int(parts[4])
            if blocks is None or free is None or blocks <= 0:
                continue

            found += 1
            used = blocks - free
            used_pct = round((used / blocks) * 100.0, 1)
            area_lines.append(f"{name} Blocks={blocks} Used={used} Free={free} Used%={used_pct:.1f}%")
            if used_pct > criteria_value:
                failed_lines.append(f"{name} 사용률 {used_pct:.1f}%")

        if found == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swap -l 결과에서 Disk Swap 데이터를 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_value, area_lines, failed_lines)

    @classmethod
    def _run_swapon_linux(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Disk Swap 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapon -s 결과에 스왑 정보가 부족합니다.",
            }

        area_lines = []
        failed_lines = []
        found = 0

        data_lines = cls._table_data_after_header(lines, ("filename", "type", "size", "used"))
        if not data_lines:
            data_lines = lines[1:]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 4:
                continue

            name = parts[0]
            size_kb = cls._to_int(parts[2])
            used_kb = cls._to_int(parts[3])
            if size_kb is None or used_kb is None or size_kb <= 0:
                continue

            found += 1
            used_pct = round((used_kb / size_kb) * 100.0, 1)
            free_kb = size_kb - used_kb
            area_lines.append(f"{name} Size={size_kb} KB Used={used_kb} KB Free={free_kb} KB Used%={used_pct:.1f}%")
            if used_pct > criteria_value:
                failed_lines.append(f"{name} 사용률 {used_pct:.1f}%")

        if found == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapon -s 결과에서 Disk Swap 데이터를 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_value, area_lines, failed_lines)

    @classmethod
    def _run_lsps_aix(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Disk Swap 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lsps -a 결과를 분석할 수 없습니다.",
            }

        area_lines = []
        failed_lines = []
        found = 0

        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue

            name = parts[0]
            used_pct = cls._to_float(parts[4].replace("%", ""))
            if used_pct is None:
                continue

            found += 1
            area_lines.append(f"{name} Used%={used_pct:.1f}%")
            if used_pct > criteria_value:
                failed_lines.append(f"{name} 사용률 {used_pct:.1f}%")

        if found == 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lsps -a 결과에서 Disk Swap 데이터를 찾을 수 없습니다.",
            }

        return cls._build_result(criteria_value, area_lines, failed_lines)

    @classmethod
    def _run_swapinfo_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        target_name = "dev"
        try:
            if isinstance(criteria, list) and len(criteria) >= 2:
                target_name = str(criteria[0]).strip().lower()
                criteria_value = float(criteria[1])
            else:
                criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Disk Swap 기준값이 올바르지 않습니다: {criteria}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        target_line = next((line for line in lines if line.lower().startswith(target_name)), None)
        if not target_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"swapinfo -tam 결과에서 {target_name} 라인을 찾을 수 없습니다.",
            }

        parts = target_line.split()
        if len(parts) < 5:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapinfo -tam 결과에서 Disk Swap 값을 파싱할 수 없습니다.",
            }

        total_mb = cls._to_float(parts[1])
        used_mb = cls._to_float(parts[2])
        free_mb = cls._to_float(parts[3])
        used_pct = cls._to_float(parts[4].replace("%", ""))

        if total_mb is None or used_mb is None or free_mb is None or used_pct is None:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapinfo -tam 결과에서 Disk Swap 수치를 해석할 수 없습니다.",
            }

        detail_lines = [
            f"{target_name} Total {total_mb:.0f} KB / Used {used_mb:.0f} KB / Free {free_mb:.0f} KB / Used% {used_pct:.1f}%"
        ]
        failed_lines = []
        if used_pct > criteria_value:
            failed_lines.append(f"{target_name} 사용률 {used_pct:.1f}%")

        return cls._build_result(criteria_value, detail_lines, failed_lines)

    @classmethod
    def _run_wmic_windows(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        try:
            if isinstance(criteria, dict):
                criteria_value = float(criteria.get("max_used_swap", 50))
            else:
                criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Disk Swap 기준값이 올바르지 않습니다: {criteria}",
            }

        items = cls._parse_wmic_blocks(stdout_data)
        if not items:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "pagefile 정보를 파싱하지 못했습니다.",
            }

        total_alloc = 0
        total_used = 0
        detail_lines = []

        for item in items:
            name = (item.get("Name") or item.get("name") or "(unknown)").strip()
            alloc = cls._to_int(item.get("AllocatedBaseSize") or item.get("allocatedbasesize"))
            used = cls._to_int(item.get("CurrentUsage") or item.get("currentusage"))
            peak = cls._to_int(item.get("PeakUsage") or item.get("peakusage"))

            if alloc is None and used is None and peak is None:
                continue

            if alloc is not None:
                total_alloc += alloc
            if used is not None:
                total_used += used

            used_pct = None
            free_mb = None
            if alloc is not None and alloc > 0 and used is not None:
                used_pct = round((used / alloc) * 100.0, 1)
                free_mb = alloc - used

            detail_lines.append(
                f"{name} Size={alloc or 0} MB Used={used or 0} MB Free={free_mb if free_mb is not None else '-'} MB Peak={peak or 0} MB Used%={used_pct if used_pct is not None else '-'}%"
            )

        if total_alloc <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "AllocatedBaseSize 합계가 0MB라 Disk Swap 사용률을 평가할 수 없습니다.",
            }

        total_pct = round((total_used / total_alloc) * 100.0, 1)
        total_free = total_alloc - total_used
        summary_lines = [
            f"Disk Swap 사용률 {total_pct:.1f}%",
            f"Total {total_alloc} MB / Used {total_used} MB / Free {total_free} MB",
        ]

        failed_lines = []
        if total_pct > criteria_value:
            failed_lines = summary_lines + detail_lines
        else:
            detail_lines = summary_lines + detail_lines

        return cls._build_result(criteria_value, detail_lines, failed_lines)

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value).strip())
        except Exception:
            return None

    @staticmethod
    def _to_float(value):
        try:
            return float(str(value).strip())
        except Exception:
            return None

    @staticmethod
    def _parse_wmic_blocks(stdout_data):
        items = []
        current = {}

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            normalized_key = key.strip()
            normalized_value = value.strip()

            if normalized_key in current and current:
                items.append(current)
                current = {}

            current[normalized_key] = normalized_value

        if current:
            items.append(current)

        return items

    @staticmethod
    def _table_data_after_header(lines, header_tokens):
        for index, line in enumerate(lines):
            lowered = line.lower()
            if all(token in lowered for token in header_tokens):
                return lines[index + 1:]
        return []

RULE_KEY = DiskSwapUsageRule.RULE_KEY
RULE_CLASS = DiskSwapUsageRule
