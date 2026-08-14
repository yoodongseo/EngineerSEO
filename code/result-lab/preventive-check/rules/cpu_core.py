from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class CpuCoreRule:
    RULE_KEY = "cpu_core"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "모든 CPU 코어 정상 상태"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "lscpu" in command:
            if os_type == "Linux":
                return cls._run_lscpu_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "/proc/cpuinfo" in command:
            if os_type == "Linux5":
                return cls._run_lscpu_linux(params, stdout_data)
            return build_unsupported_command(params)

        if "psrinfo -v" in command:
            if os_type == "Solaris":
                return cls._run_psrinfo_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc processor" in command:
            if os_type == "Aix":
                return cls._run_lsdev_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "ioscan -fnc processor" in command:
            if os_type == "Hpux":
                return cls._run_ioscan_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "wmic path win32_processor" in command:
            if os_type == "Windows":
                return cls._run_wmic_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _build_core_result(cls, is_pass, detail_lines):
        return {
            "is_success": 1,
            "is_pass": is_pass,
            "check_target": "CPU 코어 상태",
            "criteria_items": ["모든 CPU 코어가 정상 상태일 것"],
            "judgement_text": "기준 이내" if is_pass == 1 else "기준 초과",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_lscpu_linux(cls, params, stdout_data):
        try:
            total_cpus_text = cls._parse_key_value(stdout_data, "CPU(s)")
            online_cpu_text = cls._parse_key_value(stdout_data, "On-line CPU(s) list")

            total_cpus = int(total_cpus_text)
            all_cpu_set = set(range(total_cpus))
            online_cpu_set = cls._parse_cpu_list_to_set(online_cpu_text)
            offline_cpus = sorted(all_cpu_set - online_cpu_set)

            detail_lines = [
                f"전체 CPU 개수 {total_cpus}개",
                f"온라인 CPU 번호 {online_cpu_text}",
            ]

            if offline_cpus:
                detail_lines.append(
                    f"오프라인 CPU 번호 {', '.join(str(cpu) for cpu in offline_cpus)}"
                )
                return cls._build_core_result(0, detail_lines)

            detail_lines.append("오프라인 CPU 번호 없음")
            return cls._build_core_result(1, detail_lines)
        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"lscpu 결과 파싱 실패: {err}",
            }

    @classmethod
    def _run_psrinfo_solaris(cls, params, stdout_data):
        try:
            lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
            if not lines:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "psrinfo -v 결과가 비어 있습니다.",
                }

            blocks = []
            current_block = []

            for line in lines:
                stripped = line.strip()
                if stripped.startswith(
                    ("Status of processor", "Status of virtual processor", "프로세서", "가상 프로세서")
                ):
                    if current_block:
                        blocks.append(current_block)
                    current_block = [line]
                    continue

                if current_block:
                    current_block.append(line)

            if current_block:
                blocks.append(current_block)

            if not blocks:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "psrinfo -v 결과에서 프로세서 블록을 찾을 수 없습니다.",
                }

            offline_blocks = []
            for block in blocks:
                block_text = "\n".join(block)
                if "on-line" not in block_text.lower():
                    offline_blocks.append(block[0].strip())

            detail_lines = [f"전체 프로세서 개수 {len(blocks)}개"]

            if offline_blocks:
                detail_lines.extend(f"오프라인 프로세서 {block_line}" for block_line in offline_blocks)
                return cls._build_core_result(0, detail_lines)

            detail_lines.append("오프라인 프로세서 없음")
            return cls._build_core_result(1, detail_lines)
        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"psrinfo -v 결과 파싱 실패: {err}",
            }

    @classmethod
    def _run_lsdev_aix(cls, params, stdout_data):
        try:
            expected_status = str(params.get("inspection_criteria") or "Available").strip()
            lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
            processor_lines = [line for line in lines if line.lower().startswith("proc")]

            if not processor_lines:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "lsdev -Cc processor 결과에서 프로세서 정보를 찾을 수 없습니다.",
                }

            failed_processors = []
            for line in processor_lines:
                parts = line.split()
                if len(parts) < 2:
                    failed_processors.append(f"파싱 실패 {line}")
                    continue

                proc_name = parts[0]
                status = parts[1]
                if status.lower() != expected_status.lower():
                    failed_processors.append(f"{proc_name} {status}")

            detail_lines = [f"전체 CPU 개수 {len(processor_lines)}개", f"정상 상태 기준 {expected_status}"]

            if failed_processors:
                detail_lines.extend(f"비정상 CPU {item}" for item in failed_processors)
                return cls._build_core_result(0, detail_lines)

            detail_lines.append("비정상 CPU 없음")
            return cls._build_core_result(1, detail_lines)
        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"lsdev -Cc processor 결과 파싱 실패: {err}",
            }

    @classmethod
    def _run_ioscan_hpux(cls, params, stdout_data):
        try:
            expected_state = str(params.get("inspection_criteria") or "CLAIMED").strip()
            lines = (stdout_data or "").splitlines()
            data_started = False
            processor_lines = []

            for line in lines:
                stripped = line.strip()

                if not data_started and stripped.startswith("========="):
                    data_started = True
                    continue

                if not data_started or not stripped:
                    continue

                if stripped.lower().startswith("processor "):
                    processor_lines.append(stripped)

            if not processor_lines:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "ioscan -fnC processor 결과에서 processor 정보를 찾을 수 없습니다.",
                }

            failed_processors = []
            for line in processor_lines:
                if expected_state.upper() not in line.upper():
                    failed_processors.append(line)

            detail_lines = [f"전체 CPU 개수 {len(processor_lines)}개", f"정상 상태 기준 {expected_state}"]

            if failed_processors:
                detail_lines.extend(f"비정상 CPU {line}" for line in failed_processors)
                return cls._build_core_result(0, detail_lines)

            detail_lines.append("비정상 CPU 없음")
            return cls._build_core_result(1, detail_lines)
        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"ioscan -fnC processor 결과 파싱 실패: {err}",
            }

    @classmethod
    def _run_wmic_windows(cls, params, stdout_data):
        try:
            criteria = params.get("inspection_criteria") or {}
            status_ok = str(criteria.get("status_ok", "OK")).strip()
            availability_ok = str(criteria.get("availability_ok", 3)).strip()
            cpu_status_ok = str(criteria.get("cpu_status_ok", 1)).strip()

            processor_items = cls._parse_windows_wmic_blocks(stdout_data)
            if not processor_items:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "Win32_Processor 결과에서 CPU 정보를 찾을 수 없습니다.",
                }

            failed_processors = []
            detail_lines = []

            for item in processor_items:
                device_id = item.get("DeviceID", "-")
                status = item.get("Status", "-")
                availability = item.get("Availability", "-")
                cpu_status = item.get("CpuStatus", "-")
                cores = item.get("NumberOfCores", "-")
                logical = item.get("NumberOfLogicalProcessors", "-")

                detail_lines.append(
                    f"{device_id} Status={status} Availability={availability} CpuStatus={cpu_status} Cores={cores} Logical={logical}"
                )

                if (
                    status.upper() != status_ok.upper()
                    or availability != availability_ok
                    or cpu_status != cpu_status_ok
                ):
                    failed_processors.append(
                        f"{device_id} Status={status} Availability={availability} CpuStatus={cpu_status}"
                    )

            detail_lines.insert(0, f"전체 CPU 개수 {len(processor_items)}개")

            if failed_processors:
                detail_lines.extend(f"비정상 CPU {item}" for item in failed_processors)
                return cls._build_core_result(0, detail_lines)

            detail_lines.append("비정상 CPU 없음")
            return cls._build_core_result(1, detail_lines)
        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Win32_Processor 결과 파싱 실패: {err}",
            }

    @staticmethod
    def _parse_key_value(output, key):
        target = str(key).strip().lower()
        for line in (output or "").splitlines():
            stripped = line.strip()
            if ":" not in stripped:
                continue

            left, right = stripped.split(":", 1)
            if left.strip().lower() == target:
                return right.strip()

        raise ValueError(f"'{key}' 항목을 찾을 수 없습니다.")

    @staticmethod
    def _parse_cpu_list_to_set(cpu_list_text):
        cpu_set = set()

        for token in (cpu_list_text or "").split(","):
            value = token.strip()
            if not value:
                continue

            if "-" in value:
                start_text, end_text = value.split("-", 1)
                start = int(start_text)
                end = int(end_text)
                cpu_set.update(range(start, end + 1))
                continue

            cpu_set.add(int(value))

        return cpu_set

    @staticmethod
    def _parse_windows_wmic_blocks(stdout_data):
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

RULE_KEY = CpuCoreRule.RULE_KEY
RULE_CLASS = CpuCoreRule
