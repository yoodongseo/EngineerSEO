from .base_filter import BaseFilter, filter_result
import re

class DiskFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _detect_df_command_error(self, stdout_data):
        output = (stdout_data or "").strip()
        output_lower = output.lower()

        error_patterns = [
            "illegal option",
            "invalid option",
            "unknown option",
            "usage:",
            "not found",
            "no such file",
            "cannot",
        ]

        for pattern in error_patterns:
            if pattern in output_lower:
                return output

        return None

    def _detect_iostat_command_error(self, stdout_data):
        output = (stdout_data or "").strip()
        output_lower = output.lower()

        error_patterns = [
            "illegal option",
            "invalid option",
            "unknown option",
            "usage:",
            "not found",
            "명령을 찾을 수 없습니다",
            "찾을 수 없습니다",
            "sysstat",
        ]

        for pattern in error_patterns:
            if pattern in output_lower:
                return output

        return None

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        result = ""

        if "df -h" in self.command:
            is_success, is_pass, result, message = self.df_type1(stdout_data)
        elif "df -g" in self.command:
            is_success, is_pass, result, message = self.df_type2(stdout_data)
        elif "du -sh" in self.command:
            is_success, is_pass, result, message = self.du_type1(stdout_data)
        elif "show system storage" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "stat filesystem" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
        elif "bdf" in self.command:
            is_success, is_pass, result, message = self.bdf_type1(stdout_data)
        elif "sar -d" in self.command:
            is_success, is_pass, result, message = self.sar_disk_type1(stdout_data)
        elif "iostat -D" in self.command:
            is_success, is_pass, result, message = self.aix_iostat_type1(stdout_data)
        elif "iostat -x" in self.command:
            is_success, is_pass, result, message = self.linux_iostat_type1(stdout_data)
        elif "vmstat" in self.command:
            is_success, is_pass, result, message = self.vmstat_type1(stdout_data)
        elif "cat" in self.command:
            is_success, is_pass, result, message = self.vmstat_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def df_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            command_error = self._detect_df_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            results_fail = []
            
            try:
                criteria = float(self.inspection_criteria)
            except Exception:
                criteria = 90.0

            if not lines or "filesystem" not in lines[0].lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 6 and "%" in parts[4]:
                    try:
                        usage_percent = float(parts[4].replace("%", ""))
                        mount_point = parts[5]
                        if usage_percent > criteria:
                            is_pass = 0
                            results_fail.append(f"❌ {mount_point}: {usage_percent:.1f}% (기준 {criteria:.1f}%)")
                    except ValueError:
                        continue

            if not results_fail:
                message = f"✅ 모든 파일 시스템 사용량이 임계값({criteria:.1f}%) 이하입니다."
            else:
                message = "\n".join(results_fail)
            
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def juniper_type1(self, stdout_data):
        try:
            is_success = 1
            
            try:
                threshold = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                is_success = 0
                message = f"❌ 점검 기준(inspection_criteria) '{self.inspection_criteria}'이(가) 유효한 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            failing_filesystems = []
            lines = stdout_data.strip().splitlines()
            
            for line in lines:
                if line.strip().startswith('Filesystem'):
                    continue
                parts = line.split()
                if len(parts) >= 5 and parts[4].endswith('%'):
                    try:
                        capacity = int(parts[4].replace('%', ''))
                        if capacity > threshold:
                            failing_filesystems.append(f"{parts[0]} ({capacity}%)")
                    except (ValueError, IndexError):
                        continue
            
            if failing_filesystems:
                is_pass = 0
                message = f"❌ 다음 파일 시스템의 사용량이 임계값({threshold}%)을 초과했습니다:\n" + '\n'.join(failing_filesystems)
            else:
                is_pass = 1
                message = f"✅ 모든 파일 시스템 사용량이 임계값({threshold}%) 이하입니다."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 디스크 사용량 점검 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def citrix_type1(self, stdout_data):
        """Citrix 'stat filesystem' 출력에서 디스크 사용량을 점검합니다."""
        try:
            is_success = 1
            
            try:
                threshold = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                is_success = 0
                message = f"❌ 점검 기준(inspection_criteria) '{self.inspection_criteria}'이(가) 유효한 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            failing_disks = []
            lines = stdout_data.strip().splitlines()

            for line in lines:
                if "Used (%)" in line:
                    parts = line.split()
                    try:
                        disk_name = parts[0]
                        usage = int(parts[-2])
                        if usage >= threshold:
                            failing_disks.append(f"{disk_name} ({usage}%)")
                    except (ValueError, IndexError):
                        continue
            
            if failing_disks:
                is_pass = 0
                message = f"❌ 다음 디스크의 사용량이 임계값({threshold}%)을 초과했습니다:\n" + "\n".join(failing_disks)
            else:
                is_pass = 1
                message = f"✅ 모든 디스크 사용량이 임계값({threshold}%) 미만입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 디스크 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
    def bdf_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            messages_list = []

            threshold = self.inspection_criteria if isinstance(self.inspection_criteria, (int, float)) else 80
            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or "Filesystem" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            data_started = False
            
            for line in lines:
                stripped_line = line.strip()
                
                if not data_started and stripped_line.startswith("Filesystem"):
                    data_started = True
                    continue

                if not data_started or not stripped_line:
                    continue

                parts = stripped_line.split()
                if len(parts) >= 5:
                    try:
                        used_pct_str = parts[4]
                        if used_pct_str.endswith("%"):
                            used_pct = float(used_pct_str.replace("%",""))
                            filesystem = parts[0]
  
                            if used_pct >= threshold:
                                is_pass = 0
                                messages_list.append(f"❌ 파일시스템 '{filesystem}' 사용률 {used_pct}% (기준: {threshold}%) - 기준값 초과")  
                    except ValueError:
                        messages_list.append(f"❌ 파일시스템 사용률 파싱 오류: {stripped_line}")
                        is_pass = 0
            if not data_started:
                is_pass = 0
                messages_list.insert(0, f"❌ 'bdf' 명령어 줄에서 파일시스템 데이터를 찾을 수 없습니다. (출력값:{str(stdout_data).strip()[:200]}...)")
            if is_pass == 1:
                message = f"✅ 모든 파일시스템 사용률이 정상입니다. (기준: {threshold}%)"
            else:
                message = "\n".join(messages_list) if messages_list else f"알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def df_type2(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            command_error = self._detect_df_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            results_fail = []
            
            try:
                criteria = float(self.inspection_criteria)
            except Exception:
                criteria = 90.0

            if not lines or "filesystem" not in lines[0].lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 7 and "%" in parts[3]:
                    try:
                        usage_percent = float(parts[3].replace("%", ""))
                        mount_point = parts[6]
                        if usage_percent > criteria:
                            is_pass = 0
                            results_fail.append(f"❌ {mount_point}: {usage_percent:.1f}% (기준 {criteria:.1f}%)")
                    except ValueError:
                        continue

            if not results_fail:
                message = f"✅ 모든 파일 시스템 사용량이 임계값({criteria:.1f}%) 이하입니다."
            else:
                message = "\n".join(results_fail)
            
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"디스크 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def sar_disk_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            threshold = self.inspection_criteria if isinstance(self.inspection_criteria, (int, float)) else 20

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "avwait" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'avwait' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            data_started = False
            disk_data_found_count = 0

            for line in lines:
                stripped_line = line.strip()
                if not data_started and "device" in stripped_line:
                    data_started = True
                    continue
                
                if not data_started or not stripped_line:
                    continue

                if stripped_line.lower().startswith("average"):
                    continue

                parts = stripped_line.split()

                if len(parts) >= 7:
                    try:
                        device_name = parts[1]
                        avwait = float(parts[6])
                        disk_data_found_count += 1
  
                        if avwait >= threshold:
                            is_pass = 0
                            message_list.append(f"❌ 디스크 '{device_name}' 의 avwait 값 {avwait}ms (기준: {threshold}ms) 기준값 초과")

                    except ValueError:
                        is_pass = 0
                        message_list.append(f"❌ 디스크 '{device_name}' 의 avwait 값 파싱 오류: '{stripped_line}' 에서 avwait 값을 숫자로 변환할 수 없습니다.")
                elif stripped_line and data_started:
                    is_pass = 0
                    message_list.append(f"❌ 예상치 못한 형색의 Average 섹션 라인: {stripped_line}")

            if not data_started or disk_data_found_count == 0:
                is_pass = 0
                message_list.insert(0, f"❌ 'sar -d' 명령어 출력에서 유효한 Average 섹션 디스크 데이터를 찾을 수 없습니다. ")
            if is_pass == 1:
                message = f"✅ 모든 디스크의 I/O 대기 시간이 정상입니다."
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 디스크 I/O 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK I/O 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def aix_iostat_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            command_error = self._detect_iostat_command_error(stdout_data)
            if command_error:
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            disk_blocks = re.split(r'(?=hdisk\d+\s+xfer:)', stdout_data)
            failed_disks_messages = []
    
            for block in disk_blocks:
                if not block.strip() or not block.startswith('hdisk'):
                    continue
    
                lines = block.strip().splitlines()
                parsed_values = self._parse_iostat_values(lines)
    
                if not parsed_values:
                    failed_disks_messages.append(f"❌ '{lines[0].split()[0] if lies else '알 수 없는 디스크'}' 블록에서 데이터 파싱 실패")
                    continue
    
                disk_name = parsed_values.get('disk_name', '알 수 없는 디스크')
                failed_metrics = self._check_thresholds(parsed_values, self.inspection_criteria)
    
                if failed_metrics:
                    failed_disks_messages.append(
                            f"{disk_name:}: [{', '.join(failed_metrics)}]"
                    )
    
            if failed_disks_messages:
                is_pass = 0
                message = "❌ 디스크 I/O 점검 필요:\n" + "\n".join(failed_disks_messages)
            else:
                is_pass = 1
                message = "✅ 모든 디스크의 I/O 상태가 정상입니다."
    
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK I/O 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def _check_thresholds(self, parsed_values, criteria):
        failed_metrics = []
    
        # 각 항목 검사
        if parsed_values.get('tm_act', 0) > criteria.get('tm_act', 999.0):
            failed_metrics.append(f"%tm_act ({parsed_values['tm_act']} > {criteria['tm_act']})")
        if parsed_values.get('read_timeouts', 0) > criteria.get('timeouts', 999):
            failed_metrics.append(f"read timeouts ({parsed_values['read_timeouts']} > {criteria['timeouts']})")
        if parsed_values.get('read_fails', 0) > criteria.get('fails', 999):
            failed_metrics.append(f"read fails ({parsed_values['read_fails']} > {criteria['fails']})")
        if parsed_values.get('read_avgserv', 0) > criteria.get('avgserv', 999.0):
            failed_metrics.append(f"read avgserv ({parsed_values['read_avgserv']} > {criteria['avgserv']})")
        if parsed_values.get('read_maxserv', 0) > criteria.get('maxserv', 999.0):
            failed_metrics.append(f"read maxserv ({parsed_values['read_maxserv']} > {criteria['maxserv']})")
        if parsed_values.get('write_timeouts', 0) > criteria.get('timeouts', 999):
            failed_metrics.append(f"write timeouts ({parsed_values['write_timeouts']} > {criteria['timeouts']})")
        if parsed_values.get('write_fails', 0) > criteria.get('fails', 999):
            failed_metrics.append(f"write fails ({parsed_values['write_fails']} > {criteria['fails']})")
        if parsed_values.get('write_avgserv', 0) > criteria.get('avgserv', 999.0):
            failed_metrics.append(f"write avgserv ({parsed_values['write_avgserv']} > {criteria['avgserv']})")
        if parsed_values.get('write_maxserv', 0) > criteria.get('maxserv', 999.0):
            failed_metrics.append(f"write maxserv ({parsed_values['write_maxserv']} > {criteria['maxserv']})")
        if parsed_values.get('sqfull', 0) > criteria.get('sqfull', 999):
            failed_metrics.append(f"queue sqfull ({parsed_values['sqfull']} > {criteria['sqfull']})")

        return failed_metrics

    def _parse_iostat_values(self, lines):
        values = {}
        header_map = {}
        current_disk_name = "알 수 없는 디스크"

        try:
            i = 0
            while i < len(lines):
                line = lines[i]

                xfer_header_match = re.match(r'^(hdisk\d+)\s+xfer:\s+(.*)', line)
                
                if xfer_header_match:
                    current_disk_name = xfer_header_match.group(1)
                    header_parts = xfer_header_match.group(2).strip().split()
                    header_map['xfer'] = {name: idx for idx, name in enumerate(header_parts)}

                    if i + 1 < len(lines) and lines[i+1].strip():
                        parts = lines[i+1].strip().split()
                        try:
                            if '%tm_act' in header_map['xfer']:
                                values['tm_act'] = float(parts[header_map['xfer']['%tm_act']])
                        except (ValueError, IndexError) as e:
                            print(f"파싱 오류: '{current_disk_name}'의 '%tm_act' 처리 중. {e}")
                    i += 2
                    continue

                for section in ['read', 'write', 'queue']:
                    header_match = re.match(r'^\s*' + section + r':\s+(.*)', line)
                    if header_match:
                        header_parts = header_match.group(1).strip().split()
                        header_map[section] = {name: idx for idx, name in enumerate(header_parts)}

                        if i + 1 < len(lines) and lines[i+1].strip():
                            parts = lines[i+1].strip().split()
                            try:
                                if section == 'read':
                                    if 'avgserv' in header_map['read']: values['read_avgserv'] = float(parts[header_map['read']['avgserv']])
                                    if 'maxserv' in header_map['read']: values['read_maxserv'] = float(parts[header_map['read']['maxserv']])
                                    if 'timeouts' in header_map['read']: values['read_timeouts'] = int(parts[header_map['read']['timeouts']])
                                    if 'fails' in header_map['read']: values['read_fails'] = int(parts[header_map['read']['fails']])
                                elif section == 'write':
                                    if 'avgserv' in header_map['write']: values['write_avgserv'] = float(parts[header_map['write']['avgserv']])
                                    if 'maxserv' in header_map['write']: values['write_maxserv'] = float(parts[header_map['write']['maxserv']])
                                    if 'timeouts' in header_map['write']: values['write_timeouts'] = int(parts[header_map['write']['timeouts']])
                                    if 'fails' in header_map['write']: values['write_fails'] = int(parts[header_map['write']['fails']])
                                elif section == 'queue':
                                    if 'sqfull' in header_map['queue']: values['sqfull'] = float(parts[header_map['queue']['sqfull']])
                            except (ValueError, IndexError) as e:
                                print(f"파싱 오류: '{current_disk_name}'의 '{section}' 섹션 처리 중. {e}")

                        i += 2
                        break
                else:
                    i += 1

            values['disk_name'] = current_disk_name
        except Exception as e:
            print(f"iostat 값 파싱 중 예외 발생: {e}")

        return values

    def linux_iostat_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_iostat_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            criteria = self.inspection_criteria
            if not isinstance(criteria, dict):
                criteria = {}

            iowait_threshold = criteria.get('iowait', 10.0)
            await_threshold = criteria.get('await', 20.0)
            util_threshold = criteria.get('util', 80.0)

            lines = stdout_data.strip().splitlines()
            failed_messages = []
            header_found = False

            try:
                for i, line in enumerate(lines):
                    if line.strip().startswith('avg-cpu:'):
                        header_found = True
                        cpu_headers = line.split()
                        cpu_values = lines[i+1].split()

                        if '%iowait' in cpu_headers:
                            iowait_header_idx = cpu_headers.index('%iowait')
                            offset = len(cpu_headers) - len(cpu_values)
                            iowait_value_idx = iowait_header_idx - offset

                            if 0 <= iowait_value_idx < len(cpu_values):
                                iowait_value = float(cpu_values[iowait_value_idx])
                                if iowait_value > iowait_threshold:
                                    failed_messages.append(f"❌ CPU %iowait가 임계값을 초과했습니다: {iowait_value}% (기준: {iowait_threshold}%) ")
                            else:
                                debug_info = (f"DEBUG INFO: "
                                            f"Headers({len(cpu_headers)}): {cpu_headers}\n"
                                            f"Values({len(cpu_values)}): {cpu_values}\n"
                                            f"Header_Idx: {iowait_header_idx}\n"
                                            f"offset: {offset}\n"
                                            f"Calculated_value_Idx: {iowait_value_idx}")
                                failed_messages.append(f"❌ CPU %iowait 값의 인덱스를 계산할 수 없습니다.\n [{debug_info}]")
            except (ValueError, IndexError) as e:
                failed_messages.append(f"❌ CPU %iowait 점검 중 오류 발생({type(e).__name__}): {e}")

            try:
                device_header_index = -1
                for i, line in enumerate(lines):
                    if line.startswith('Device'):
                        header_found = True
                        device_header_index = i
                        break

                if device_header_index != -1:
                    device_headers = lines[device_header_index].split()
                    await_index = device_headers.index('await') if 'await' in device_headers else -1
                    util_index = device_headers.index('%util') if '%util' in device_headers else -1

                    if await_index != -1 and util_index != -1:
                        for i in range(device_header_index + 1, len(lines)):
                            parts = lines[i].split()
                            if not parts: continue
                            device_name = parts[0]
                            try:
                                await_value = float(parts[await_index])
                                util_value = float(parts[util_index])

                                if await_value > await_threshold:
                                    failed_messages.append(f"❌ 장치 '{device_name}의 await 시간이 임계값을 초과했습니다. {await_value} (기준: {await_threshold})")
                                if util_value > util_threshold:
                                    failed_messages.append(f"❌ 장치 '{device_name}의 %util이 임계값을 초과했습니다. {util_value}% (기준: {util_threshold}%)")
                            except (ValueError, IndexError):
                                continue

            except (ValueError, IndexError) as e:
                failed_messages.append(f"❌ Device I/O 점검 중 오류 발생: {e}")

            if not header_found:
                is_pass = 0
                message = f"❌ 명령어 실패: iostat 출력에서 필수 헤더(avg-cpu 또는 Device)를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if failed_messages:
                is_pass = 0
                message = "I/O 점검 결과, 다음 항목이 임계값을 초과했습니다:\n" + "\n".join(failed_messages)
            else:
                is_pass = 1
                message = "✅ 모든 I/O 항목이 정상 범위 내에 있습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ iostat -x 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def vmstat_type1(self, stdout_data):
        try:
            is_success = 1
            criteria = self.inspection_criteria

            if not isinstance(criteria, dict):
                is_pass = 0
                message = "❌ inspection_criteria가 딕셔너리 형식이 아닙니다."
                result = message
                return is_success, is_pass, result, message

            missing_keys = []
            if 'b' not in criteria:
                missing_keys.append("'b' 키")
            if 'wa' not in criteria:
                missing_keys.append("'wa' 키")

            if missing_keys:
                is_pass = 0
                message = f"❌ inspection_criteria에 다음 키가 선언되지 않았습니다: {', '.join(missing_keys)}"
                result = message
                return is_success, is_pass, result, message

            b_threshold = criteria['b']
            wa_threshold = criteria['wa']

            lines = stdout_data.strip().splitlines()

            header_line = None
            data_line = None

            for i, line in enumerate(lines):
                if 'r' in line and 'b' in line and 'swpd' in line:
                    header_line = line
                    if i + 1 < len(lines):
                        data_line = lines[i+1]
                    break

            if not header_line or not data_line:
                is_pass = 0
                message = "❌ vmstat 출력에서 유효한 헤더 또는 데이터 라인을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            header_parts = header_line.split()
            data_parts = data_line.split()

            try:
                b_col_idx = header_parts.index('b')
                wa_col_idx = header_parts.index('wa')
            except ValueError:
                is_pass = 0
                message = "❌ vmstat 출력 헤더에서 'b' 또는 'wa' 컬럼을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_messages = []

            try:
                b_value = int(data_parts[b_col_idx])
                wa_value = int(data_parts[wa_col_idx])

                if b_value > b_threshold:
                    failed_messages.append(f"Blocked Processes(b)가 임계값을 초과했습니다: {b_value} (기준: {b_threshold})")
                if wa_value > wa_threshold:
                    failed_messages.append(f"IO Wait(wa)가 임계값을 초과했습니다: {wa_value} (기준: {wa_threshold}%)")

            except (ValueError, IndexError):
                is_pass = 0
                message = f"❌ vmstat 데이터 라인 파싱 중 오류 발생: {data_line}"
                result = message
                return is_success, is_pass, result, message

            if failed_messages:
                is_pass = 0
                message = "❌ vmstat 점검 결과, 다음 항목이 임계값을 초과했습니다:\n" + "\n".join(failed_messages)
            else:
                is_pass = 1
                message = f"✅ vmstat의 Blocked Processes(b)와 IO Wait(wa)가 정상 범위 내에 있습니다.\n 'Blocked Processes(b)': {b_value} \n 'IO Wait(wa)': {wa_value}"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ vmstat 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def du_type1(self, stdout_data):
        try:
            is_success = 1
            output_lower = stdout_data.lower()
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]

            if "no such" in output_lower or "not found" in output_lower or "없습니다" in stdout_data:
                is_pass = 0
                message = "❌ 점검 필요: 점검 대상 경로가 없습니다."
            elif not lines:
                is_pass = 0
                message = "❌ 점검 필요: 명령어 결과가 없습니다."
            else:
                first_parts = lines[0].split(maxsplit=1)
                if len(first_parts) < 2:
                    is_pass = 0
                    message = "❌ 점검 필요: 명령어 결과 형식이 올바르지 않습니다."
                else:
                    is_pass = 1
                    message = "✅ 정상: 용량 및 경로 정보를 확인했습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ du -sh 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
