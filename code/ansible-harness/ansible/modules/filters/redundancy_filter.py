from .base_filter import BaseFilter, filter_result
import re

class RedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "lsvg -l rootvg" in self.command:
            is_success, is_pass, result, message = self.lsvg_type1(stdout_data)
        elif "ioscan -fnC fc" in self.command:
            is_success, is_pass, result, message = self.ioscan_fc_type1(stdout_data)
        elif "lanscan" in self.command:
            is_success, is_pass, result, message = self.lanscan_type2(stdout_data)
        elif "mdadm --detail" in self.command:
            is_success, is_pass, result, message = self._linux_mdadm_type1(stdout_data)
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

    def lsvg_type1(self, stdout_data):
        try:
            is_success = 1
            failed_lvs = []

            expected_state = self.inspection_criteria

            lines = stdout_data.strip().splitlines()

            if not lines:
                is_pass = 0
                message = "❌ 명령어 출력이 비어 있습니다."
                result = message
                return is_success, is_pass, result, message

            header = None
            header_index = -1

            for i, line in enumerate(lines[:3]):
                if 'LV STATE' in line:
                    header = line
                    header_index = i
                    break

            if header is None:
                is_pass = 0
                message = "❌ 'LV STATE' 컬럼을 찾을 수 없습니다. 출력 방식이 변경되었습니다."
                result = message
                return is_success, is_pass, result, message

            try:
                lv_state_start_index = header.find("LV STATE")
            except ValueError:
                is_pass = 0
                message = "❌ 'LV STATE' 컬럼을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            for line in lines[header_index + 1:]:
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                if len(stripped_line) > lv_state_start_index:
                    lv_state_part = stripped_line[lv_state_start_index:].strip()
                    lv_state = lv_state_part.split()[0]

                    if "open/" in lv_state and expected_state not in lv_state:
                        failed_lvs.append(stripped_line)

                else:
                    continue

            if failed_lvs:
                is_pass = 0
                message = f"❌ 다음 논리 볼륨의 상태가  '{expected_state}'가 아닙니다:\n" + "\n".join(failed_lvs)
            else:
                is_pass = 1
                message = f"✅ 모든 논리 볼륨이 정상 상태('{expected_state}')입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK 이중화 상태 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def ioscan_fc_type1(self, stdout_data):
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
            fc_port_count = 0
            data_started = False
            for line in lines:
                stripped_line = line.strip()

                if not data_started and stripped_line.startswith("========="): # 헤더 구분선 이후부터 데이터 파싱 처리
                    data_started = True
                    continue
                if not data_started or not stripped_line: #데이터 시작 전 라인 및 빈 칸 건너뛰기
                    continue

                fc_match = re.match(r"fc\s+\d", stripped_line)
                if fc_match:
                    fc_port_count += 1

                    if "CLAIMED" not in stripped_line:
                        is_pass = 0
                        message_list.append(f"❌ FC 포트 '{fc_match.group(0)}' 의 S/W State가 'CLAIMED'가 아님 (또는 찾을 수 없음): {stripped_line}")

                    for abnormal_state in abnormal_states:
                        if abnormal_state in stripped_line.upper():
                            is_pass = 0
                            message_list.append(f"❌ FC 포트 '{fc_match.group(0)}' 에서 비정상 상태 '{abnormal_states}' 발견: {stripped_line}")
                            break

            if fc_port_count < 2:
                is_pass = 0
                if fc_port_count == 0:
                    message_list.append(f"❌ FC 포트가 인식되지 않았습니다. (이중화 미구성)")
                else:
                    message_list.append(f"❌ FC 포트가 1개만 인식되었습니다. (이중화 미구성)")

            if is_pass == 1:
                message = f"✅ FC 포트 상태가 정상입니다. ({fc_port_count}개 포트 인식)"
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 FC 포트 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def lanscan_type2(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            critical_interfaces = []

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            # 각 인터페이스 블록 분리
            interface_block = re.split(r'(?m)^PPA Number\s*=\s*(\d+)', stdout_data)[1:]

            if not interface_block:
                is_pass = 0
                message_list.append(f"❌ LinkAgg 인터페이스 정보를 찾을 수 없습니다.")

            for i in range(0, len(interface_block), 2):
                ppa_number = interface_block[i].strip()
                block_content = interface_block[i+1]

                admin_status_line = ""
                oper_status_line = ""
                
                admin_status_match = re.search(r'Administration Status(?:\s*\(value\))?\s*=\s*(.+)', block_content)
                if admin_status_match:
                    admin_status_line = admin_status_match.group(0).strip().lower()
                if "up" not in admin_status_line:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Administration Status가 'UP'이 아닙니다. ")

                operation_status_match = re.search(r'Operation Status(?:\s*\(value\))?\s*=\s*(.+)', block_content)
                if operation_status_match:
                    operation_status_line = operation_status_match.group(0).strip().lower()
                if "up" not in operation_status_line:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Operation Status가 'UP'이 아닙니다. ")


                inbound_errors_match = re.search(r'Inbound Errors\s*=\s*(\d+)', block_content)
                inbound_errors = int(inbound_errors_match.group(1)) if inbound_errors_match else -1 # -1의 경우 파싱 실패

                outbound_errors_match = re.search(r'Outbound Errors\s*=\s*(\d+)', block_content)
                outbound_errors = int(outbound_errors_match.group(1)) if outbound_errors_match else -1 # -1의 경우 파싱 실패

                inbound_discards_match = re.search(r'Inbound Discards\s*=\s*(\d+)', block_content)
                inbound_discards = int(inbound_discards_match.group(1)) if inbound_discards_match else -1 # -1의 경우 파싱 실패

                outbound_discards_match = re.search(r'Outbound Discards\s*=\s*(\d+)', block_content)
                outbound_discards = int(outbound_discards_match.group(1)) if outbound_discards_match else -1 # -1의 경우 파싱 실패

                if inbound_errors > 0:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Inbound Error 값 {inbound_errors}이(가) 0이 아닙니다.")
                    
                if outbound_errors > 0:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Outbound Error 값 {outbound_errors}이(가) 0이 아닙니다.")

                if inbound_discards > 0:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Inbound Discards 값 {inbound_discards}이(가) 0이 아닙니다.")

                if outbound_discards > 0:
                    is_pass = 0
                    message_list.append(f"❌ PPA {ppa_number} Outbound Discards 값 {outbound_discards}이(가) 0이 아닙니다.")

            if is_pass == 1:
                message = f"✅ 모든 LinkAgg 인터페이스 상태 및 에러 값이 정상입니다.)"
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 NIC 이중화 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ NIC 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def _linux_mdadm_type1(self, stdout_data):
        is_success = 1

        if not stdout_data.strip():
            message = "✅ RAID(mdadm)가 구성되어 있지 않습니다."
            is_pass = 1
            result = message
            return is_success, is_pass, result, message

        try:
            device_blocks = stdout_data.strip().split('/dev/md')
            failed_devices_info = []
            warning_messages = []
            current_is_pass = 1

            for block in device_blocks:
                if not block.strip() or ':' not in block.split('\n')[0]:
                    continue

                lines = block.strip().split('\n')
                device_name = f"/dev/md{lines[0].split(':')[0].strip()}"
                details = {}

                for line in lines[1:]:
                    if ':' in line:
                        parts = line.split(':', 1)
                        key = parts[0].strip()
                        value = parts[1].strip()
                        details[key] = value

                state = details.get('State', 'unknown').lower()
                failed_devices = int(details.get('Failed Devices', '0'))
                raid_devices = int(details.get('Raid Devices', '0'))
                active_devices = int(details.get('active_devices', '0'))
                working_devices = int(details.get('working_devices', '0'))
                spare_devices = int(details.get('spare_devices', '0'))

                device_errors = []

                if 'clean' not in state:
                    device_errors.append(f"RAID 상태가 비정상({details.get('State', '알 수 없음')})")
                if failed_devices > 0:
                    device_errors.append(f"실패한 장치({failed_devices}개) 발견")
                if active_devices != raid_devices:
                    device_errors.append(f"ghkftjd wkdcl tn ({active_devices}개)가 RAID 장치 수({raid_devices}개)와 불일치")
                if working_devices != raid_devices:
                    device_errors.append(f"정상 동작 장치 수 ({working_devices}개)가 RAID 장치 수({raid_devices}개)와 불일치")

                if device_errors:
                    current_is_pass = 0
                    failed_devices_info.append(f"❌ {device_name}: {', '.join(device_errors)}")

                if spare_devices == 0:
                    warning_messages.append(f"⚠ {device_name}: 스페어 디스크가 없어 자동 복구가 불가능할 수 있습니다. (권고 사항)")

            if current_is_pass:
                is_pass = 1
                message = "✅ 모든 RAID 장치가 정상 상태입니다."
                if warning_messages:
                    message += "\n" + "\n".join(warning_messages)
            else:
                is_pass = 0
                message = "RAID 장치 점검 결과, 다음과 같은 문제가 발견되엇습니다:\n" + "\n".join(failed_devices_info)
                if warning_messages:
                    message += "\n" + "\n".join(warning_messages)

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ DISK 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
