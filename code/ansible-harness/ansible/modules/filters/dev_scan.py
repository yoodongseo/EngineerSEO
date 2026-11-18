from .base_filter import BaseFilter, filter_result
import re

class DevscanFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        if "machinfo" in self.command:
            is_success, is_pass, result, message = self.machinfo_type1(stdout_data)
        elif "lsdev -Cc memory" in self.command:
            is_success, is_pass, result, message = self.lsdev_type1(stdout_data)
        elif "ioscan -fnC processor" in self.command:
            is_success, is_pass, result, message = self.ioscan_type1(stdout_data)
        elif "lsdev -Cc processor" in self.command:
            is_success, is_pass, result, message = self.lsdev_type2(stdout_data)
        elif "ioscan -fnC disk" in self.command:
            is_success, is_pass, result, message = self.ioscan_fc_type2(stdout_data)
        elif "lsdev -Cc disk" in self.command:
            is_success, is_pass, result, message = self.lsdev_type1(stdout_data)
        elif "lsblk" in self.command:
            is_success, is_pass, result, message = self.lsblk_type1(stdout_data)
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

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or not("Memory Information" in stdout_data or "Memory: " in stdout_data): 
                is_pass = 0
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
            lines = stdout_data.strip().splitlines()
            if not lines:
                is_pass = 0
                message = f"❌ Disk  인식 여부  점검 실패: '{self.command}' 명령어 출력이 없습니다."
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
                message = "❌ Disk 인식 여부  파싱 실패: 유효한 메모리 장치 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            if failed_devices:
                is_pass = 0
                message = f"❌ 일부 Disk 장치가 비정상 상태입니다. {', '.join(failed_devices)}. (기준: {self.inspection_criteria})"
            else:
                is_pass = 1
                message = f"✅ 모든 Disk  장치 ({total_devices}개)가 정상 상태('{self.inspection_criteria}')입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ lsdev  Disk 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    ### ioscan 점검 ###
    def ioscan_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not stdout_data or "Description" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실행 실패: '{str(stdout_data).strip()[:200]}..."
                result = message
                return is_success, is_pass, result, message

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실행 실패: '{str(stdout_data).strip()[:200]}..."
                result = message
                return is_success, is_pass, result, message


            processor_count = 0

            abnormal_keywords = ["UNCLAIMED", "NO_HW", "ERROR"]

            lines = stdout_data.splitlines()

            data_started = False
            for line in lines:
                stripped_line = line.strip()

                if not data_started and stripped_line.startswith("======"):
                    data_started = True
                    continue
                if not data_started:
                    continue
                if not stripped_line:
                    continue

                for keyword in abnormal_keywords:
                    if keyword in stripped_line:
                        is_pass = 0
                        message_list.append(f"❌ 비정상 키워드 '{keyword}' 발견: {stripped_line}")
                        break

                processor_match = re.match(r"processor\s+\d+", stripped_line)
                if processor_match:
                    processor_count += 1
                    if "CLAIMED" not in stripped_line:
                        is_pass = 0
                        message_list.append(f"❌ processor 항목 중 S/W state가 'CLAIMED' 가 아님: {stripped_line}")

            if processor_count == 0:
                is_pass = 0
                message_list.insert(0, "❌ processor 항목이 발견되지 않았습니다.")

            if is_pass == 1:
                message = f"✅ CPU(processor) 상태가 정상입니다. ({processor_count}개 processor 항목 확인)"
            else:
                message = f"\n".join(message_list) if message_list else "❌ 알 수 없는 오류로 CPU 점검 실패."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ ioscan CPU 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def lsdev_type2(self, stdout_data):
        try:
            is_success = 1
            lines = stdout_data.strip().splitlines()
            if not lines:
                is_pass = 0
                message = "❌ CPU 코어 상태 점검 실패: 'lsdev -Cc processor' 명령어 출력이 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_procs = []
            total_procs = 0
            # inspection_criteria를 소문자로 반환하여 비교
            expected_status = self.inspection_criteria.lower()

            for line in lines:
                line_content = line.strip()
                if line_content.lower().startswith('proc'):
                    total_procs += 1
                    parts = line_content.split()
                    if len(parts) >= 2:
                        proc_name, status = parts[0], parts[1]
                        if status.lower() != expected_status:
                            failed_procs.append(f"{proc_name}({status})")
                    else:
                        failed_procs.append(f"파싱 실패:'{line_content}'")

            if total_procs == 0:
                is_pass = 0
                message = "❌ CPU 코어 정보 파싱 실패: 유효한 프로세서 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            if failed_procs:
                is_pass = 0
                message = f"❌ 일부 CPU 코어가 비정상 상태입니다. {', '.join(failed_procs)}. (기준: {self.inspection_criteria})"
            else:
                is_pass = 1
                message = f"✅ 모든 CPU 코어 ({total_procs}게)가 정상 상태('{self.inspection_criteria}')입니다."

            result = message

        except Exception as e:
           is_pass = 0
           is_success = 0
           message = f"❌ lsdev CPU 코어 평가 실패: {str(e)}"
           result = message

        return is_success, is_pass, result, message

    def ioscan_fc_type2(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            abnormal_states = []
            if isinstance(self.inspection_criteria, list):
                abnormal_states = [str(item).upper() for item in self.inspection_criteria]
            else:
                is_pass = 0
                message_list.append("❌ 불량 기준 점검 필요: 'inspection_criteria' 형식이 List가 아닙니다.")
                message = "\n".join(message_list)
                result = message
                return is_success, is_pass, result, message

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "Class" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Class' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            disk_found_count = 0
            data_started = False
            for line in lines:
                stripped_line = line.strip()

                if not data_started and stripped_line.startswith("========="): # 헤더 구분선 이후부터 데이터 파싱 처리
                    data_started = True
                    continue
                if not data_started or not stripped_line: #데이터 시작 전 라인 및 빈 칸 건너뛰기
                    continue

                disk_match = re.match(r"disk\s+\d", stripped_line)
                if disk_match:
                    disk_found_count += 1

                    if "CLAIMED" not in stripped_line:
                        is_pass = 0
                        message_list.append(f"❌ 디스크 '{disk_match.group(0)}' 의 S/W State가 'CLAIMED'가 아님 (또는 찾을 수 없음): {stripped_line}")
                    for abnormal_state in abnormal_states:
                        if abnormal_state in stripped_line.upper():
                            is_pass = 0
                            message_list.append(f"❌ 디스크 '{disk_match.group(0)}' 에서 비정상 상태 '{abnormal_states}' 발견: {stripped_line}")
                            break

            if disk_found_count == 0:
                is_pass = 0
                if disk_found_count == 0:
                    message_list.append(f"❌ 'disk' 클래스 항목이 존재하지 않습니다. (이중화 미구성)")

            if is_pass == 1:
                message = f"✅ 디스크 상태가 정상입니다. ({disk_found_count}개 포트 인식)"
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 디스크 인식 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK 인식여부 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def lsblk_type1(self, stdout_data):
        try:
            is_success = 1

            if not stdout_data.strip():
                is_pass = 0
                message = "❌ 'lsblk' 명령어 출력이 없습니다. 디스크가 정상적으로 인식되지 않았을 수 있습니다."
            else:
                is_pass = 1
                message = "✅ 'lsblk' 명령어가 성공적으로 실행되었으며, 디스크가 정상적으로 인식되었습니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK 인식여부 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
