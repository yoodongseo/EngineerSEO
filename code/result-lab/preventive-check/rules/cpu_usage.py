from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class CpuUsageRule:
    RULE_KEY = "cpu_usage"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        criteria = params.get("inspection_criteria")
        if isinstance(criteria, dict):
            if "max_user_sys_pct" in criteria:
                return (
                    f"User+Privileged {float(criteria.get('max_user_sys_pct', 0)):.1f}% 이하 / "
                    f"Idle {float(criteria.get('min_idle_pct', 0)):.1f}% 이상 / "
                    f"Interrupt {float(criteria.get('max_irq_pct', 0)):.1f}% 이하"
                )
            if "process" in criteria and "total" in criteria:
                return (
                    f"개별 프로세스 CPU 사용률 {float(criteria.get('process', 0)):.1f}% 이하 / "
                    f"시스템 전체 CPU 사용률 {float(criteria.get('total', 0)):.1f}% 이하"
                )
        try:
            return f"시스템 전체 CPU 사용률 {float(criteria):.1f}% 이하"
        except Exception:
            return "시스템 전체 CPU 사용률 기준 이내"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip()

        if "top" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_top_cpu(params, stdout_data)
            return build_unsupported_command(params)

        if "vmstat" in command:
            if os_type in ("Linux", "Linux5"):
                return cls._run_vmstat_linux(params, stdout_data)
            if os_type == "Aix":
                return cls._run_vmstat_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "sar" in command:
            if os_type == "Hpux":
                return cls._run_sar_hpux(params, stdout_data)
            return build_unsupported_command(params)

        if "prstat" in command:
            if os_type == "Solaris":
                return cls._run_prstat_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "get-counter" in command:
            if os_type == "Windows":
                return cls._run_get_counter_windows(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _run_top_cpu(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"CPU 기준값이 숫자가 아닙니다: {criteria}",
            }

        cpu_line = None
        for line in (stdout_data or "").splitlines():
            if "Cpu(s):" in line or "CPU:" in line:
                cpu_line = line.strip()
                break

        if not cpu_line:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "top 결과에서 CPU 사용률 라인을 찾을 수 없습니다.",
            }

        usage = 0.0
        for part in cpu_line.split(","):
            token = part.strip()
            if not token:
                continue

            value = cls._extract_first_number(token)
            if value is None:
                continue

            if " us" in token or token.endswith("us") or " sy" in token or token.endswith("sy"):
                usage += value

        return cls._build_total_usage_result(usage, criteria_value)

    @staticmethod
    def _extract_first_number(text):
        number = []
        dot_seen = False
        started = False

        for ch in text:
            if ch.isdigit():
                number.append(ch)
                started = True
                continue

            if ch == "." and not dot_seen:
                number.append(ch)
                dot_seen = True
                started = True
                continue

            if started:
                break

        if not number or number == ["."]:
            return None

        try:
            return float("".join(number))
        except Exception:
            return None

    @staticmethod
    def _is_number(text):
        try:
            float(text)
            return True
        except Exception:
            return False

    @classmethod
    def _build_total_usage_result(cls, usage, criteria_value):
        is_pass = 1 if usage <= criteria_value else 0

        return {
            "is_success": 1,
            "is_pass": is_pass,
            "check_target": "CPU 사용률",
            "criteria_items": [f"시스템 전체 {criteria_value:.1f}% 이하"],
            "judgement_text": "기준 이내" if is_pass == 1 else "기준 초과",
            "detail_lines": [f"시스템 전체 CPU 사용률 {usage:.1f}%"],
        }

    @classmethod
    def _run_vmstat_linux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"CPU 기준값이 숫자가 아닙니다: {criteria}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        
        id_index = -1
        data_parts = None

        for i, line in enumerate(lines):
            parts = line.split()
            
            if "us" in parts and "sy" in parts and "id" in parts and "wa" in parts:
                id_index = parts.index("id")
                
                if i + 1 < len(lines):
                    next_line_parts = lines[i + 1].split()
                    
                    if len(parts) == len(next_line_parts):
                        data_parts = next_line_parts
                break

        if id_index == -1 or not data_parts:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 결과에서 CPU 데이터 라인을 찾을 수 없습니다.",
            }

        try:
            idle_value = float(data_parts[id_index])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 결과에서 CPU 유휴율(id) 값을 찾을 수 없습니다.",
            }

        usage = 100.0 - idle_value
        return cls._build_total_usage_result(usage, criteria_value)

    @classmethod
    def _run_vmstat_aix(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"CPU 기준값이 숫자가 아닙니다: {criteria}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        data_parts = None

        for line in reversed(lines):
            parts = line.split()
            if len(parts) >= 17:
                data_parts = parts
                break

        if not data_parts:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 결과에서 AIX CPU 데이터 라인을 찾을 수 없습니다.",
            }

        try:
            idle_value = float(data_parts[-2])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "vmstat 결과에서 AIX CPU 유휴율(id) 값을 찾을 수 없습니다.",
            }

        usage = 100.0 - idle_value
        return cls._build_total_usage_result(usage, criteria_value)

    @classmethod
    def _run_sar_hpux(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        try:
            criteria_value = float(criteria)
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"CPU 기준값이 숫자가 아닙니다: {criteria}",
            }

        lines = [line.strip() for line in (stdout_data or "").splitlines() if line.strip()]
        data_parts = None

        for line in reversed(lines):
            parts = line.split()

            if len(parts) < 5:
                continue

            if parts[0].lower().startswith("average"):
                continue

            if all(cls._is_number(part) for part in parts[-4:]):
                data_parts = parts
                break

        if not data_parts:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "sar 결과에서 CPU 데이터 라인을 찾을 수 없습니다.",
            }

        try:
            idle_value = float(data_parts[-1])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "sar 결과에서 CPU 유휴율(%idle) 값을 찾을 수 없습니다.",
            }

        usage = 100.0 - idle_value
        return cls._build_total_usage_result(usage, criteria_value)

    @classmethod
    def _run_prstat_solaris(cls, params, stdout_data):
        criteria = params.get("inspection_criteria")

        if not isinstance(criteria, dict):
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "CPU 기준값은 process, total 키를 가진 dict 형식이어야 합니다.",
            }

        if "process" not in criteria or "total" not in criteria:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "CPU 기준값에 process 또는 total 항목이 없습니다.",
            }

        try:
            process_threshold = float(criteria["process"])
            total_threshold = float(criteria["total"])
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "CPU 기준값(process/total)이 숫자가 아닙니다.",
            }

        lines = [line.rstrip() for line in (stdout_data or "").splitlines() if line.strip()]
        header_index = -1
        cpu_col_index = -1

        for index, line in enumerate(lines):
            if "PID" in line and "PROCESS/NLWP" in line:
                header_parts = line.split()

                if "CPU" in header_parts:
                    cpu_col_index = header_parts.index("CPU")
                    header_index = index
                    break

                if "%CPU" in header_parts:
                    cpu_col_index = header_parts.index("%CPU")
                    header_index = index
                    break

        if header_index == -1 or cpu_col_index == -1:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "prstat 결과에서 CPU 헤더를 찾을 수 없습니다.",
            }

        total_cpu_usage = 0.0
        max_process_usage = 0.0
        failed_process_lines = []

        for line in lines[header_index + 1:]:
            parts = line.split()

            if not parts:
                continue

            if parts[0].startswith("Total:"):
                continue

            if not parts[0].isdigit():
                continue

            if len(parts) <= cpu_col_index:
                continue

            try:
                cpu_value = float(parts[cpu_col_index].replace("%", ""))
            except Exception:
                continue

            total_cpu_usage += cpu_value
            if cpu_value > max_process_usage:
                max_process_usage = cpu_value

            if cpu_value > process_threshold:
                pid = parts[0]
                user = parts[1] if len(parts) > 1 else "-"
                process_name = parts[-1]
                failed_process_lines.append(
                    f"프로세스 {process_name} (PID:{pid}, USER:{user}) CPU 사용률 {cpu_value:.1f}%"
                )

        criteria_items = [
            f"개별 프로세스 {process_threshold:.1f}% 이하",
            f"시스템 전체 {total_threshold:.1f}% 이하",
        ]
        observed_lines = [
            f"개별 프로세스 최대 CPU 사용률 {max_process_usage:.1f}%",
            f"시스템 전체 CPU 사용률 {total_cpu_usage:.1f}%",
        ]

        if failed_process_lines or total_cpu_usage > total_threshold:
            detail_lines = list(observed_lines)

            if failed_process_lines:
                detail_lines.extend(failed_process_lines)

            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "CPU 사용률",
                "criteria_items": criteria_items,
                "judgement_text": "기준 초과",
                "detail_lines": detail_lines,
            }

        return {
            "is_success": 1,
            "is_pass": 1,
            "check_target": "CPU 사용률",
            "criteria_items": criteria_items,
            "judgement_text": "기준 이내",
            "detail_lines": observed_lines,
        }

    @classmethod
    def _run_get_counter_windows(cls, params, stdout_data):
        criteria = params.get("inspection_criteria") or {}

        try:
            max_user_sys = float(criteria.get("max_user_sys_pct", 80))
            min_idle = float(criteria.get("min_idle_pct", 20))
            max_irq = float(criteria.get("max_irq_pct", 5))
        except Exception:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Windows CPU 기준값(inspection_criteria)이 숫자가 아닙니다.",
            }

        values = cls._parse_get_counter_values(stdout_data)
        if not values:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-Counter 결과를 파싱하지 못했습니다.",
            }

        user = values.get("user")
        privileged = values.get("privileged")
        idle = values.get("idle")
        interrupt = values.get("interrupt")

        if user is None or privileged is None or idle is None:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "Get-Counter 결과에서 필수 CPU 카운터 값을 찾을 수 없습니다.",
            }

        user_sys = round(user + privileged, 2)

        criteria_items = [
            f"User+Privileged {max_user_sys:.1f}% 이하",
            f"Idle {min_idle:.1f}% 이상",
            f"Interrupt {max_irq:.1f}% 이하",
        ]
        detail_lines = [
            f"User+Privileged {user_sys:.2f}%",
            f"Idle {idle:.2f}%",
        ]

        if interrupt is not None:
            detail_lines.append(f"Interrupt {interrupt:.2f}%")

        failed_lines = []
        if user_sys > max_user_sys:
            failed_lines.append(
                f"User+Privileged {user_sys:.2f}%가 기준 {max_user_sys:.1f}%를 초과했습니다."
            )
        if idle < min_idle:
            failed_lines.append(
                f"Idle {idle:.2f}%가 기준 {min_idle:.1f}% 미만입니다."
            )
        if interrupt is not None and interrupt > max_irq:
            failed_lines.append(
                f"Interrupt {interrupt:.2f}%가 기준 {max_irq:.1f}%를 초과했습니다."
            )

        if failed_lines:
            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "CPU 사용률",
                "criteria_items": criteria_items,
                "judgement_text": "기준 초과",
                "detail_lines": detail_lines + failed_lines,
            }

        return {
            "is_success": 1,
            "is_pass": 1,
            "check_target": "CPU 사용률",
            "criteria_items": criteria_items,
            "judgement_text": "기준 이내",
            "detail_lines": detail_lines,
        }

    @staticmethod
    def _parse_get_counter_values(stdout_data):
        values = {}

        for line in (stdout_data or "").splitlines():
            stripped = line.strip()
            if not stripped or "=" not in stripped:
                continue

            key, value = stripped.split("=", 1)
            key_text = key.strip().lower()

            try:
                number = float(value.strip())
            except Exception:
                continue

            if key_text == "user":
                values["user"] = number
            elif key_text == "privileged":
                values["privileged"] = number
            elif key_text == "idle":
                values["idle"] = number
            elif key_text == "interrupt":
                values["interrupt"] = number

        return values

RULE_KEY = CpuUsageRule.RULE_KEY
RULE_CLASS = CpuUsageRule
