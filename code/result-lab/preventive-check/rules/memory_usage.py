import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class MemoryUsageRule:
    RULE_KEY = "memory_usage"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, dict):
            if "max_used_mem" in criteria:
                return (
                    f"메모리 Used {float(criteria.get('max_used_mem', 0)):.1f}% 이하 / "
                    f"Free {float(criteria.get('min_free_mem_pct', 0)):.1f}% 이상"
                )
        if isinstance(criteria, list) and len(criteria) >= 2:
            try:
                return f"시스템 전체 메모리 사용률 {float(criteria[1]):.1f}% 이하"
            except Exception:
                pass
        try:
            return f"시스템 전체 메모리 사용률 {float(criteria):.1f}% 이하"
        except Exception:
            return "시스템 전체 메모리 사용률 기준 이내"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "free -m" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_free_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "prtconf" in command and "vmstat" in command:
            if os_type == "Solaris":
                return cls._run_solaris_memory(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc memory" in command:
            if os_type == "Aix":
                return cls._run_lsdev_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "swapinfo -tam" in command:
            if os_type == "Hpux":
                return cls._run_swapinfo_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic os get freephysicalmemory,totalvisiblememorysize /value" in command:
            if os_type == "Windows":
                return cls._run_wmic_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_usage_result(cls, used_pct, criteria_value, detail_lines):
        return {
            "is_success": 1,
            "is_pass": 1 if used_pct <= criteria_value else 0,
            "check_target": "메모리 사용률",
            "criteria_items": [f"시스템 전체 {criteria_value:.1f}% 이하"],
            "judgement_text": "기준 이내" if used_pct <= criteria_value else "기준 초과",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_free_linux(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"메모리 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        output_lines = (stdout_data or "").splitlines()
        mem_index = next(
            (index for index, line in enumerate(output_lines) if line.lower().strip().startswith("mem:")),
            None,
        )
        mem_line = output_lines[mem_index] if mem_index is not None else None
        if not mem_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "free -m 결과에서 Mem 라인을 찾을 수 없습니다.",
            }

        parts = mem_line.split()
        if len(parts) < 4:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "free -m 결과에서 메모리 값을 파싱할 수 없습니다.",
            }

        total = int(parts[1])
        raw_used = int(parts[2])
        free = int(parts[3])
        header_line = output_lines[mem_index - 1].lower() if mem_index and mem_index > 0 else ""
        available = int(parts[6]) if "available" in header_line and len(parts) >= 7 else None

        if available is None:
            buffer_cache_line = next(
                (
                    line
                    for line in (stdout_data or "").splitlines()
                    if line.strip().startswith("-/+ buffers/cache:")
                ),
                None,
            )
            if buffer_cache_line:
                buffer_parts = buffer_cache_line.split()
                if len(buffer_parts) >= 4:
                    available = int(buffer_parts[-1])

        if available is None and len(parts) >= 6:
            try:
                available = free + int(parts[4]) + int(parts[5])
            except Exception:
                available = free
        elif available is None:
            available = free

        used = total - available
        used_pct = round((used / total) * 100.0, 1)
        free_pct = round((available / total) * 100.0, 1)

        return cls._build_usage_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 메모리 사용률 {used_pct:.1f}%",
                f"Free/Available Memory {free_pct:.1f}%",
                f"Total {total} MB / Used {used} MB / RawUsed {raw_used} MB / Free {free} MB / Available {available} MB",
            ],
        )

    @classmethod
    def _run_solaris_memory(cls, params, stdout_data):
        try:
            criteria_value = float(params.get("inspection_criteria"))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"메모리 기준값이 숫자가 아닙니다: {params.get('inspection_criteria')}",
            }

        total_match = re.search(r"Total Memory:\s*(\d+)\s*MB", stdout_data or "", re.IGNORECASE)
        free_match = re.search(r"Free Memory\s*:\s*(\d+)\s*MB", stdout_data or "", re.IGNORECASE)

        if not total_match or not free_match:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Solaris 메모리 출력에서 Total Memory 또는 Free Memory를 찾을 수 없습니다.",
            }

        total = int(total_match.group(1))
        free = int(free_match.group(1))
        used = total - free
        used_pct = round((used / total) * 100.0, 1)

        return cls._build_usage_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 메모리 사용률 {used_pct:.1f}%",
                f"Total {total} MB / Used {used} MB / Free {free} MB",
            ],
        )

    @classmethod
    def _run_lsdev_aix(cls, params, stdout_data):
        expected_status = str(params.get("inspection_criteria") or "Available").strip()
        memory_lines = [
            line.strip()
            for line in (stdout_data or "").splitlines()
            if line.strip().lower().startswith("mem")
        ]

        if not memory_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "lsdev -Cc memory 결과에서 메모리 장치 정보를 찾을 수 없습니다.",
            }

        failed_items = []
        for line in memory_lines:
            parts = line.split()
            if len(parts) < 2:
                failed_items.append(f"파싱 실패 {line}")
                continue

            device_name = parts[0]
            status = parts[1]
            if status.lower() != expected_status.lower():
                failed_items.append(f"{device_name} {status}")

        return {
            "is_success": 1,
            "is_pass": 0 if failed_items else 1,
            "check_target": "메모리 사용률",
            "criteria_items": [f"모든 메모리 장치가 {expected_status} 상태일 것"],
            "judgement_text": "기준 초과" if failed_items else "기준 이내",
            "detail_lines": (
                [f"전체 메모리 장치 {len(memory_lines)}개", f"정상 상태 기준 {expected_status}"]
                + ([f"비정상 메모리 장치 {item}" for item in failed_items] if failed_items else ["비정상 메모리 장치 없음"])
            ),
        }

    @classmethod
    def _run_swapinfo_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        if not isinstance(criteria, list) or len(criteria) < 2:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Hpux 메모리 기준값은 [target, threshold] 형식이어야 합니다.",
            }

        target_name = str(criteria[0]).strip().lower()
        target_aliases = {target_name}
        if target_name == "memory":
            target_aliases.add("mem")

        try:
            criteria_value = float(criteria[1])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"메모리 기준값이 숫자가 아닙니다: {criteria[1]}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        data_line = next(
            (line for line in lines if any(line.lower().startswith(alias) for alias in target_aliases)),
            None,
        )

        if not data_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"swapinfo -tam 결과에서 {target_name} 라인을 찾을 수 없습니다.",
            }

        parts = data_line.split()
        if len(parts) < 5:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "swapinfo -tam 결과에서 메모리 값을 파싱할 수 없습니다.",
            }

        total = float(parts[1])
        used = float(parts[2])
        free = float(parts[3])
        used_pct = round((used / total) * 100.0, 1)

        return cls._build_usage_result(
            used_pct,
            criteria_value,
            [
                f"시스템 전체 메모리 사용률 {used_pct:.1f}%",
                f"Total {total:.0f} MB / Used {used:.0f} MB / Free {free:.0f} MB",
            ],
        )

    @classmethod
    def _run_wmic_windows(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}
        try:
            criteria_value = float(criteria.get("max_used_mem", 80))
            min_free_pct = float(criteria.get("min_free_mem_pct", 20))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Windows 메모리 기준값이 숫자가 아닙니다: {criteria}",
            }

        kv = cls._parse_wmic_kv(stdout_data)
        free_kb = cls._to_int(kv.get("FreePhysicalMemory"))
        total_kb = cls._to_int(kv.get("TotalVisibleMemorySize"))

        if free_kb is None or total_kb is None or total_kb <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Windows 메모리 출력에서 FreePhysicalMemory 또는 TotalVisibleMemorySize를 파싱하지 못했습니다.",
            }

        used_kb = total_kb - free_kb
        used_pct = round((used_kb / total_kb) * 100.0, 1)
        free_pct = round((free_kb / total_kb) * 100.0, 1)
        total_mb = round(total_kb / 1024, 1)
        used_mb = round(used_kb / 1024, 1)
        free_mb = round(free_kb / 1024, 1)
        is_pass = 1 if used_pct <= criteria_value and free_pct >= min_free_pct else 0

        return {
            "is_success": 1,
            "is_pass": is_pass,
            "check_target": "메모리 사용률",
            "criteria_items": [
                f"시스템 전체 Used {criteria_value:.1f}% 이하",
                f"시스템 전체 Free {min_free_pct:.1f}% 이상",
            ],
            "judgement_text": "기준 이내" if is_pass == 1 else "기준 초과",
            "detail_lines": [
                f"시스템 전체 메모리 사용률 {used_pct:.1f}%",
                f"시스템 전체 가용 메모리 비율 {free_pct:.1f}%",
                f"Total {total_mb:.1f} MB / Used {used_mb:.1f} MB / Free {free_mb:.1f} MB",
            ],
        }

    @staticmethod
    def _parse_wmic_kv(stdout_data):
        kv = {}
        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            kv[key.strip()] = value.strip()

        return kv

    @staticmethod
    def _to_int(value):
        try:
            return int(value)
        except Exception:
            return None

RULE_KEY = MemoryUsageRule.RULE_KEY
RULE_CLASS = MemoryUsageRule
