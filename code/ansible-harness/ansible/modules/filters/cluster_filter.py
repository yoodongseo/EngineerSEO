#!/usr/bin/python
# -*- coding: utf-8 -*-

from .base_filter import BaseFilter, filter_result

class ClusterFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        
        if "cmviewcl" in self.command:
            is_success, is_pass, result, message = self.cmviewcl_type1(stdout_data)
        elif "lssrc -g cluster" in self.command:
            is_success, is_pass, result, message = self.line_check_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': "서비스 실행 여부",
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def cmviewcl_type1(self, stdout_data):
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
                message = f"❌ 명령어 실패: 'command not found' 클러스터 구성여부 확인 필요"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            cluster_status_line_found = False
            node_section = False
            package_section = False

            for line in lines:
                stripped_line = line.strip().lower()

                if "cluster status:" in stripped_line:
                    cluster_status_line_found = True
                    if "up" not in stripped_line:
                        is_pass = 0
                        message_list.append(f"❌ Cluster Status가 'up' 이 아닙니다: {line}")
                    for state in abnormal_states:
                        if state in stripped_line:
                            is_pass = 0
                            message_list.append(f"❌ Cluster Status의 비정상 키워드 '{state}' 발견: {line}")
                            break
                
                if "node status" in stripped_line:
                    node_section = True
                    package_section = False
                    continue
                if "package status" in stripped_line:
                    node_section = False
                    package_section = True
                    continue
                if "cluster status" in stripped_line and not stripped_line.startswith("cluster status:"):
                    continue
                if "node name" in stripped_line and (node_section or package_section):
                    continue
                if "package name" in stripped_line and package_section:
                    continue

                if node_section and stripped_line:
                    parts = stripped_line.split()
                    if len(parts) >= 2:
                        node_name = parts[0]
                        node_status = parts[1]

                        if node_status != "up":
                            is_pass = 0
                            message_list.append(f"❌ 노드 '{node_name}' 가 'up' 이 아닙니다: {node_status}")

                        for state in abnormal_states:
                            if state in stripped_line:
                                is_pass = 0
                                message_list.append(f"❌ Cluster Status의 비정상 키워드 '{state}' 발견: {line}")
                                break

                if package_section and stripped_line:
                    parts = stripped_line.split()
                    if len(parts) >= 3:
                        package_name = parts[0]
                        package_status = parts[2]

                        if package_status != "running":
                            is_pass = 0
                            message_list.append(f"❌ 패키지 '{package_name}' 가 'running' 이 아닙니다: {package_status}")

                        for state in abnormal_states:
                            if state in stripped_line:
                                is_pass = 0
                                message_list.append(f"❌ Cluster Status의 비정상 키워드 '{state}' 발견: {line}")
                                break

            if not cluster_status_line_found:
                is_pass = 0
                message_list.insert(0, f"❌ 'cmviewcl' 출력에서 Cluster Status 데이터를 찾을 수 없습니다. (출력값:{str(stdout_data).strip()[:200]}...)")
  

            if is_pass == 1:
                message = f"✅ Cluster 상태가 정상입니다."
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 Cluster 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 클러스터 이중화 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def line_check_type1(self, stdout_data):
        """라인 별 inspection_criteria 키워드를 검색하고, 명령어 자체의 오류도 확인합니다."""
        try:
            is_success = 1

            if not stdout_data or not stdout_data.strip():
                is_pass = 0
                message = "❌ 명령어 결과가 없습니다."
                result = message
                return is_success, is_pass, result, message

            first_line = stdout_data.strip().splitlines()[0].strip()
            if first_line.startswith(('0513-086')):
                is_pass = 1
                message = f"✅ 클러스터 미구성 상태입니다:\n {first_line}"
                result = message
                return is_success, is_pass, result, message

            if not self.inspection_criteria:
                is_pass = 0
                message = "❌ 검사할 키워드가 지정되지 않았습니다."
                result = message
                return is_success, is_pass, result, message

            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(c).lower() for c in self.inspection_criteria]
            else:
                criteria_list = [c.strip().lower() for c in str(self.inspection_criteria).split(',')]

            failed_lines = []
            for line in stdout_data.strip().splitlines():
                line_lower = line.lower()
                for keyword in criteria_list:
                    if keyword not in line_lower:
                        failed_lines.append(line.strip())
                        break
            
            if failed_lines:
                is_pass = 0
                criteria_str = ", ".join(criteria_list)
                message = f"❌ Cluster 점검 필요: ({criteria_str}) 상태가 아닌 시스템.\n" + "\n".join(failed_lines)
            else:
                is_pass = 1
                message = "✅ 모든 시스템이 정상입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Cluster 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
