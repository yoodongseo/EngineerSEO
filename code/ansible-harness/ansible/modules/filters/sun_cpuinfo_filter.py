from .base_filter import BaseFilter, filter_result
import re

class SunCPUInfoFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1        
        message = ""
        
        if "top -bn1 | grep 'Cpu(s)'" in self.command:
            is_success, is_pass, result, message = self.top_type1(stdout_data)
        elif "stat ns" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
        elif "mpstat" in self.command:
            is_success, is_pass, result, message = self.mpstat_type1(stdout_data)
        elif "sar" in self.command:
            is_success, is_pass, result, message = self.sar_type1(stdout_data)
        elif "vmstat" in self.command:
            is_success, is_pass, result, message = self.vmstat_type1(stdout_data)
        elif "prstat" in self.command:
            is_success, is_pass, result, message = self.prstat_type1(stdout_data)
        elif "psrinfo" in self.command:
            is_success, is_pass, result, message = self.psrinfo_v_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message
        
        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success
        }

    def citrix_type1(self, stdout_data):
        """Citrix 'stat ns' 출력에서 Packet/Management CPU 사용률을 추출합니다."""
        try:
            is_success = 1
            packet_cpu = None
            mgmt_cpu = None

            packet_match = re.search(r"Packet CPU usage \(%\)\s+([\d.]+)", stdout_data)
            if packet_match:
                packet_cpu = float(packet_match.group(1))

            mgmt_match = re.search(r"Management CPU usage \(%\)\s+([\d.]+)", stdout_data)
            if mgmt_match:
                mgmt_cpu = float(mgmt_match.group(1))

            if packet_cpu is None or mgmt_cpu is None:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: Packet 또는 Management CPU 사용률을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            is_pass = 1 if packet_cpu <= self.inspection_criteria and mgmt_cpu <= self.inspection_criteria else 0
            status = "✅" if is_pass else "❌"
            
            message = f"{status} Packet CPU: {packet_cpu}%, Management CPU: {mgmt_cpu}% (기준: {self.inspection_criteria}%)"
            if not is_pass:
                message += " - 기준값 초과"
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Citrix CPU 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def juniper_type1(self, stdout_data):
        """Juniper 'show chassis routing-engine' 출력에서 CPU 사용률 추출"""
        try:
            is_success = 1
            idle_match = re.search(r'Idle\s+(\d+)\s+percent', stdout_data)
            if idle_match:
                idle_percent = int(idle_match.group(1))
                usage = 100 - idle_percent
                is_pass = 1 if usage <= self.inspection_criteria else 0
                status = "✅" if is_pass else "❌"
                result = message
            else:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 'Idle' 값을 찾을 수 없습니다."
                result = message
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ CPU 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    # 주석을 잘 달아주세요
    # Command: top -bn1 | grep 'Cpu(s)'
    # Result: 
    # %Cpu(s):  1.8 us,  5.5 sy,  0.0 ni, 91.7 id,  0.0 wa,  0.0 hi,  0.9 si,  0.0 st
    def top_type1(self,stdout_data):
        try:
            is_success = 1            
            lines = stdout_data.splitlines()
            cpu_line = next((line for line in lines if "Cpu(s):" in line or "CPU:" in line), None)
            if cpu_line:
                usage = 0.0
                for part in cpu_line.split(","):
                    part = part.strip()
                    try:
                        value = float(part.split(" ")[0])
                        if "us" in part or "sy" in part:
                            usage += value
                    except ValueError:
                        continue  # 숫자로 변환 안 되면 스킵
                is_pass = 1 if usage <= self.inspection_criteria else 0
                status = "✅" if is_pass else "❌"
                message = f"{status} CPU 사용률 (user+system): {usage:.1f}%"
                result = message
            else:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패"
                result = message
        except Exception as e:
            is_pass = 0
            message = f"❌ CPU 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    # Command: lscpu
    # Result: 
    # Architecture:        x86_64
    # CPU op-mode(s):      32-bit, 64-bit
    # Byte Order:          Little Endian
    # CPU(s):              6
    # On-line CPU(s) list: 0-5
    # Thread(s) per core:  1
    # Core(s) per socket:  1
    # Socket(s):           6
    # NUMA node(s):        1
    # Vendor ID:           GenuineIntel
    # CPU family:          6
    # Model:               85
    # Model name:          Intel(R) Xeon(R) Silver 4208 CPU @ 2.10GHz
    # Stepping:            7
    # CPU MHz:             2095.077
    # BogoMIPS:            4190.15
    # Hypervisor vendor:   VMware
    # Virtualization type: full
    # L1d cache:           32K
    # L1i cache:           32K
    # L2 cache:            1024K
    # L3 cache:            11264K
    # NUMA node0 CPU(s):   0-5
    # Flags:               fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon nopl xtopology tsc_reliable nonstop_tsc cpuid pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch invpcid_single ssbd ibrs ibpb stibp ibrs_enhanced fsgsbase tsc_adjust bmi1 avx2 smep bmi2 invpcid avx512f avx512dq rdseed adx smap clflushopt clwb avx512cd avx512bw avx512vl xsaveopt xsavec xgetbv1 xsaves arat pku ospke avx512_vnni md_clear flush_l1d arch_capabilities
    # 설명: CPU 코어별 상태 점검  
    # 물리적 코어의 정상(online/offline) 유무 점검
    # CPU(s) 와 On-line CPU(s) list 개수가 같아야 함
    def lscpu_type1(self, stdout_data):
        try:
            is_success = 1                        
            total_cpus = int(self.parse_value(stdout_data, "CPU(s)"))
            online_list_str = self.parse_value(stdout_data, "On-line CPU(s) list")
            online_count = self.count_online_cpus(online_list_str)

            if str(total_cpus).isdigit() and str(online_count).isdigit():
                if total_cpus == online_count:                
                    is_pass = 1 
                    message = f"✅ 모든 CPU가 온라인 상태입니다"
                    result = message
                else:
                    is_pass = 0
                    message = "❌ 일부 CPU가 오프라인 상태이면 성능저하가 발생"
                    result = message    
            else:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패"
                result = message
        except Exception as e:
            is_pass = 0
            message = f"❌ CPU 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def lscpu_type2(self, stdout_data):
        try:
            is_success = 1
            total_cpus_str = self.parse_value(stdout_data, "CPU(s)")
            online_list_str = self.parse_value(stdout_data, "On-line CPU(s) list")

            if not total_cpus_str.isdigit():
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 'CPU(s)' 값이 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            total_cpus = int(total_cpus_str)
            all_cpus_set = set(range(total_cpus))
            online_cpus_set = self._parse_cpu_list_to_set(online_list_str)

            offline_cpus = sorted(list(all_cpus_set - online_cpus_set))

            if not offline_cpus:
                is_pass = 1
                message = f"✅ 모든 CPU({total_cpus}개)가 온라인 상태입니다."
            else:
                is_pass = 0
                offline_str = ", ".join(map(str, offline_cpus))
                message = f"❌ 다음 CPU가 오프라인 상태입니다: {offline_str}"

            result = message

        except (ValueError, IndexError) as e:
            is_pass = 0
            is_success = 0
            message = f"❌ CPU 코어 평가 실패: {str(e)}"
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ CPU 코어 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def parse_value(self, output, key):
        pattern = rf'^{re.escape(key)}\s*:\s*(.+)$'
        for line in output.splitlines():
            m = re.match(pattern, line)
            if m:
                return m.group(1).strip()
        raise ValueError(f"'{key}' 항목을 찾을 수 없습니다.")

    def _parse_cpu_list_to_set(self, cpu_list_str):
        online_cpus = set()
        for part in cpu_list_str.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                start, end = map(int, part.split('-', 1))
                online_cpus.update(range(start, end + 1))
            else:
                online_cpus.add(int(part))
        return online_cpus




    # Command: sar -u
    # Result: 
    # Linux 3.10.0-1160.el7.x86_64 (hostname)   12/01/23   _x86_64_  (6 CPU)
    # 12:00:01        CPU     %user     %nice   %system   %iowait    %steal     %idle
    # 12:10:01        all      1.50      0.00      5.25      0.00      0.00     93.25
    # 12:20:01        all      2.10      0.00      6.15      0.50      0.00     91.25
    # 12:30:01        all      1.80      0.00      5.80      0.20      0.00     92.20
    # Average:        all      1.80      0.00      5.80      0.20      0.00     92.20
    # 설명: sar 명령어를 통한 CPU 사용률 점검 (10분 단위)
    # Average 라인의 user 값을 기준값과 비교
    def sar_type1(self, stdout_data):
        try:
            is_success = 1            
            lines = stdout_data.splitlines()
            
            # Average 라인 찾기 (영어/한글 모두 지원)
            avg_line = next((line for line in lines if "Average:" in line or "평균값:" in line), None)
            if avg_line:
                parts = avg_line.split()
                if len(parts) >= 7:
                    try:
                        user = float(parts[2])
                        
                        # user 값만 기준값과 비교
                        is_pass = 1 if user <= self.inspection_criteria else 0
                        status = "✅" if is_pass else "❌"
                        
                        criteria = self.inspection_criteria
                        if is_pass:
                            message = f"{status} CPU 사용률 (user): {user:.1f}% (기준 {criteria}%)"
                        else:
                            message = f"{status} CPU 사용률 (user): {user:.1f}% (기준 {criteria}%) 초과"
                        result = message
                    except (ValueError, IndexError):
                        is_pass = 0
                        message = "❌ CPU 사용률 파싱 실패"
                        result = message
                else:
                    is_pass = 0
                    message = "❌ sar 출력 형식이 올바르지 않습니다"
                    result = message
            else:
                is_pass = 0
                message = "❌ sar Average 라인을 찾을 수 없습니다"
                result = message
        except Exception as e:
            is_pass = 0
            message = f"❌ sar CPU 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def parse_value(self, output, key):
        """
        lscpu 출력에서 "key:" 로 시작하는 줄의 값을 반환
        """
        pattern = rf'^{re.escape(key)}\s*:\s*(.+)$'
        for line in output.splitlines():
            m = re.match(pattern, line)
            if m:
                return m.group(1).strip()
        raise ValueError(f"'{key}' 항목을 찾을 수 없습니다.")

    def count_online_cpus(self, cpu_list_str):
        """
        "0-3,5,7-9" 같은 문자열을 받아 실제 CPU 개수를 계산
        """
        total = 0
        for part in cpu_list_str.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                total += int(end) - int(start) + 1
            else:
                total += 1
        return total
    
    ### vmstat 점검 ####
    def vmstat_type1(self, stdout_data):
        try:
            is_success = 1
            lines = stdout_data.strip().splitlines()
            if len(lines) < 3:
                is_pass = 0
                message = "❌CPU 정보 파싱 실패: 'vmstat' 출력이 너무 짧습니다. "
                result = message
                return is_success, is_pass, result, message

            data_line = None
            for line in reversed(lines):
                parts_check = line.strip().split()
                if not parts_check:
                    continue

                num_count = sum(1 for part in parts_check if part.isdigit())
                if len(parts_check) >= 10 and (num_count / len(parts_check)) > 0.8:
                    data_line = line
                    break

            if not data_line:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 'vmstat' 출력에서 유효한 데이터 라인을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            parts = data_line.split()

            idle_percent = int(parts[-2])
            usage = 100 - idle_percent
            is_pass = 1 if usage <= self.inspection_criteria else 0
            if is_pass:
                message = f"✅ CPU 사용률: {usage}% (기준: {self.inspection_criteria}%)"
            else:
                message = f"❌ CPU 사용률: {usage}% (기준: {self.inspection_criteria}%) - 점검 필요"
        
            result = message
    
        except IndexError:
            is_pass = 0
            is_success = 0
            message = f"❌ vmstat CPU 평가 실패: 데이터 라인에서 CPU 정보를 찾을 수 없습니다."
            result = message
        except ValueError:
            is_pass = 0
            is_success = 0
            message = f"❌ vmstat CPU 평가 실패: CPU 유휴 값을 숫자로 변환할 수 없습니다."
            result = message
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ vmstat CPU 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def mpstat_type1(self, stdout_data):
        try:
            is_success = 1

            required_keys = ['usage', 'iowait', 'idle', 'interrupt']
            if not isinstance(self.inspection_criteria, dict) or not all(key in self.inspection_criteria for key in required_keys):
                is_pass = 0
                message = f"❌ 설정 오류: inspection_criteria가 올바르지 않습니다. 다음 키가 필요합니다: {required_kyes}"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()

            header_line = next((line for line in lines if '%usr' in line and 'CPU' in line), None)
            data_line = next((line for line in lines if 'all' in line.split()), None)

            if not header_line or not data_line:
                is_pass = 0
                message = f"❌ CPU 정보 파싱 실패: 'mpstat' 출력에서 헤더 또는 'all' CPU 데이터 라인을 찾을 수 없습니다.\n 'header_line': {header_line}\n 'data_line': {data_line}"
                result = message
                return is_success, is_pass, result, message

            header_parts = header_line.split()
            data_parts = data_line.split()

            val_usr, val_sys, val_iowait, val_irq, val_soft, val_idle = -1, -1, -1, -1, -1, -1

            try:
                h_idx_cpu = header_parts.index('CPU')
                d_idx_cpu = data_parts.index('all')
                offset = h_idx_cpu - d_idx_cpu

                val_usr = float(data_parts[header_parts.index('%usr') - offset])
                val_sys = float(data_parts[header_parts.index('%sys') - offset])
                val_iowait = float(data_parts[header_parts.index('%iowait') - offset])
                val_irq = float(data_parts[header_parts.index('%irq') - offset])
                val_soft = float(data_parts[header_parts.index('%soft') - offset])
                val_idle = float(data_parts[header_parts.index('%idle') - offset])

            except (ValueError, IndexError) as e:
                is_pass = 0
                message = f"❌ CPU 값 파싱 실패: 데이터 라인에서 값을 추출할 수 없습니다 - {e}. Data: {data_parts}, Header: {header_aprts}"
                result = message
                return is_success, is_pass, result, message

            failures = []
            usage = val_usr + val_sys
            if usage >= self.inspection_criteria['usage']:
                failures.append(f"CPU 사용률(usr+sys)이 {usage:.2f}%로 기준치({self.inspection_criteria['usage']:.2f}%) 이상입니다.")

            if val_iowait >= self.inspection_criteria['iowait']:
                failures.append(f"I/O 대기(iowait)가 {val_iowait:.2f}%로 기준치({self.inspection_criteria['iowait']:.2f}%) 이상입니다.")

            if val_idle < self.inspection_criteria['idle']:
                failures.append(f"CPU 유휴(idle)가 {val_idle:.2f}%로 기준치({self.inspection_criteria['idle']:.2f}%) 이상입니다.")

            interrupt_usage = val_irq + val_soft
            if interrupt_usage >= self.inspection_criteria['interrupt']:
                failures.append(f"인터럽트(irq+soft)가 {interrupt_usage:.2f}%로 기준치({self.inspection_criteria['interrupt']:.2f}%) 이상입니다.")

            if failures:
                is_pass = 0
                message = "❌ CPU 상태 점검 실패:\n" + "\n".join(failures)
            else:
                is_pass = 1
                message = f"✅ CPU 상태 양호. 사용률(usr+sys): {usage:.2f}%, I/O 대기: {val_iowait:.2f}%, 유휴: {val_idle:.2f}%, 인터럽트: {interrupt_usage:.2f}%"

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ mpstat CPU 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def prstat_type1(self, stdout_data):
        try:
            is_success = 1

            if not isinstance(self.inspection_criteria, dict) or 'process' not in self.inspection_criteria or 'total' not in self.inspection_criteria:
                is_pass = 0
                message = "❌ 설정 오류: inspection_criteria는 'process'와 'total' 키를 포함하는 딕셔너리여야 합니다."
                result = message
                return is_success, is_pass, result, message

            process_threshold = self.inspection_criteria['process']
            total_threshold = self.inspection_criteria['total']

            lines = stdout_data.strip().splitlines()

            failed_processes = []
            total_cpu_usage = 0.0
            process_lines_started = False

            header_line = None
            cpu_col_index = -1
            start_index = 0

            for i, line in enumerate(lines):
                if 'PID' in line and 'PROCESS/NLWP' in line:
                    header_index = i
                    header_parts = line.split()

                    try:
                        if 'CPU' in header_parts:
                            cpu_col_index = header_parts.index('CPU')
                        elif '%CPU' in header_parts:
                            cpu_col_index = header_parts.index('%CPU')
                        else:
                            raise ValueError
                    except ValueError:
                        is_pass = 0
                        message = "❌ CPU 정보 파싱 실패: 출력에서 'CPU' 컬럼을 찾을 수 없습니다."
                        result = message
                        return is_success, is_pass, result, message
                    break

            if header_index == -1:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 유효한 헤더 라인('PID', 'PROCESS/NLWP' 포함)을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            for line in lines[header_index + 1:]:
                line = line.strip()
                if not line or 'Total:' in line:
                    continue

                parts = line.split()
                
                if not parts or not parts[0].isdigit():
                    continue

                if len(parts) <= cpu_col_index:
                    continue

                try:
                    cpu_str = parts[cpu_col_index]
                    if '%' in cpu_str:
                        cpu_usage = float(cpu_str.replace('%',''))
                    else:
                        cpu_usage = float(cpu_str)

                    total_cpu_usage += cpu_usage

                    if cpu_usage > process_threshold:
                        pid = parts[0]
                        user = parts[1]
                        process_name = parts[-1]
                        failed_processes.append(f" - 프로세스 {process_name} (PID:'{pid}', USER:'{user}') CPU 사용률 {cpu_usage:.1f}% (기준: {process_threshold}%)")

                except (ValueError, IndexError):
                    continue

            failed_messages = []
            if failed_processes:
                failed_messages.append("다음 프로세스의 CPU 사용률이 기준치를 초과했습니다:\n" + "\n".join(failed_processes))

            if total_cpu_usage > total_threshold:
                failed_messages.append(f"시스템 전체 CPU 사용률이 {total_cpu_usage:.2f}%로 기준치({total_threshold}%)를 초과했습니다.")

            if failed_messages:
                is_pass = 0
                message = f"❌ CPU 상태 점검 필요:\n" + "\n".join(failed_messages)

            else:
                is_pass = 1
                message = f"✅ CPU 상태 양호. 전체 사용률: {total_cpu_usage:.2f}% (개발 프로세스 및 전체 사용률 기준치 충족)"

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ prstat CPU 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def psrinfo_v_type1(self, stdout_data):
        try:
            is_success = 1

            lines = stdout_data.strip().splitlines()

            if not lines:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 'psrinfo -v' 출력이 비어 있습니다."
                result = message
                return is_success, is_pass, result, message

            blocks = []
            current_block = []
            start_patterns = ('Status of processor', '프로세서', '가상 프로세서')

            for line in lines:
                if line.strip().startswith(start_patterns):
                    if current_block:
                        blocks.append("\n".join(current_block))
                    current_block = [line]
                elif current_block:
                    current_block.append(line)

            if current_block:
                blocks.append("\n".join(current_block))

            if not blocks:
                is_pass = 0
                message = "❌ CPU 정보 파싱 실패: 유효한 프로세서 블록을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_blocks = []
            online_keywords = ['on-line', '온라인']

            for block in blocks:
                is_online = any(keyword in block for keyword in online_keywords)

                if not is_online:
                    failed_blocks.append(block)

            if failed_blocks:
                is_pass = 0
                message = "❌ 다음 프로세서가 온라인 상태가 아닙니다:\n---\n" + "\n---\n".join(failed_blocks)
            else:
                is_pass = 1
                message = f"✅ 모든 프로세서({len(blocks)}개)가 온라인 상태입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ psrinfo CPU 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
