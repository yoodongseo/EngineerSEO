import re
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class DiskStatRule:
    RULE_KEY = "disk_stat"
    SOLARIS_IOSTAT_ERROR_PATTERNS = [
        "illegal option",
        "invalid option",
        "unknown option",
        "usage:",
        "not found",
        "명령을 찾을 수 없습니다",
        "찾을 수 없습니다",
        "cannot",
    ]

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        return "Disk I/O 지연 및 오류 없음"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip().lower()

        if "vmstat" in command or command.startswith("cat"):
            if os_type in ("linux", "linux5"):                
                return cls._run_vmstat(params, stdout_data)
            return build_unsupported_command(params)

        if "sar -d" in command:
            if os_type == "hpux":                
                return cls._run_sar_disk(params, stdout_data)
            return build_unsupported_command(params)

        if "iostat -d" in command:
            if os_type == "aix":                
                return cls._run_aix_iostat(params, stdout_data)
            return build_unsupported_command(params)

        if "iostat" in command:
            if os_type == "solaris":
                return cls._run_solaris_iostat(params, stdout_data)            

            if "iostat -x" in command:
                if os_type in ("linux", "linux5"):                    
                    return cls._run_linux_iostat(params, stdout_data)
                return build_unsupported_command(params)

            return build_unsupported_command(params)

        if "get-counter" in command:
            if os_type == "windows":                
                return cls._run_windows_get_counter_latency(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _run_windows_get_counter_latency(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        try:
            threshold = float(criteria)
        except (TypeError, ValueError):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"디스크 Latency 기준값이 숫자가 아닙니다: {criteria}",
            }

        text = (stdout_data or "").strip()
        if not text:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-Counter 출력이 비어 있습니다.",
            }

        read_match = re.search(r"Read\s+Latency\s+([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        write_match = re.search(r"Write\s+Latency\s+([0-9]+(?:\.[0-9]+)?)", text, re.IGNORECASE)
        if not read_match or not write_match:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-Counter 출력에서 Read/Write Latency 값을 찾을 수 없습니다.",
            }

        read_latency = float(read_match.group(1))
        write_latency = float(write_match.group(1))

        detail_lines = [
            f"Read Latency {read_latency:.3f}ms",
            f"Write Latency {write_latency:.3f}ms",
        ]
        failed_lines = []
        if read_latency > threshold:
            failed_lines.append(
                f"Read Latency가 임계값을 초과했습니다: {read_latency:.3f}ms (기준: {threshold:.3f}ms)"
            )
        if write_latency > threshold:
            failed_lines.append(
                f"Write Latency가 임계값을 초과했습니다: {write_latency:.3f}ms (기준: {threshold:.3f}ms)"
            )

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "디스크 I/O Latency",
            "criteria_items": [
                f"Read Latency {threshold:.1f}ms 이하",
                f"Write Latency {threshold:.1f}ms 이하",
            ],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @classmethod
    def _run_vmstat(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "inspection_criteria가 딕셔너리 형식이 아닙니다.",
            }

        missing_keys = []
        if "b" not in criteria:
            missing_keys.append("'b' 키")
        if "wa" not in criteria:
            missing_keys.append("'wa' 키")
        if missing_keys:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"inspection_criteria에 다음 키가 선언되지 않았습니다: {', '.join(missing_keys)}",
            }

        try:
            b_threshold = int(criteria["b"])
            wa_threshold = int(criteria["wa"])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "inspection_criteria의 b/wa 기준값이 정수가 아닙니다.",
            }

        header_tokens = []
        data_tokens = []
        
        lines = (stdout_data or "").strip().splitlines()
        for raw_line in lines:
            line = raw_line.strip()
            if not line or "---" in line or "procs" in line or "system" in line:
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            # 모든 토큰이 문자로만 이루어져 있으면 헤더
            is_alpha = all(p.isalpha() for p in parts)
            # 숫자로만 이루어져 있으면 데이터 (음수, 공백 처리 포함)
            is_digit = all(p.lstrip('-').isdigit() for p in parts)
            
            if is_alpha:
                header_tokens.extend(parts)
            elif is_digit:
                data_tokens.extend(parts)
                # 헤더 개수만큼 데이터를 수집했으면 (첫 번째 출력 단위 완료) 중단
                if len(header_tokens) > 0 and len(data_tokens) >= len(header_tokens):
                    break

        if not header_tokens or not data_tokens:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 출력에서 유효한 헤더 또는 데이터 라인을 찾을 수 없습니다.",
            }

        if "b" not in header_tokens or "wa" not in header_tokens:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 출력 헤더에서 'b' 또는 'wa' 컬럼을 찾을 수 없습니다.",
            }

        b_col_idx = header_tokens.index("b")
        wa_col_idx = header_tokens.index("wa")
        bi_col_idx = header_tokens.index("bi") if "bi" in header_tokens else -1
        bo_col_idx = header_tokens.index("bo") if "bo" in header_tokens else -1

        try:
            b_value = int(data_tokens[b_col_idx])
            wa_value = int(data_tokens[wa_col_idx])
            bi_value = int(data_tokens[bi_col_idx]) if bi_col_idx >= 0 else None
            bo_value = int(data_tokens[bo_col_idx]) if bo_col_idx >= 0 else None
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"vmstat 데이터 라인 파싱 중 오류 발생: {' '.join(data_tokens)}",
            }

        criteria_items = [
            f"Blocked Processes(b, procs) {b_threshold} 이하",
            f"IO Wait(wa, cpu) {wa_threshold}% 이하",
        ]
        detail_lines = [
            f"Blocked Processes(b, procs) {b_value}",
            f"IO Wait(wa, cpu) {wa_value}%",
        ]
        if bi_value is not None:
            detail_lines.append(f"Block In(bi, io) {bi_value}")
        if bo_value is not None:
            detail_lines.append(f"Block Out(bo, io) {bo_value}")

        failed_messages = []
        if b_value > b_threshold:
            failed_messages.append(
                f"Blocked Processes(b, procs)가 임계값을 초과했습니다: {b_value} (기준: {b_threshold})"
            )
        if wa_value > wa_threshold:
            failed_messages.append(
                f"IO Wait(wa, cpu)가 임계값을 초과했습니다: {wa_value}% (기준: {wa_threshold}%)"
            )

        if failed_messages:
            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "디스크 I/O",
                "criteria_items": criteria_items,
                "judgement_text": "기준 초과",
                "detail_lines": detail_lines + failed_messages,
            }

        return {
            "is_success": 1,
            "is_pass": 1,
            "check_target": "디스크 I/O",
            "criteria_items": criteria_items,
            "judgement_text": "기준 이내",
            "detail_lines": detail_lines,
        }

    @classmethod
    def _run_sar_disk(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            threshold = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"디스크 I/O 기준값이 숫자가 아닙니다: {criteria}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        data_started = False
        detail_lines = []
        failed_lines = []

        for line in lines:
            if not data_started and "device" in line.lower():
                data_started = True
                continue

            if not data_started or line.lower().startswith("average"):
                continue

            parts = line.split()
            if len(parts) < 7:
                continue

            try:
                device_name = parts[1]
                avwait = float(parts[6])
            except Exception:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"sar -d 출력 파싱 중 오류 발생: {line}",
                }

            detail_lines.append(f"디스크 {device_name} avwait {avwait}ms")
            if avwait >= threshold:
                failed_lines.append(f"디스크 '{device_name}' 의 avwait 값 {avwait}ms (기준: {threshold}ms) 기준값 초과")

        if not data_started or not detail_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "sar -d 출력에서 유효한 디스크 데이터를 찾을 수 없습니다.",
            }

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "디스크 I/O",
            "criteria_items": [f"avwait {threshold:.1f}ms 미만"],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @classmethod
    def _run_aix_iostat(cls, params, stdout_data):
        parsed_criteria = cls._parse_threshold_dict(
            params.get("inspection_criteria"),
            {
                "tm_act": float,
                "timeouts": int,
                "fails": int,
                "avgserv": float,
                "maxserv": float,
                "sqfull": float,
            },
            "iostat -D 기준값",
        )
        if isinstance(parsed_criteria, dict) and "is_success" in parsed_criteria:
            return parsed_criteria

        criteria = parsed_criteria
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat -D 기준값은 딕셔너리 형식이어야 합니다.",
            }

        disk_blocks = cls._split_aix_iostat_blocks(stdout_data)
        if not disk_blocks:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat -D 출력에서 디스크 블록을 찾을 수 없습니다.",
            }

        detail_lines = []
        failed_lines = []

        for block in disk_blocks:
            parsed_values = cls._parse_aix_iostat_block(block)
            if not parsed_values:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"iostat -D 블록 파싱에 실패했습니다: {block[0]}",
                }

            disk_name = parsed_values.get("disk_name", "알 수 없는 디스크")
            metric_failures = cls._check_aix_iostat_thresholds(parsed_values, criteria)
            summary_parts = []
            if "tm_act" in parsed_values:
                summary_parts.append(f"%tm_act {parsed_values['tm_act']}")
            if "sqfull" in parsed_values:
                summary_parts.append(f"sqfull {parsed_values['sqfull']}")
            detail_lines.append(f"디스크 {disk_name}: {', '.join(summary_parts) if summary_parts else '측정값 확인'}")

            for failure in metric_failures:
                failed_lines.append(f"{disk_name}: {failure}")

        criteria_items = cls._build_aix_iostat_criteria_items(criteria)
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "디스크 I/O",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @classmethod
    def _run_linux_iostat(cls, params, stdout_data):
        parsed_criteria = cls._parse_threshold_dict(
            params.get("inspection_criteria"),
            {
                "iowait": float,
                "await": float,
                "util": float,
            },
            "iostat -x 기준값",
            defaults={"iowait": 10.0, "await": 20.0, "util": 80.0},
        )
        if isinstance(parsed_criteria, dict) and "is_success" in parsed_criteria:
            return parsed_criteria

        criteria = parsed_criteria
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat -x 기준값은 딕셔너리 형식이어야 합니다.",
            }

        iowait_threshold = criteria["iowait"]
        await_threshold = criteria["await"]
        util_threshold = criteria["util"]

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        cpu_iowait = None
        device_header_index = -1

        for index, line in enumerate(lines):
            if line.startswith("avg-cpu:") and index + 1 < len(lines):
                cpu_headers = line.split()
                cpu_values = lines[index + 1].split()
                if "%iowait" in cpu_headers:
                    header_index = cpu_headers.index("%iowait")
                    offset = len(cpu_headers) - len(cpu_values)
                    value_index = header_index - offset
                    if 0 <= value_index < len(cpu_values):
                        try:
                            cpu_iowait = float(cpu_values[value_index])
                        except (TypeError, ValueError):
                            return {
                                "is_success": 0,
                                "is_pass": 0,
                                "reason_text": f"iostat -x CPU %iowait 파싱 중 오류 발생: {lines[index + 1]}",
                            }
            if line.startswith("Device"):
                device_header_index = index
                break

        if device_header_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat -x 출력에서 Device 헤더를 찾을 수 없습니다.",
            }

        device_headers = lines[device_header_index].split()
        if "await" not in device_headers or "%util" not in device_headers:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat -x 출력에서 await 또는 %util 컬럼을 찾을 수 없습니다.",
            }

        await_index = device_headers.index("await")
        util_index = device_headers.index("%util")
        detail_lines = []
        failed_lines = []

        if cpu_iowait is not None:
            detail_lines.append(f"CPU %iowait {cpu_iowait}%")
            if cpu_iowait > iowait_threshold:
                failed_lines.append(f"CPU %iowait가 임계값을 초과했습니다: {cpu_iowait}% (기준: {iowait_threshold}%)")

        for line in lines[device_header_index + 1:]:
            parts = line.split()
            if len(parts) <= max(await_index, util_index):
                continue

            device_name = parts[0]
            try:
                await_value = float(parts[await_index])
                util_value = float(parts[util_index])
            except Exception:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"iostat -x 장치 데이터 파싱 중 오류 발생: {line}",
                }

            detail_lines.append(f"장치 {device_name} await {await_value}, %util {util_value}%")
            if await_value > await_threshold:
                failed_lines.append(f"장치 '{device_name}' 의 await 시간이 임계값을 초과했습니다: {await_value} (기준: {await_threshold})")
            if util_value >= util_threshold:
                failed_lines.append(f"장치 '{device_name}' 의 %util이 임계값을 초과했습니다: {util_value}% (기준: {util_threshold}%)")

        criteria_items = [
            f"CPU %iowait {iowait_threshold:.1f}% 이하",
            f"장치 await {await_threshold:.1f} 이하",
            f"장치 %util {util_threshold:.1f}% 미만",
        ]
        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "디스크 I/O",
            "criteria_items": criteria_items,
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @classmethod
    def _run_solaris_iostat(cls, params, stdout_data):
        command_error = cls._detect_solaris_iostat_command_error(stdout_data)
        if command_error:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"명령어 실패: {command_error.splitlines()[0]}",
            }

        parsed_criteria = cls._parse_threshold_dict(
            params.get("inspection_criteria"),
            {
                "wait_pct_max": float,
                "busy_max": float,
                "wait_max": float,
            },
            "iostat 기준값",
            defaults={"wait_pct_max": 0.0, "busy_max": 80.0, "wait_max": 0.0},
        )
        if isinstance(parsed_criteria, dict) and "is_success" in parsed_criteria:
            return parsed_criteria

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        if not any("extended" in line.lower() for line in lines):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat 출력에서 extended 헤더를 찾을 수 없습니다.",
            }

        header_index = -1
        for index, line in enumerate(lines):
            if line.lower().startswith("device"):
                header_index = index
                break
        if header_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat 출력에서 Device 헤더를 찾을 수 없습니다.",
            }

        headers = lines[header_index].split()
        normalized = {header.lower(): idx for idx, header in enumerate(headers)}
        required_columns = ["device", "wait", "%w", "%b"]
        if any(column not in normalized for column in required_columns):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat 출력에서 wait/%w/%b 컬럼을 찾을 수 없습니다.",
            }

        detail_lines = []
        failed_lines = []
        for line in lines[header_index + 1:]:
            parts = line.split()
            if len(parts) <= max(normalized["wait"], normalized["%w"], normalized["%b"]):
                continue
            try:
                device = parts[normalized["device"]]
                wait_value = float(parts[normalized["wait"]])
                wait_pct_value = float(parts[normalized["%w"]])
                busy_value = float(parts[normalized["%b"]])
            except (TypeError, ValueError):
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"iostat 장치 데이터 파싱 중 오류 발생: {line}",
                }

            detail_lines.append(
                f"장치 {device} wait {wait_value}, %w {wait_pct_value}, %b {busy_value}"
            )
            if wait_value > parsed_criteria["wait_max"]:
                failed_lines.append(
                    f"장치 '{device}' wait 값 {wait_value} (기준: {parsed_criteria['wait_max']}) 기준 초과"
                )
            if wait_pct_value > parsed_criteria["wait_pct_max"]:
                failed_lines.append(
                    f"장치 '{device}' %w 값 {wait_pct_value} (기준: {parsed_criteria['wait_pct_max']}) 기준 초과"
                )
            if busy_value >= parsed_criteria["busy_max"]:
                failed_lines.append(
                    f"장치 '{device}' %b 값 {busy_value} (기준: {parsed_criteria['busy_max']}) 기준 초과"
                )

        if not detail_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "iostat 출력에서 장치 데이터를 찾을 수 없습니다.",
            }

        return {
            "is_success": 1,
            "is_pass": 0 if failed_lines else 1,
            "check_target": "디스크 I/O",
            "criteria_items": [
                f"wait {parsed_criteria['wait_max']:.1f} 이하",
                f"%w {parsed_criteria['wait_pct_max']:.1f}% 이하",
                f"%b {parsed_criteria['busy_max']:.1f}% 미만",
            ],
            "judgement_text": "기준 초과" if failed_lines else "기준 이내",
            "detail_lines": detail_lines + failed_lines,
        }

    @classmethod
    def _detect_solaris_iostat_command_error(cls, stdout_data):
        output = (stdout_data or "").strip()
        output_lower = output.lower()
        for pattern in cls.SOLARIS_IOSTAT_ERROR_PATTERNS:
            if pattern in output_lower:
                return output
        return None

    @staticmethod
    def _split_aix_iostat_blocks(stdout_data):
        blocks = []
        for block in re.split(r"(?=hdisk\d+\s+xfer:)", stdout_data or ""):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and lines[0].startswith("hdisk") and "xfer:" in lines[0]:
                blocks.append(lines)
        return blocks

    @staticmethod
    def _parse_aix_iostat_block(lines):
        values = {}
        header_map = {}
        disk_name = "알 수 없는 디스크"
        index = 0

        while index < len(lines):
            line = lines[index]

            if "xfer:" in line and line.startswith("hdisk"):
                parts = line.split(None, 2)
                disk_name = parts[0]
                headers = parts[2].split() if len(parts) > 2 else []
                header_map["xfer"] = {name: idx for idx, name in enumerate(headers)}
                if index + 1 < len(lines):
                    data_parts = lines[index + 1].split()
                    if "%tm_act" in header_map["xfer"]:
                        try:
                            values["tm_act"] = float(data_parts[header_map["xfer"]["%tm_act"]])
                        except (IndexError, TypeError, ValueError):
                            return None
                index += 2
                continue

            for section in ["read", "write", "queue"]:
                prefix = f"{section}:"
                if line.startswith(prefix):
                    headers = line[len(prefix):].strip().split()
                    header_map[section] = {name: idx for idx, name in enumerate(headers)}
                    if index + 1 < len(lines):
                        data_parts = lines[index + 1].split()
                        try:
                            if section == "read":
                                if "avgserv" in header_map[section]:
                                    values["read_avgserv"] = float(data_parts[header_map[section]["avgserv"]])
                                if "maxserv" in header_map[section]:
                                    values["read_maxserv"] = float(data_parts[header_map[section]["maxserv"]])
                                if "timeouts" in header_map[section]:
                                    values["read_timeouts"] = int(data_parts[header_map[section]["timeouts"]])
                                if "fails" in header_map[section]:
                                    values["read_fails"] = int(data_parts[header_map[section]["fails"]])
                            elif section == "write":
                                if "avgserv" in header_map[section]:
                                    values["write_avgserv"] = float(data_parts[header_map[section]["avgserv"]])
                                if "maxserv" in header_map[section]:
                                    values["write_maxserv"] = float(data_parts[header_map[section]["maxserv"]])
                                if "timeouts" in header_map[section]:
                                    values["write_timeouts"] = int(data_parts[header_map[section]["timeouts"]])
                                if "fails" in header_map[section]:
                                    values["write_fails"] = int(data_parts[header_map[section]["fails"]])
                            elif section == "queue" and "sqfull" in header_map[section]:
                                values["sqfull"] = float(data_parts[header_map[section]["sqfull"]])
                        except (IndexError, TypeError, ValueError):
                            return None
                    index += 2
                    break
            else:
                index += 1

        values["disk_name"] = disk_name
        return values

    @staticmethod
    def _check_aix_iostat_thresholds(parsed_values, criteria):
        failed_metrics = []

        if parsed_values.get("tm_act", 0) > criteria.get("tm_act", 999.0):
            failed_metrics.append(f"%tm_act ({parsed_values['tm_act']} > {criteria['tm_act']})")
        if parsed_values.get("read_timeouts", 0) > criteria.get("timeouts", 999):
            failed_metrics.append(f"read timeouts ({parsed_values['read_timeouts']} > {criteria['timeouts']})")
        if parsed_values.get("read_fails", 0) > criteria.get("fails", 999):
            failed_metrics.append(f"read fails ({parsed_values['read_fails']} > {criteria['fails']})")
        if parsed_values.get("read_avgserv", 0) > criteria.get("avgserv", 999.0):
            failed_metrics.append(f"read avgserv ({parsed_values['read_avgserv']} > {criteria['avgserv']})")
        if parsed_values.get("read_maxserv", 0) > criteria.get("maxserv", 999.0):
            failed_metrics.append(f"read maxserv ({parsed_values['read_maxserv']} > {criteria['maxserv']})")
        if parsed_values.get("write_timeouts", 0) > criteria.get("timeouts", 999):
            failed_metrics.append(f"write timeouts ({parsed_values['write_timeouts']} > {criteria['timeouts']})")
        if parsed_values.get("write_fails", 0) > criteria.get("fails", 999):
            failed_metrics.append(f"write fails ({parsed_values['write_fails']} > {criteria['fails']})")
        if parsed_values.get("write_avgserv", 0) > criteria.get("avgserv", 999.0):
            failed_metrics.append(f"write avgserv ({parsed_values['write_avgserv']} > {criteria['avgserv']})")
        if parsed_values.get("write_maxserv", 0) > criteria.get("maxserv", 999.0):
            failed_metrics.append(f"write maxserv ({parsed_values['write_maxserv']} > {criteria['maxserv']})")
        if parsed_values.get("sqfull", 0) > criteria.get("sqfull", 999):
            failed_metrics.append(f"queue sqfull ({parsed_values['sqfull']} > {criteria['sqfull']})")

        return failed_metrics

    @staticmethod
    def _build_aix_iostat_criteria_items(criteria):
        items = []
        if "tm_act" in criteria:
            items.append(f"%tm_act {criteria['tm_act']} 이하")
        if "timeouts" in criteria:
            items.append(f"timeouts {criteria['timeouts']} 이하")
        if "fails" in criteria:
            items.append(f"fails {criteria['fails']} 이하")
        if "avgserv" in criteria:
            items.append(f"avgserv {criteria['avgserv']} 이하")
        if "maxserv" in criteria:
            items.append(f"maxserv {criteria['maxserv']} 이하")
        if "sqfull" in criteria:
            items.append(f"sqfull {criteria['sqfull']} 이하")
        return items or ["디스크 I/O 기준 확인"]

    @staticmethod
    def _parse_threshold_dict(criteria, schema, label, defaults=None):
        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"{label}은 딕셔너리 형식이어야 합니다.",
            }

        parsed = {}
        defaults = defaults or {}
        for key, caster in schema.items():
            raw_value = criteria.get(key, defaults.get(key))
            if raw_value is None:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"{label}에 '{key}' 키가 선언되지 않았습니다.",
                }
            try:
                parsed[key] = caster(raw_value)
            except (TypeError, ValueError):
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": f"{label}의 '{key}' 값이 숫자가 아닙니다: {raw_value}",
                }

        return parsed

RULE_KEY = DiskStatRule.RULE_KEY
RULE_CLASS = DiskStatRule
