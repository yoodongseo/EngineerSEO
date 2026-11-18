#!/usr/bin/python
# -*- coding: utf-8 -*-

from .base_filter import BaseFilter, filter_result

class RHEL6ClusterFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        
        if "crm_mon" in self.command:
            is_success, is_pass, result, message = self.crm_type1(stdout_data)
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

    def crm_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            abnormal_states = []
            if not isinstance(self.inspection_criteria, dict):
                is_pass = 0
                message_list.append("❌ 불량 기준 점검 필요: 'inspection_criteria' 형식이 Dict 이 아닙니다.")
                message = "\n".join(message_list)
                result = message
                return is_success, is_pass, result, message

            ok_if_missing = bool(self.inspection_criteria.get("ok_if_command_missing", True))
            bad_tokens = [str(x).lower() for x in self.inspection_criteria.get("bad_tokens", ["maintenance", "offline", "stopped", "failed"])]

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌crm_mon 출력이 비어있습니다. (수집 실패)"
                result = message
                return is_success, is_pass, result, message

            low = stdout_data.lower()

            if ("not found" in low or "no such" in low or "찾을 수 없습니다" in low) and ok_if_missing:
                message = "✅crm_mon 명령어 미존재(미설치)"
                result = message
                return is_success, is_pass, result, message

            if "maintenance" in low:
                is_pass = 0
                message_list.appned("❌클러스터가 Maintenance 모드로 동작 중입니다.")

            lines = stdout_data.splitlines()
            in_node_list = False
            offline_nodes = []

            for line in lines:
                s = line.strip()
                if not s:
                    continue

                if s.startswith("Node List:"):
                    in_node_list = True
                    continue

                if in_node_list:
                    if s.startswith("Full List of Resources:") or s.endswith(":") and not s.startswith("*"):
                        in_node_list = False

                    if "offline:" in s.lower():
                        offline_nodes.append(s)

            if offline_nodes:
                is_pass = 0
                message_list.append("❌ Offline 노드 존재:\n" + "\n".join(offline_nodes))

            in_res = False
            bad_res_lines = []

            for line in lines:
                s = line.strip()
                if not s:
                    continue

                if s.startswith("Full List of Resources:"):
                    in_res = True
                    continue

                if in_res:
                    sl = s.lower()
                    if "stopped" in sl or "failed" in sl:
                        bad_res_lines.append(s)

            if bad_res_lines:
                is_pass = 0
                message_list.append("❌비정상 리소스 상태 감지:\n" + "\n".join(bad_res_lines))

            extra_hits = [t for t in bad_tokens if t in low]
            if extra_hits and is_pass == 1:
                is_pass = 0
                message_list.append(f"❌비정상 키워드 감지: {sorted(set(extra_hits))}")
 
            if is_pass == 1:
                message = f"✅ Cluster 상태가 정상입니다."
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 Cluster 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 클러스터 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
