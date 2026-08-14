from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class PagingSpaceRule:
    RULE_KEY = "paging_space"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, dict) and "max_used_swap" in criteria:
            return f"시스템 전체 Paging Space 사용률 {float(criteria.get('max_used_swap', 0)):.1f}% 이하"
        if isinstance(criteria, list) and len(criteria) >= 2:
            try:
                return f"시스템 전체 Paging Space 사용률 {float(criteria[1]):.1f}% 이하"
            except Exception:
                pass
        try:
            return f"시스템 전체 Paging Space 사용률 {float(criteria):.1f}% 이하"
        except Exception:
            return "시스템 전체 Paging Space 사용률 기준 이내"

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

        if "svmon -g" in command:
            if os_type == "Aix":
                return cls._run_svmon_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "swapinfo -tam" in command:
            if os_type == "Hpux":
                return cls._run_swapinfo_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic pagefile get" in command:
            if os_type == "Windows":
                return cls._run_wmic_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_paging_result(cls, used_pct, criteria_value, detail_lines):
        return {
            "is_success": 1,
            "is_pass": 1 if used_pct <= criteria_value else 0,
            "check_target": "Paging Space 사용률",
            "criteria_items": [f"시스템 전체 {criteria_value:.1f}% 이하"],
            "judgement_text": "기준 이내" if used_pct <= criteria_value else "기준 초과",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_swapon_linux(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Paging Space 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapon -s 결과에 스왑 정보가 부족합니다.",
            }

        total_kb = 0
        used_kb = 0
        area_lines = []

        data_lines = cls._table_data_after_header(lines, ("filename", "type", "size", "used"))
        if not data_lines:
            data_lines = lines[1:]

        for line in data_lines:
            parts = line.split()
            if len(parts) < 4:
                continue

            name = parts[0]
            try:
                size_kb = int(parts[2])
                used_area_kb = int(parts[3])
            except Exception:
                continue
            total_kb += size_kb
            used_kb += used_area_kb

            area_pct = 0.0 if size_kb == 0 else round((used_area_kb / size_kb) * 100.0, 1)
            area_lines.append(
                f"{name} Size={size_kb} KB Used={used_area_kb} KB Used%={area_pct:.1f}%"
            )

        if total_kb <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapon -s 결과에서 총 스왑 크기를 계산할 수 없습니다.",
            }

        used_pct = round((used_kb / total_kb) * 100.0, 1)
        return cls._build_paging_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 Paging Space 사용률 {used_pct:.1f}%",
                f"Total {total_kb} KB / Used {used_kb} KB / Free {total_kb - used_kb} KB",
            ]
            + area_lines,
        )

    @classmethod
    def _run_swap_solaris(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Paging Space 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if len(lines) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swap -l 결과를 분석할 수 없습니다.",
            }

        total_blocks = 0
        total_free = 0
        area_lines = []

        for line in lines[1:]:
            parts = line.split()
            if len(parts) < 5:
                continue

            name = parts[0]
            blocks = int(parts[3])
            free = int(parts[4])
            used = blocks - free
            total_blocks += blocks
            total_free += free

            area_pct = 0.0 if blocks == 0 else round((used / blocks) * 100.0, 1)
            area_lines.append(
                f"{name} Blocks={blocks} Used={used} Free={free} Used%={area_pct:.1f}%"
            )

        if total_blocks <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swap -l 결과에서 총 Paging Space 크기를 계산할 수 없습니다.",
            }

        total_used = total_blocks - total_free
        used_pct = round((total_used / total_blocks) * 100.0, 1)
        return cls._build_paging_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 Paging Space 사용률 {used_pct:.1f}%",
                f"Total {total_blocks} Blocks / Used {total_used} Blocks / Free {total_free} Blocks",
            ]
            + area_lines,
        )

    @classmethod
    def _run_svmon_aix(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Paging Space 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        target_line = next(
            (line.strip() for line in (stdout_data or "").splitlines() if line.strip().startswith("pg space")),
            None,
        )
        if not target_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 'pg space' 라인을 찾을 수 없습니다.",
            }

        parts = target_line[len("pg space"):].strip().split()
        if len(parts) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 Paging Space 값을 파싱할 수 없습니다.",
            }

        size = int(parts[0])
        inuse = int(parts[1])
        if size <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 Paging Space size 값이 0 이하입니다.",
            }

        used_pct = round((inuse / size) * 100.0, 1)
        return cls._build_paging_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 Paging Space 사용률 {used_pct:.1f}%",
                f"Total {size} / Used {inuse} / Free {size - inuse}",
            ],
        )

    @classmethod
    def _run_swapinfo_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        target_name = "total"
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
                "reason_text": f"Paging Space 기준값이 올바르지 않습니다: {criteria}",
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
                "reason_text": "swapinfo -tam 결과에서 Paging Space 값을 파싱할 수 없습니다.",
            }

        total_mb = float(parts[1])
        used_mb = float(parts[2])
        free_mb = float(parts[3])
        used_pct = float(parts[4].replace("%", ""))

        return cls._build_paging_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 Paging Space 사용률 {used_pct:.1f}%",
                f"Total {total_mb:.0f} MB / Used {used_mb:.0f} MB / Free {free_mb:.0f} MB",
            ],
        )

    @classmethod
    def _run_wmic_windows(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        try:
            criteria_value = float(criteria.get("max_used_swap", 50))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Paging Space 기준값이 숫자가 아닙니다: {criteria}",
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
        area_lines = []

        for item in items:
            name = (item.get("Name") or "").strip() or "pagefile"
            alloc = cls._to_int(item.get("AllocatedBaseSize"))
            used = cls._to_int(item.get("CurrentUsage"))
            peak = cls._to_int(item.get("PeakUsage"))

            if alloc is not None:
                total_alloc += alloc
            if used is not None:
                total_used += used

            pct = 0.0 if not alloc else round((used or 0) / alloc * 100.0, 1)
            area_lines.append(
                f"{name} Size={alloc or 0} MB Used={used or 0} MB Peak={peak or 0} MB Used%={pct:.1f}%"
            )

        if total_alloc <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "AllocatedBaseSize 합계가 0MB라 Paging Space를 평가할 수 없습니다.",
            }

        used_pct = round((total_used / total_alloc) * 100.0, 1)
        return cls._build_paging_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 Paging Space 사용률 {used_pct:.1f}%",
                f"Total {total_alloc} MB / Used {total_used} MB / Free {total_alloc - total_used} MB",
            ]
            + area_lines,
        )

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
            if key.strip() in current and current:
                items.append(current)
                current = {}
            current[key.strip()] = value.strip()

        if current:
            items.append(current)

        return items

    @staticmethod
    def _to_int(value):
        try:
            return int(str(value).strip())
        except Exception:
            return None

    @staticmethod
    def _table_data_after_header(lines, header_tokens):
        for index, line in enumerate(lines):
            lowered = line.lower()
            if all(token in lowered for token in header_tokens):
                return lines[index + 1:]
        return []

RULE_KEY = PagingSpaceRule.RULE_KEY
RULE_CLASS = PagingSpaceRule
