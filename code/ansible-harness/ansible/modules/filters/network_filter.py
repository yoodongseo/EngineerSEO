from .base_filter import BaseFilter, filter_result
import re
import sys

class NetworkFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""

        if "lanscan" in self.command:
            is_success, is_pass, result, message = self.lanscan_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        # # 현재 로직 상 명령어는 필터를 무조건 타야 하므로 단지 실행만 하고 반합하는 필터
        # is_success, is_pass, result, message = self.action(stdout_data)

        return {
            'message': result,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success
        }
    
    def action(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1

            keywords_to_find = [kw.strip().lower() for kw in self.inspection_criteria(',') if kw.strip()]

            if not keywords_to_find:
                is_pass = 1
                is_success = 1
                message = "✅success action"
                result = message
                return is_success, is_pass, result, message

            found_keywords = set()

            for line in stdout_data.splitlines():
                lower_line = line.lower()
                for keyword in keywords_to_find:
                    if keyword in lower_line:
                        found_keywords.add(lower_line)
                        break
            
            if found_keywords:
                is_pass = 0
                is_success = 0
                message = f"❌ 명령어 결과 확인 필요합니다. \n {', '.join(sorted(list(found_keywords)))}"
            else:
                is_pass = 1
                message = "✅ 명령어 결과가 정상입니다."
            
            result = message
        
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ fail action: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def lanscan_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            critical_interfaces = []

            if isinstance(self.inspection_criteria, list):
                critical_interfaces = [str(item).lower() for item in self.inspection_criteria]

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "Hardware Station" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Hardware Station' 를 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()

            data_start_index = -1

            for i, line in enumerate(lines):
                if line.strip().startswith("Path"):
                    data_start_index = i + 1
                    break

            if data_start_index == -1 or data_start_index >= len(lines):
                is_pass = 0
                message = f"❌ 'lanscan' 명령어 출력에서 데이터 시작 지점을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            data_lines = lines[data_start_index:]

            active_interface_count = 0
            total_physical_nic_count = 0

            for line in lines:
                stripped_line = line.strip()

                if not stripped_line:
                    continue
  
                parts = stripped_line.split()

                if len(parts) >= 6 and (parts[4].startswith("lan") or parts[4].startswith("LinkAgg")):
                    interface_name = parts[4]
                    state = parts[3].upper()

                    if interface_name.startswith("lan") and not interface_name.startswith("LinkAgg"):
                        total_physical_nic_count += 1

                    if state == "UP":
                        active_interface_count += 1

                    elif state == "DOWN" or state == "UNKNOWN":
                        if not critical_interfaces or interface_name.lower() in critical_interfaces:
                            is_pass = 0
                            message_list.append(f"❌ 사용 중인 인터페이스 '{interface_name}' 상태 점검 필요: '{state}' ")
                        else:
                            message_list.append(f"비활성/미사용 인터페이스 '{interface_name}' 상태: '{state}'.")

            if total_physical_nic_count > 0 and active_interface_count == 0:
                is_pass = 0
                message_list.insert(0, f"❌ 모든 물리 NIC({total_physical_nic_count}개) 가 DOWN 상태입니다.")
                
            if is_pass == 1:
                message = f"✅ 네트워크 인터페이스 상태가 정상입니다. ({active_interface_count}개 활성 인터페이스)"
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 네트워크 인터페이스 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message
        
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ fail action: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
