import re

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class MemoryScanRule:
    RULE_KEY = "memory_scan"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "할당된 메모리 정상 인식"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "dmidecode -t memory" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_dmidecode_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "prtdiag" in command:
            if os_type == "Solaris":
                return cls._run_prtdiag_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "machinfo" in command:
            if os_type == "Hpux":
                return cls._run_machinfo_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "svmon -g" in command:
            if os_type == "Aix":
                return cls._run_svmon_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic memorychip get" in command:
            if os_type == "Windows":
                return cls._run_wmic_memorychip_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_scan_result(cls, is_pass, detail_lines):
        return {
            "is_success": 1,
            "is_pass": is_pass,
            "check_target": "메모리 상태",
            "criteria_items": ["메모리 장치 정보가 정상적으로 인식될 것"],
            "judgement_text": "기준 이내" if is_pass == 1 else "기준 초과",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_dmidecode_linux(cls, params, stdout_data):
        raw = stdout_data or ""
        lowered = raw.lower()

        if "command not found" in lowered or "not found" in lowered:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dmidecode 명령어가 설치되어 있지 않습니다.",
            }

        if "permission denied" in lowered and (
            "/dev/mem" in lowered or "/sys/firmware/dmi/tables" in lowered
        ):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": (
                    "dmidecode 실행은 되었으나 DMI 정보 접근 권한이 차단되었습니다. "
                    "/dev/mem 또는 /sys/firmware/dmi/tables 접근이 제한된 환경일 수 있습니다. "
                    "root 권한, 보안정책(SELinux/하드닝), 컨테이너/가상화 환경 설정을 확인해야 합니다."
                ),
            }

        if "permission denied" in lowered:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dmidecode 실행 결과에 권한 오류가 있습니다.",
            }

        modules = re.split(r"\n(?=Memory Device)", stdout_data or "")
        valid_modules = []
        info_modules = []

        for index, module in enumerate(modules, 1):
            if "Memory Device" not in module:
                continue

            size = cls._extract_field(module, "Size")
            speed = cls._extract_field(module, "Speed")
            form_factor = cls._extract_field(module, "Form Factor")
            rank = cls._extract_field(module, "Rank")

            if not size and not speed and not form_factor and not rank:
                continue

            valid_modules.append(index)

            if not size or size == "No Module Installed":
                info_modules.append(f"Memory Device {index} Size={size or 'Unknown'}")
                continue

            extra_info = []
            if speed:
                extra_info.append(f"Speed={speed}")
            if rank:
                extra_info.append(f"Rank={rank}")

            if extra_info:
                info_modules.append(f"Memory Device {index} " + ", ".join(extra_info))

        if not valid_modules:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "dmidecode -t memory 결과에서 메모리 장치 정보를 찾을 수 없습니다.",
            }

        detail_lines = [f"메모리 장치 {len(valid_modules)}개 확인"]
        detail_lines.extend(info_modules)

        return cls._build_scan_result(1, detail_lines)

    @classmethod
    def _run_prtdiag_solaris(cls, params, stdout_data):
        found_line = None
        memory_device_lines = []

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if "Memory size:" in stripped or "메모리 크기" in stripped:
                found_line = stripped
                break

            if re.match(r"^RAM\s+in use\b", stripped, re.IGNORECASE):
                memory_device_lines.append(stripped)

        if found_line:
            return cls._build_scan_result(1, [found_line])

        if memory_device_lines:
            return cls._build_scan_result(1, memory_device_lines)

        if not found_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "prtdiag 결과에서 메모리 인식 정보를 찾을 수 없습니다.",
            }

    @classmethod
    def _run_machinfo_hpux(cls, params, stdout_data):
        physical_memory_mb = None
        configured_memory_mb = None

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()

            physical_match = re.search(r"Physical Memory\s*:\s*(.+)", stripped)
            if physical_match:
                physical_memory_mb = cls._extract_mb(physical_match.group(1))

            configured_match = re.search(r"Configured Memory\s*:\s*(.+)", stripped)
            if configured_match:
                configured_memory_mb = cls._extract_mb(configured_match.group(1))

            if re.match(r"^Memory:\s*", stripped) and physical_memory_mb is None:
                direct = re.search(r"^Memory:\s*(.+)", stripped)
                if direct:
                    physical_memory_mb = cls._extract_mb(direct.group(1))

        if physical_memory_mb is None or physical_memory_mb <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "machinfo 결과에서 Physical Memory 정보를 찾을 수 없습니다.",
            }

        detail_lines = [f"Physical Memory {physical_memory_mb} MB"]
        if configured_memory_mb is not None and configured_memory_mb > 0:
            detail_lines.append(f"Configured Memory {configured_memory_mb} MB")

        return cls._build_scan_result(1, detail_lines)

    @classmethod
    def _run_svmon_aix(cls, params, stdout_data):
        memory_line = next(
            (line.strip() for line in (stdout_data or "").splitlines() if line.strip().startswith("memory")),
            None,
        )

        if not memory_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 memory 라인을 찾을 수 없습니다.",
            }

        parts = memory_line.split()
        if len(parts) < 3:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 메모리 값을 파싱할 수 없습니다.",
            }

        size = int(parts[1])
        inuse = int(parts[2])
        if size <= 0:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "svmon -G 결과에서 memory size 값이 0 이하입니다.",
            }

        detail_lines = [
            f"memory size {size}",
            f"memory inuse {inuse}",
        ]
        return cls._build_scan_result(1, detail_lines)

    @classmethod
    def _run_wmic_memorychip_windows(cls, params, stdout_data):
        raw = stdout_data or ""
        lowered = raw.lower()
        if "invalid query" in lowered or "error:" in lowered:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "wmic memorychip 명령 실행 결과에 오류가 있습니다.",
            }

        items = cls._parse_wmic_blocks(stdout_data)
        if not items:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "wmic memorychip 결과에서 메모리 슬롯 정보를 찾을 수 없습니다.",
            }

        failed_items = []
        detail_lines = [f"메모리 슬롯 {len(items)}개 확인"]

        for item in items:
            bank = (item.get("BankLabel") or "").strip() or "(unknown)"
            capacity = cls._to_int(item.get("Capacity"))
            configured_speed = cls._to_int(item.get("ConfiguredClockSpeed"))
            speed = cls._to_int(item.get("Speed"))
            status = (item.get("Status") or "").strip()

            slot_parts = [
                f"{bank} Capacity={capacity or 0}",
                f"Speed={speed or 0}",
            ]
            if configured_speed is not None:
                slot_parts.append(f"ConfiguredClockSpeed={configured_speed}")
            slot_parts.append(f"Status={status or '-'}")
            detail_lines.append(" ".join(slot_parts))

            if capacity is None or capacity <= 0:
                failed_items.append(f"{bank} Capacity={capacity or 0}")
            if speed is not None and speed < 0:
                failed_items.append(f"{bank} Speed={speed}")
            if configured_speed is not None and configured_speed < 0:
                failed_items.append(f"{bank} ConfiguredClockSpeed={configured_speed}")

        if failed_items:
            detail_lines.extend(f"비정상 메모리 슬롯 {item}" for item in failed_items)
            return cls._build_scan_result(0, detail_lines)

        detail_lines.append("비정상 메모리 슬롯 없음")
        return cls._build_scan_result(1, detail_lines)

    @staticmethod
    def _extract_field(block_text, field_name):
        match = re.search(rf"{re.escape(field_name)}:\s*(.+)", block_text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_mb(text):
        mb_match = re.search(r"(\d+)\s*MB", text or "", re.IGNORECASE)
        if mb_match:
            return int(mb_match.group(1))

        gb_match = re.search(r"(\d+\.?\d*)\s*GB", text or "", re.IGNORECASE)
        if gb_match:
            return int(float(gb_match.group(1)) * 1024)

        return None

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
    def _to_int(value):
        try:
            return int(value)
        except Exception:
            return None

RULE_KEY = MemoryScanRule.RULE_KEY
RULE_CLASS = MemoryScanRule
