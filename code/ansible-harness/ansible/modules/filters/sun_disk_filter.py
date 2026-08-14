from .base_filter import BaseFilter, filter_result
import re

class SunDiskFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _detect_command_error(self, stdout_data):
        output = (stdout_data or "").strip()
        output_lower = output.lower()
        patterns = [
            "illegal option",
            "invalid option",
            "unknown option",
            "usage:",
            "not found",
            "명령을 찾을 수 없습니다",
            "찾을 수 없습니다",
            "cannot",
        ]
        for pattern in patterns:
            if pattern in output_lower:
                return output
        return None

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if self.command.strip().startswith("df"):
            is_success, is_pass, result, message = self.sun_df_type1(stdout_data)
        elif "metastat" in self.command:
            is_success, is_pass, result, message = self.sun_metastat_type1(stdout_data)
        elif "format" in self.command:
            is_success, is_pass, result, message = self.sun_format_type1(stdout_data)
        elif "iostat" in self.command:
            is_success, is_pass, result, message = self.sun_iostat_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def sun_df_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            try:
                criteria = float(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = f"❌ 점검 필요: 점검 기준값(inspection_criteria)이 올바른 숫자가 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            if len(lines) < 2:
                is_pass = 0
                message = f"❌ 점검 필요: '{self.command}' 출력 내용을 분석할 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            header_line = lines[0].lower()
            header_parts = header_line.split()

            capacity_idx = -1
            filesystem_idx = 0

            if 'capacity' in header_parts:
                capacity_idx = header_parts.index('capacity')
            elif '용량' in header_parts:
                capacity_idx = header_parts.index('용량')
            else:
                is_pass = 0
                message = "❌ 점검 필요: 'Capacity' 또는 '용량' 헤더를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_disks = []
            for line in lines[1:]:
                parts = line.split()
                if not parts or len(parts) <= capacity_idx:
                    continue

                filesystem = parts[filesystem_idx]
                mount_point = parts[-1]
                capacity_str = parts[capacity_idx]

                if capacity_str.endswith('%'):
                    try:
                        usage_percent = int(capacity_str[:-1])
                        if usage_percent >= criteria:
                            failed_disks.append(f" - {filesystem} ({mount_point}) (사용률: {usage_percent}%)")
                    except ValueError:
                        continue

            if failed_disks:
                is_pass = 0
                fail_list_str = "\n".join(failed_disks)
                message = f"❌ 점검 필요: 다음 파일시스템의 사용률이 기준({criteria}%) 이상입니다:\n{fail_list_str}"
            else:
                is_pass = 1
                message = f"✅ 정상: 모든 파일시스템의 사용률이 기준({criteria}%) 미만입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Solaris 디스크 사용량 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def sun_metastat_type1(self, stdout_data):
        try:
            is_success = 1
    
            # 설정 변수#
            NO_DB_KEYWORDS = ["there are no existing databases", "기존 데이터베이스 없음"]
            STATE_KEYWORDS = ['state:', '상태:']
            OK_STATUESE = ['okay', '정상']
            BLOCK_SPLIT_REGEX = r'\n(?=\w+:\s)'
    
            if any(keyword in stdout_data for keyword in NO_DB_KEYWORDS):
                is_pass = 1
                message = "✅ 정상: 확인 가능한 RAID 이중화 구성이 없습니다."
                result = message
                return is_success, is_pass, result, message
    
            blocks = re.split(BLOCK_SPLIT_REGEX, stdout_data)
            failed_devices = []
    
            for block in blocks:
                if not block.strip():
                    continue
    
                lines = block.strip().splitlines()
                device_name = lines[0].split(':')[0].strip()
    
                state_line = None
                for line in lines:
                    stripped_line = line.strip()
                    if any(stripped_line.lower().startswith(kw) for kw in STATE_KEYWORDS):
                        state_line = stripped_line
                        break
    
                if state_line:
                    state_value = state_line.split(':', 1)[1].strip()
    
                    if state_value.lower() not in OK_STATUESE:
                        failed_devices.append(f" - {device_name} (상태: {state_value})")
    
            if failed_devices:
                is_pass = 0
                fail_list_str = "\n".join(failed_devices)
                message = f"❌ 점검 필요: 다음 디바이스의 상태가 정상이 아닙니다:\n{fail_list_str}"
            else:
                is_pass = 1
                message = "✅ 정상: 모든 미러(RAID) 디바이스의 상태가 정상입니다."
    
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Solaris metastat 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def sun_format_type1(self, stdout_data):
        try:
            is_success = 1

            if not isinstance(self.inspection_criteria, str) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ 점검 필요: 점검 기준값(inspection_criteria)이 올바른 문자열 형식이 아닙니다."
                result = message
                return is_success, is_pass, result, message

            failure_conditions = [item.strip().lower() for item in self.inspection_criteria.split(',')]

            try:
                start_index = stdout_data.upper().index("AVAILABLE DISK SELECTIONS:")
                disk_section_text = stdout_data[start_index:]
            except ValueError:
                is_pass = 0
                message = "❌ 점검 필요: 출력에서 'AVAILABLE DISK SELECTIONS:'를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            disk_blocks = re.split(r'\n\s*(?=\d+\.)', disk_section_text)
            failed_disks = []

            for block in disk_blocks[1:]:
                block_lower = block.lower()
                for condition in failure_conditions:
                    if condition in block_lower:
                        failed_disks.append(block.strip())

            if failed_disks:
                is_pass = 0
                fail_list_str = "\n".join([f" - {disk}" for disk in failed_disks])
                message = f"❌ 점검 필요: 다음 디스크에서 '{', '.join(failure_conditions)}' 상태가 발견되었습니다:\n{fail_list_str}"
            else:
                is_pass = 1
                message = "✅ 정상: 모든 디스크가 정상적으로 인식되었습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Solaris format 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def sun_iostat_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ 점검 필요: 점검 기준값(inspection_criteria)이 올바른 형식이 아닙니다."
                result = message
                return is_success, is_pass, result, message

            svc_t_max = float(self.inspection_criteria.get("svc_t_max", 20))
            busy_max = float(self.inspection_criteria.get("busy_max", 80))
            wait_max = float(self.inspection_criteria.get("wait_max", 0))

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌명령어 출력이 비어있습니다."
                result = message
                return is_success, is_pass, result, message
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "extended" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'extended' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = [l.strip() for l in stdout_data.splitlines() if l.strip()]

            data_started = False
            checked = 0

            for line in lines:
                if line.lower().startswith("device"):
                    data_started = True
                    continue

                if not data_started:
                    continue

                parts = line.split()
                if len(parts) < 10:
                    continue

                try:
                    device = parts[0]
                    wait = float(parts[5])
                    svc_t = float(parts[7])
                    busy = float(parts[9])
                except ValueError:
                    continue

                checked += 1

                if wait > wait_max:
                    is_pass = 0
                    message_list.append(f"❌ {device}: wait={wait}")

                if svc_t >= svc_t_max:
                    is_pass = 0
                    message_list.append(f"❌ {device}: svc_t={svc_t}ms (기준: < {svc_t_max}ms)")
                if busy >= busy_max:
                    is_pass = 0
                    message_list.append(f"❌ {device}: %b={busy}% (기준: < {busy_max}%)")

            if checked == 0:
                is_success = 0
                is_pass = 0
                message = f"❌ iostat 데이터 라인을 찾지 못했습니다. (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if is_pass == 1:
                message = f"✅ Disk I/O 정상: {checked} 개 디스크 모두 임계치 미만"
            else:
                message = "\n".join(message_list)

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Solaris iostat 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
