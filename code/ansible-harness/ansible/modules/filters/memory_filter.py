from .base_filter import BaseFilter, filter_result
import re

class MemoryFilter(BaseFilter):
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
        message = ""
        if "free -m" in self.command:
            is_success, is_pass, result, message = self.free_type1(stdout_data)
        elif "dmidecode -t memory" in self.command:
            is_success, is_pass, result, message = self.dmidecode_type1(stdout_data)
        elif "show chassis routing-engine" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "stat ns" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
        elif "free -h" in self.command:
            is_success, is_pass, result, message = self.free_type_h(stdout_data)
        elif "sar -r" in self.command:
            is_success, is_pass, result, message = self.sar_type1(stdout_data)
        elif "swapinfo -tam" in self.command:
            is_success, is_pass, result, message = self.swapinfo_type1(stdout_data)
        elif "machinfo" in self.command:
            is_success, is_pass, result, message = self.machinfo_type1(stdout_data)
        elif "lsdev -Cc memory" in self.command:
            is_success, is_pass, result, message = self.lsdev_type1(stdout_data)
        elif "svmon -G" in self.command:
            is_success, is_pass, result, message = self.svmon_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }

    def citrix_type1(self, stdout_data):
        """Citrix 'stat ns' 출력에서 InUse Memory (%) 사용률을 추출합니다."""
        try:
            is_success = 1
            inuse_mem = None

            mem_match = re.search(r"InUse Memory \(%\)\s+([\d.]+)", stdout_data)
            if mem_match:
                inuse_mem = float(mem_match.group(1))

            if inuse_mem is None:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패: 'InUse Memory (%)'를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            is_pass = 1 if inuse_mem <= self.inspection_criteria else 0
            status = "✅" if is_pass else "❌"
            
            message = f"{status} InUse Memory: {inuse_mem}% (기준: {self.inspection_criteria}%)"
            if not is_pass:
                message += " - 기준값 초과"
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Citrix 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def juniper_type1(self, stdout_data):
        """Juniper 'show chassis routing-engine' 출력에서 Memory 사용률 추출"""
        try:
            is_success = 1
            mem_match = re.search(r'Memory utilization\s+(\d+)\s+percent', stdout_data)
            if mem_match:
                usage = int(mem_match.group(1))
                is_pass = 1 if usage <= self.inspection_criteria else 0
                status = "✅" if is_pass else "❌"
                message = f"{status} 메모리 사용률: {usage}% (기준: {self.inspection_criteria}%)"
                if not is_pass:
                    message += " 초과"
                result = message
            else:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패: 'Memory utilization' 값을 찾을 수 없습니다."
                result = message
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    # 주석을 잘 달아주세요
    # Command: free -m
    # Result: 
    #               total        used        free      shared  buff/cache   available
    # Mem:          15760        5476        4019         181        6264        9773
    # Swap:          4039           0        4039

    def free_type1(self,stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            mem_line = next((line for line in lines if line.lower().startswith("mem")), None)
            if mem_line:
                parts = mem_line.split()
                total = int(parts[1])
                used = int(parts[2])
                usage = (used / total) * 100
                is_pass = 1 if usage <= self.inspection_criteria else 0
                status = "✅" if is_pass else "❌"
                message = f"{status} 메모리 사용률 {usage:.1f}% (조건: {self.inspection_criteria}% 초과)"
                result = message
            else:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패"
                result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def free_type_h(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            mem_line = next((line for line in lines if line.lower().startswith("mem")), None)
            if mem_line:
                parts = mem_line.split()
                total_str = parts[1]
                used_str = parts[2]

                total = self.convert_to_mb(total_str)
                used = self.convert_to_mb(used_str)

                if total > 0:
                    usage = (used / total) * 100
                    is_pass = 1 if usage <= self.inspection_criteria else 0
                    status = "✅" if is_pass else "❌"
                    message = f"{status} 메모리 사용률 {usage:.1f}%"
                    result = message
                else:
                    is_pass = 0
                    message = "❌ 메모리 total 값을 파싱할 수 없습니다."
                    result = message
            else:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패"
                result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def convert_to_mb(self, value_str):
        value_str = value_str.upper()
        if 'G' in value_str:
            return float(value_str.replace('G', '')) * 1024
        elif 'M' in value_str:
            return float(value_str.replace('M', ''))
        elif 'K' in value_str:
            return float(value_str.replace('K', '')) / 1024
        elif 'B' in value_str:
            return float(value_str.replace('B', '')) / (1024*1024)
        else:
            return float(value_str)

    # Command: dmidecode -t memory
    # Result: 
    # 할당된 메모리가 정상 인식 여부 확인
    # 정상판단기준 : 
    # size / speed / form_factor / rank 항목 등이 No Module Installed' or 'Unknown' 이면 안됨

    def dmidecode_type1(self,stdout_data):
        try:
            is_success = 1     
            message = ""
            result = ""

            modules = re.split(r'\n(?=Memory Device)', stdout_data)
            issues = []

            if modules:
                for index, module in enumerate(modules, 1):
                    size_match = re.search(r'Size: (.+)', module)
                    speed_match = re.search(r'Speed: (.+)', module)
                    form_factor_match = re.search(r'Form Factor: (.+)', module)
                    rank_match = re.search(r'Rank: (.+)', module)

                    size = size_match.group(1) if size_match else 'Unknown'
                    speed = speed_match.group(1) if speed_match else 'Unknown'
                    form_factor = form_factor_match.group(1) if form_factor_match else 'Unknown'
                    rank = rank_match.group(1) if rank_match else 'Unknown'

#                    if size == 'No Module Installed' or 'Unknown' in (size, speed, form_factor, rank):
#                        issues.append({
#                            'Module': index,
#                            'Size': size,
#                            'Speed': speed,
#                            'Form Factor': form_factor,
#                            'Rank': rank
#                        })
                
#            if issues:
#                is_pass = 0
#                message = "❌ 할당된 메모리에 문제가 있습니다.\n 확인 필요:" + "\n".join(issues)
#                result = str(issues)
            if size:
                is_pass = 1
                status = "✅"
                message = f"{status} 할당된 메모리는 정상입니다."
                result = message
            else:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패"
                result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    # Command: sar -r
    # Result: 
    # Linux 3.10.0-1160.el7.x86_64 (hostname)   12/01/23   _x86_64_  (6 CPU)
    # 12:00:01    kbmemfree kbmemused  %memused kbbuffers  kbcached  kbcommit   %commit
    # 12:10:01      4019000  11747000     74.51    626400   5638000  15760000     99.99
    # 12:20:01      3980000  11776000     74.73    628000   5642000  15780000     99.99
    # 12:30:01      3950000  11806000     74.95    630000   5646000  15800000     99.99
    # Average:      3950000  11806000     74.95    630000   5646000  15800000     99.99
    # 설명: sar 명령어를 통한 메모리 사용률 점검 (10분 단위)
    # Average 라인의 %memused 값을 확인
    def sar_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            
            # Average 라인 찾기 (영어/한글 모두 지원)
            avg_line = next((line for line in lines if "Average:" in line or "평균값:" in line), None)
            if avg_line:
                parts = avg_line.split()
                # Try to locate header line to find index of %memused
                memused_idx = None
                try:
                    avg_pos = lines.index(avg_line)
                    header_search_space = lines[max(0, avg_pos-5):avg_pos]
                    for hdr in reversed(header_search_space):
                        hdr_parts = hdr.split()
                        for i, tok in enumerate(hdr_parts):
                            if '%memused' in tok.lower():
                                memused_idx = i
                                break
                        if memused_idx is not None:
                            break
                except Exception:
                    memused_idx = None
                try:
                    if memused_idx is not None and len(parts) > memused_idx:
                        memused = float(parts[memused_idx])
                    else:
                        # Fallback: pick the first float token that looks like a percent (<=100)
                        memused = None
                        for p in parts:
                            try:
                                v = float(p)
                                if 0.0 <= v <= 100.0:
                                    memused = v
                                    break
                            except Exception:
                                continue
                        if memused is None:
                            raise ValueError('메모리 사용률(%memused) 파싱 실패')
                    
                    is_pass = 1 if memused <= self.inspection_criteria else 0
                    status = "✅" if is_pass else "❌"
                    criteria = self.inspection_criteria
                    if is_pass:
                        message = f"{status} 메모리 사용률 (%memused): {memused:.1f}% (기준 {criteria}%) "
                    else:
                        message = f"{status} 메모리 사용률 (%memused): {memused:.1f}% (기준 {criteria}%) 초과"
                    result = message
                except (ValueError, IndexError):
                    is_pass = 0
                    message = "❌ 메모리 사용률 파싱 실패"
                    result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ sar 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def swapinfo_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message = ""
            result = ""

            target_line_name = "total"
            threshold = 80

            if isinstance(self.inspection_criteria, list) and len(self.inspection_criteria) == 2:
                target_line_name = str(self.inspection_criteria[0]).lower()
                try:
                    threshold = float(self.inspection_criteria[1])
                except ValueError:
                  pass
            elif isinstance(self.inspection_criteria, dict):
                target_line_name = self.inspection_criteria.get('target_line', 'total').lower()
                threshold = self.inspection_criteria.get('threshold', 80)
            elif isinstance(self.inspection_criteria, (int, float)):
                threshold = self.inspection_criteria

            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "USED" not in stdout_data:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            pct_used_value = None

            for line in lines:
                stripped_line = line.strip()
                match = re.match(rf"^{target_line_name}\s+", stripped_line.lower())
                if match:
                    parts = stripped_line.split()
                    if len(parts) >= 5:
                      pct_used_str = parts[4]
                      if pct_used_str.endswith("%"):
                          pct_used_value = float(pct_used_str.replace("%", ""))
            
            if pct_used_value is None:
                is_pass = 0
                message = f"❌ 메모리 정보 확인 실패: 'momory' 행의 'USED' 값을 찾을 수 없습니다.(출력값:{str(stdout_data).strip()[:200]}...)"
                result = message
            else:
                if pct_used_value < threshold:
                    is_pass = 1
                    status = "✅"
                    message = f"{status} {target_line_name.capitalize()} PCT USED: {pct_used_value}% (기준: {threshold}%)"
                else:
                    is_pass = 1
                    status = "❌"
                    message = f"{status} {target_line_name.capitalize()} PCT USED: {pct_used_value}% (기준: {threshold}%)"
                result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 파일시스템 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
    
    def machinfo_type1(self, stdout_data):
    
        def _extract_mb_from_string(mem_str):
            mb_match = re.search(r"(\d+)\s*MB", mem_str)
            if mb_match:
                return int(mb_match.group(1))

            gb_match = re.search(r"(\d+\.?\d*)\s*GB", mem_str)
            if gb_match:
                return int(float(gb_match.group(1)) * 1024)

            return 0

        try:
            is_success = 1
            is_pass = 1
            message = ""
            result = ""

            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or not("Memory Information" in stdout_data or "Memory: " in stdout_data): 
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 실패: 필수 메모리 정보를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            physical_memory_mb = None
            configured_memory_mb = None

            lines = stdout_data.splitlines()


            for line in lines:
                stripped_line = line.strip()

                physical_match = re.search(r"Physical Memory\s*:\s*(.+)", stripped_line)
                if physical_match:
                    physical_memory_mb = _extract_mb_from_string(physical_match.group(1))

                configured_match = re.search(r"Configured Memory\s*:\s*(.+)", stripped_line)
                if configured_match:
                    configured_memory_mb = _extract_mb_from_string(configured_match.group(1))

                if re.match(r"^Memory:\s*", stripped_line) and physical_memory_mb is None:
                    direct_memory_value = re.search(r"^Memory:\s*(.+)", stripped_line)
                    if direct_memory_value:
                        physical_memory_mb = _extract_mb_from_string(direct_memory_value.group(1))

            messages_list = []

            if physical_memory_mb is None or physical_memory_mb <= 0:
                is_pass = 0
                messages_list.append("❌ Physical Memory 정보가 없거나 0MB 이하 입니다.")

            if is_pass == 1:
                if physical_memory_mb is not None:
                    mem_info = f"{physical_memory_mb} MB"
                    if configured_memory_mb is not None:
                        mem_info += f"(Configured: {configured_memory_mb} MB)"
                    message = f"✅ 메모리 상태 정상: {mem_info}"
                else:
                    message = "✅ 상세 정보 확인 필요"
            else:
                message = "\n".join(messages_list) if messages_list else f"❌ 메모리 상태 점검 실패. (출력값: {str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def lsdev_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            if not lines:
                is_pass = 0
                message = f"❌ 메모리 상태 점검 실패: '{self.command}' 명령어 출력이 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_devices = []
            total_devices = 0
            expected_status = self.inspection_criteria.lower()

            for line in lines:
                line_content = line.strip()
                if not line_content:
                    continue

                parts = line_content.split()

                if len(parts) >= 2:
                    device_name, status = parts[0], parts[1]

                    if device_name.lower() == 'name' and status.lower() == 'status':
                        continue

                    total_devices += 1
                    if status.lower() != expected_status:
                        failed_devices.append(f"{device_name}({status})")

            if total_devices == 0:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패: 유효한 메모리 장치 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            if failed_devices:
                is_pass = 0
                message = f"❌ 일부 메모리 장치가 비정상 상태입니다. {', '.join(failed_devices)}. (기준: {self.inspection_criteria})"
            else:
                is_pass = 1
                message = f"✅ 모든 메모리 장치 ({total_devices}개)가 정상 상태('{self.inspection_criteria}')입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ lsdev  메모리 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def svmon_type1(self, stdout_data):
        try:
            is_success = 1
            command_error = self._detect_command_error(stdout_data)
            if command_error:
                is_pass = 0
                message = f"❌ 명령어 실패: {command_error.splitlines()[0]}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            mem_line = next((line for line in lines if line.strip().startswith("memory")), None)

            if mem_line:
                parts = mem_line.split()
                size = int(parts[1])
                inuse = int(parts[2])

                if size > 0:
                    usage = (inuse / size) * 100
                    is_pass = 1 if usage <= self.inspection_criteria else 0
                    status = "✅" if is_pass else "❌"
                    message = f"{status} 메모리 사용률: {usage:.1f}% (기준: {self.inspection_criteria}%)"
                    if not is_pass:
                        message += " - 기준값 초과"
                    result = message
                else:
                    is_pass = 0
                    message = "❌ 메모리 'size' 값이 0이므로 사용률 계산할 수 없습니다."
                    result = message
            else:
                is_pass = 0
                message = f"❌ '{self.command}' 출력에서 'memory' 라인을 찾을 수 없습니다."
                result = message

        except (ValueError, IndexError) as e:
            is_pass = 0
            is_success = 0
            message = f"❌ svmon 메모리 평가 실패: 데이터 파싱 중 오류가 발생했습니다. ({e})"
            result = message
        except Exception as e:
             is_success = 0
             is_pass = 0
             message = f"❌ svmon  메모리 평가 실패: {str(e)}"
             result = message

        return is_success, is_pass, result, message
