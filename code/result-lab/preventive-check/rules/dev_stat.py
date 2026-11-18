import re
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class DevStatRule:
    RULE_KEY = "dev_stat"

    @classmethod
    def criteria_required(cls, command):                
        if command == "lsblk" or "/proc/partitions" in command:
            return False        
        else:     
            return True        

    @classmethod
    def build_check_rules(cls, params):
        return "디스크 정상 인식 상태"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "machinfo" in command:
            if os_type == "Hpux":
                return cls._run_machinfo(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc memory" in command:
            if os_type in ("Aix", "Hpux"):
                return cls._run_lsdev_memory(params, stdout_data)
            return build_unsupported_command(params)

        if "ioscan -fnc processor" in command:
            if os_type == "Hpux":
                return cls._run_ioscan_processor(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc processor" in command:
            if os_type in ("Aix", "Hpux"):
                return cls._run_lsdev_processor(params, stdout_data)
            return build_unsupported_command(params)

        if "ioscan -fnc disk" in command:
            if os_type == "Hpux":
                return cls._run_ioscan_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "lsdev -cc disk" in command:
            if os_type in ("Aix", "Hpux"):
                return cls._run_lsdev_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "lsblk" in command:
            if os_type == "Linux":
                return cls._run_lsblk_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "/proc/partitions" in command:
            if os_type == "Linux5":
                return cls._run_lsblk_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "format" in command:
            if os_type == "Solaris":
                return cls._run_solaris_format_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "get-disk" in command:
            if os_type == "Windows":
                return cls._run_get_disk_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @staticmethod
    def _extract_mb_from_string(mem_str):
        mb_match = re.search(r"(\d+)\s*MB", mem_str)
        if mb_match:
            return int(mb_match.group(1))

        gb_match = re.search(r"(\d+\.?\d*)\s*GB", mem_str)
        if gb_match:
            return int(float(gb_match.group(1)) * 1024)

        return 0

    @staticmethod
    def _normalize_text(value):
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _build_failure(reason_text):
        return {
            "is_success": 0,
            "is_pass": 0,
            "reason_text": reason_text,
        }

    @staticmethod
    def _build_result(check_target, criteria_text, judgement_text, detail_lines, is_pass):
        result = {
            "is_success": 1,
            "is_pass": is_pass,
            "check_target": check_target,
            "judgement_text": judgement_text,
            "detail_lines": detail_lines,
        }

        if isinstance(criteria_text, list):
            result["criteria_items"] = criteria_text
        else:
            result["criteria_text"] = criteria_text

        return result

    @classmethod
    def _run_machinfo(cls, params, stdout_data):
        text = stdout_data or ""

        if "Memory Information" not in text and "Memory: " not in text:
            return cls._build_failure(
                f"필수 메모리 정보를 찾을 수 없습니다. (출력값: {text.strip()[:200]}...)"
            )

        physical_memory_mb = None
        configured_memory_mb = None

        for raw_line in text.splitlines():
            line = raw_line.strip()

            physical_match = re.search(r"Physical Memory\s*:\s*(.+)", line)
            if physical_match:
                physical_memory_mb = cls._extract_mb_from_string(physical_match.group(1))

            configured_match = re.search(r"Configured Memory\s*:\s*(.+)", line)
            if configured_match:
                configured_memory_mb = cls._extract_mb_from_string(configured_match.group(1))

            if re.match(r"^Memory:\s*", line) and physical_memory_mb is None:
                direct_memory_match = re.search(r"^Memory:\s*(.+)", line)
                if direct_memory_match:
                    physical_memory_mb = cls._extract_mb_from_string(direct_memory_match.group(1))

        if physical_memory_mb is None or physical_memory_mb <= 0:
            return cls._build_result(
                check_target="메모리 장치 상태",
                criteria_text="Physical Memory 0MB 초과",
                judgement_text="점검 필요",
                detail_lines=["Physical Memory 정보가 없거나 0MB 이하입니다."],
                is_pass=0,
            )

        memory_line = f"Physical Memory {physical_memory_mb} MB"
        if configured_memory_mb is not None:
            memory_line = f"{memory_line} (Configured: {configured_memory_mb} MB)"

        return cls._build_result(
            check_target="메모리 장치 상태",
            criteria_text="Physical Memory 0MB 초과",
            judgement_text="정상",
            detail_lines=[memory_line],
            is_pass=1,
        )

    @classmethod
    def _run_lsdev_memory(cls, params, stdout_data):
        expected_status = cls._normalize_text(params.get("inspection_criteria"))
        return cls._run_lsdev_generic(
            stdout_data=stdout_data,
            expected_status=expected_status,
            check_target="메모리 장치 상태",
        )

    @classmethod
    def _run_lsdev_disk(cls, params, stdout_data):
        expected_status = cls._normalize_text(params.get("inspection_criteria"))
        return cls._run_lsdev_generic(
            stdout_data=stdout_data,
            expected_status=expected_status,
            check_target="디스크 장치 상태",
        )

    @classmethod
    def _run_lsdev_generic(cls, stdout_data, expected_status, check_target):
        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines:
            return cls._build_failure("lsdev 명령어 출력이 없습니다.")

        if not expected_status:
            return cls._build_failure("inspection_criteria가 비어 있어 상태 비교를 수행할 수 없습니다.")

        failed_devices = []
        total_devices = 0
        expected_lower = expected_status.lower()

        for line in lines:
            parts = line.split()
            if len(parts) < 2:
                continue

            device_name = parts[0]
            status = parts[1]

            if device_name.lower() == "name" and status.lower() == "status":
                continue

            total_devices += 1
            if status.lower() != expected_lower:
                failed_devices.append(f"{device_name}({status})")

        if total_devices == 0:
            return cls._build_failure("lsdev 결과에서 유효한 장치 정보를 찾을 수 없습니다.")

        if failed_devices:
            return cls._build_result(
                check_target=check_target,
                criteria_text=f"상태 '{expected_status}'",
                judgement_text="점검 필요",
                detail_lines=[f"비정상 장치: {', '.join(failed_devices)}"],
                is_pass=0,
            )

        return cls._build_result(
            check_target=check_target,
            criteria_text=f"상태 '{expected_status}'",
            judgement_text="정상",
            detail_lines=[f"전체 {total_devices}개 장치가 정상 상태입니다."],
            is_pass=1,
        )

    @classmethod
    def _run_ioscan_processor(cls, params, stdout_data):
        text = stdout_data or ""
        if "not found" in text.lower():
            return cls._build_failure(
                f"명령어 실행 실패: {text.strip()[:200]}..."
            )

        if not text or "Description" not in text:
            return cls._build_failure("ioscan 결과에서 Description 헤더를 찾을 수 없습니다.")

        abnormal_keywords = ["UNCLAIMED", "NO_HW", "ERROR"]
        processor_count = 0
        issue_lines = []

        data_started = False
        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not data_started and line.startswith("======"):
                data_started = True
                continue

            if not data_started or not line:
                continue

            for keyword in abnormal_keywords:
                if keyword in line:
                    issue_lines.append(f"비정상 키워드 '{keyword}' 발견: {line}")
                    break

            if re.match(r"processor\s+\d+", line):
                processor_count += 1
                if "CLAIMED" not in line:
                    issue_lines.append(f"S/W state CLAIMED 아님: {line}")

        if processor_count == 0:
            issue_lines.insert(0, "processor 항목이 발견되지 않았습니다.")

        if issue_lines:
            return cls._build_result(
                check_target="CPU 장치 상태",
                criteria_text="모든 processor 항목 CLAIMED",
                judgement_text="점검 필요",
                detail_lines=issue_lines,
                is_pass=0,
            )

        return cls._build_result(
            check_target="CPU 장치 상태",
            criteria_text="모든 processor 항목 CLAIMED",
            judgement_text="정상",
            detail_lines=[f"processor 항목 {processor_count}개 모두 정상입니다."],
            is_pass=1,
        )

    @classmethod
    def _run_lsdev_processor(cls, params, stdout_data):
        expected_status = cls._normalize_text(params.get("inspection_criteria"))
        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not lines:
            return cls._build_failure("lsdev -Cc processor 명령어 출력이 없습니다.")

        if not expected_status:
            return cls._build_failure("inspection_criteria가 비어 있어 상태 비교를 수행할 수 없습니다.")

        failed_procs = []
        total_procs = 0
        expected_lower = expected_status.lower()

        for line in lines:
            if not line.lower().startswith("proc"):
                continue

            total_procs += 1
            parts = line.split()
            if len(parts) < 2:
                failed_procs.append(f"파싱 실패: {line}")
                continue

            proc_name = parts[0]
            status = parts[1]
            if status.lower() != expected_lower:
                failed_procs.append(f"{proc_name}({status})")

        if total_procs == 0:
            return cls._build_failure("유효한 프로세서 정보를 찾을 수 없습니다.")

        if failed_procs:
            return cls._build_result(
                check_target="CPU 장치 상태",
                criteria_text=f"상태 '{expected_status}'",
                judgement_text="점검 필요",
                detail_lines=[f"비정상 코어: {', '.join(failed_procs)}"],
                is_pass=0,
            )

        return cls._build_result(
            check_target="CPU 장치 상태",
            criteria_text=f"상태 '{expected_status}'",
            judgement_text="정상",
            detail_lines=[f"전체 {total_procs}개 CPU 코어가 정상 상태입니다."],
            is_pass=1,
        )

    @classmethod
    def _run_ioscan_disk(cls, params, stdout_data):
        text = stdout_data or ""
        criteria = params.get("inspection_criteria")

        if not isinstance(criteria, list):
            return cls._build_failure("inspection_criteria 형식이 list가 아닙니다.")

        abnormal_states = [str(item).upper() for item in criteria]

        if "not found" in text.lower():
            return cls._build_failure(
                f"명령어 실패: 'command not found' (출력값: {text.strip()[:200]}...)"
            )

        if not text or "Class" not in text:
            return cls._build_failure(
                f"ioscan 결과에서 필수 헤더 'Class'를 찾을 수 없습니다. (출력값: {text.strip()[:200]}...)"
            )

        data_started = False
        disk_found_count = 0
        issue_lines = []

        for raw_line in text.splitlines():
            line = raw_line.strip()

            if not data_started and line.startswith("========="):
                data_started = True
                continue

            if not data_started or not line:
                continue

            disk_match = re.match(r"disk\s+\d", line)
            if not disk_match:
                continue

            disk_found_count += 1

            if "CLAIMED" not in line:
                issue_lines.append(f"{disk_match.group(0)} 상태가 CLAIMED가 아닙니다: {line}")

            upper_line = line.upper()
            for abnormal_state in abnormal_states:
                if abnormal_state in upper_line:
                    issue_lines.append(f"{disk_match.group(0)} 비정상 상태 '{abnormal_state}' 검출: {line}")
                    break

        if disk_found_count == 0:
            issue_lines.append("'disk' 클래스 항목이 존재하지 않습니다.")

        criteria_items = ["모든 disk 항목 CLAIMED"] + [f"비정상 상태 미검출: {item}" for item in abnormal_states]

        if issue_lines:
            return cls._build_result(
                check_target="디스크 장치 상태",
                criteria_text=criteria_items,
                judgement_text="점검 필요",
                detail_lines=issue_lines,
                is_pass=0,
            )

        return cls._build_result(
            check_target="디스크 장치 상태",
            criteria_text=criteria_items,
            judgement_text="정상",
            detail_lines=[f"disk 항목 {disk_found_count}개 모두 정상입니다."],
            is_pass=1,
        )

    @classmethod
    def _run_lsblk_disk(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        source_name = "/proc/partitions" if "/proc/partitions" in command else "lsblk"
        text = (stdout_data or "").strip()
        if not text:
            return cls._build_result(
                check_target="디스크 장치 상태",
                criteria_text=f"{source_name} 출력 존재",
                judgement_text="점검 필요",
                detail_lines=[f"{source_name} 명령어 출력이 없습니다."],
                is_pass=0,
            )

        if source_name == "/proc/partitions":
            disk_names = cls._parse_proc_partition_names(text)
            if not disk_names:
                return cls._build_result(
                    check_target="디스크 장치 상태",
                    criteria_text="/proc/partitions 출력 존재",
                    judgement_text="점검 필요",
                    detail_lines=["/proc/partitions 결과에서 디스크 정보를 찾을 수 없습니다."],
                    is_pass=0,
                )

            return cls._build_result(
                check_target="디스크 장치 상태",
                criteria_text="/proc/partitions 출력 존재",
                judgement_text="정상",
                detail_lines=[f"디스크 장치 {len(disk_names)}개 확인: {', '.join(disk_names)}"],
                is_pass=1,
            )

        return cls._build_result(
            check_target="디스크 장치 상태",
            criteria_text="lsblk 출력 존재",
            judgement_text="정상",
            detail_lines=["lsblk 명령어 출력이 확인되었습니다."],
            is_pass=1,
        )

    @staticmethod
    def _parse_proc_partition_names(text):
        names = []
        for raw_line in (text or "").splitlines():
            parts = raw_line.split()
            if len(parts) != 4:
                continue
            if parts[0].lower() == "major" or not parts[2].isdigit():
                continue

            name = parts[3]
            if re.match(r"^(sd[a-z]+|hd[a-z]+|vd[a-z]+|xvd[a-z]+|nvme\d+n\d+|dm-\d+)$", name):
                names.append(name)

        return names

    @classmethod
    def _run_solaris_format_disk(cls, params, stdout_data):
        text = stdout_data or ""
        criteria = cls._normalize_text(params.get("inspection_criteria"))
        if not criteria:
            return cls._build_failure("format 점검 기준이 비어 있습니다.")

        header_marker = "available disk selections:"
        lower_text = text.lower()
        header_index = lower_text.find(header_marker)
        if header_index == -1:
            return cls._build_failure("format 출력에서 'AVAILABLE DISK SELECTIONS:' 구간을 찾을 수 없습니다.")

        token_list = [token.strip().lower() for token in criteria.split(",") if token.strip()]
        disk_section = text[header_index + len(header_marker):].strip()
        disk_blocks = [
            block.strip()
            for block in re.split(r"\n\s*(?=\d+\.)", disk_section)
            if block.strip()
        ]
        if not disk_blocks:
            return cls._build_failure("format 출력에서 점검 가능한 디스크 블록을 찾을 수 없습니다.")

        detail_lines = []
        failed_lines = []
        for block in disk_blocks:
            first_line = block.splitlines()[0].strip()
            detail_lines.append(first_line)
            block_lower = block.lower()
            for token in token_list:
                if token in block_lower:
                    failed_lines.append(f"비정상 토큰 '{token}' 검출: {first_line}")
                    break

        return cls._build_result(
            check_target="디스크 장치 상태",
            criteria_text=[f"비정상 토큰 미검출: {token}" for token in token_list],
            judgement_text="점검 필요" if failed_lines else "정상",
            detail_lines=detail_lines + failed_lines if failed_lines else detail_lines,
            is_pass=0 if failed_lines else 1,
        )

    @classmethod
    def _run_get_disk_windows(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        blocked_statuses = cls._parse_status_criteria(criteria)
        if not blocked_statuses:
            return cls._build_failure("inspection_criteria가 비어 있어 상태 비교를 수행할 수 없습니다.")

        rows = cls._parse_windows_value_blocks(stdout_data)
        if not rows:
            return cls._build_failure("Get-Disk 결과에서 유효한 디스크 key=value 데이터를 찾을 수 없습니다.")

        blocked_lower = [status.lower() for status in blocked_statuses]
        detail_lines = []
        failed_lines = []

        for row in rows:
            disk_number = cls._normalize_text(row.get("Number")) or "-"
            disk_name = cls._normalize_text(row.get("FriendlyName")) or "-"
            status_text = cls._normalize_operational_status(row.get("OperationalStatus"))
            health_text = cls._normalize_text(row.get("HealthStatus")) or "-"
            bus_type = cls._normalize_text(row.get("BusType")) or "-"
            partition_style = cls._normalize_text(row.get("PartitionStyle")) or "-"
            size_text = cls._format_disk_size(row.get("Size"))
            detail_lines.append(
                " / ".join(
                    [
                        f"Disk {disk_number}",
                        f"이름: {disk_name}",
                        f"상태: {status_text or '-'}",
                        f"Health: {health_text}",
                        f"Bus: {bus_type}",
                        f"파티션: {partition_style}",
                        f"크기: {size_text}",
                    ]
                )
            )

            if status_text and status_text.lower() in blocked_lower:
                failed_lines.append(
                    f"Disk {disk_number} ({disk_name}) 상태가 금지 상태 '{status_text}' 입니다."
                )

        criteria_items = [f"비정상 상태 미검출: {status}" for status in blocked_statuses]
        if failed_lines:
            return cls._build_result(
                check_target="디스크 장치 상태",
                criteria_text=criteria_items,
                judgement_text="점검 필요",
                detail_lines=failed_lines,
                is_pass=0,
            )

        return cls._build_result(
            check_target="디스크 장치 상태",
            criteria_text=criteria_items,
            judgement_text="정상",
            detail_lines=detail_lines,
            is_pass=1,
        )

    @staticmethod
    def _parse_status_criteria(criteria):
        if isinstance(criteria, list):
            return [str(item).strip() for item in criteria if str(item).strip()]
        if isinstance(criteria, str):
            return [token.strip() for token in criteria.split(",") if token.strip()]
        return []

    @staticmethod
    def _parse_windows_value_blocks(stdout_data):
        items = []
        current_item = {}

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped:
                if current_item:
                    items.append(current_item)
                    current_item = {}
                continue

            if "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()

            if key in current_item and current_item:
                items.append(current_item)
                current_item = {}

            current_item[key] = value

        if current_item:
            items.append(current_item)

        return items

    @staticmethod
    def _normalize_operational_status(status_value):
        if isinstance(status_value, list):
            for item in status_value:
                item_text = str(item).strip()
                if item_text:
                    return item_text
            return ""
        return str(status_value).strip() if status_value is not None else ""

    @staticmethod
    def _format_disk_size(size_value):
        try:
            size_int = int(size_value)
        except (TypeError, ValueError):
            return "-"

        if size_int <= 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB", "PB"]
        size = float(size_int)
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1

        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.1f} {units[unit_index]}"

RULE_KEY = DevStatRule.RULE_KEY
RULE_CLASS = DevStatRule
