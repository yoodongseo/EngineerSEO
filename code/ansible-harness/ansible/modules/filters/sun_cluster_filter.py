#!/usr/bin/python
# -*- coding: utf-8 -*-

from .base_filter import BaseFilter, filter_result

class SunClusterFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        
        if "scstat" in self.command:
            is_success, is_pass, result, message = self.scstat_type1(stdout_data)
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

    def scstat_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            abnormal_states = []
            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message_list.append("❌ 불량 기준 점검 필요: 'inspection_criteria' 형식이 Dict 이 아닙니다.")
                message = "\n".join(message_list)
                result = message
                return is_success, is_pass, result, message

            node_ok = str(self.inspection_criteria.get("node_ok", "online")).lower()
            path_ok = str(self.inspection_criteria.get("path_ok", "online")).lower()
            rg_ok = str(self.inspection_criteria.get("rg_ok", "online")).lower()
            nic_ok = str(self.inspection_criteria.get("nic_ok", "online")).lower()

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌scstat 출력이 비어있습니다. (수집 실패)"
                result = message
                return is_success, is_pass, result, message

            low = stdout_data.lower()

            if "not found" in low or "없음" in low:
                message = "✅scstat 명령어 미존재(클러스터 존재여부 확인 필요)"
                result = message
                return is_success, is_pass, result, message

            section = None
            counts = {"nodes": 0, "paths": 0, "rgs": 0, "nics": 0}

            for raw in stdout_data.splitlines():
                line = raw.strip()
                if not line:
                    continue

                l = line.lower()

                if "cluster nodes" in l:
                    section = "nodes"; continue
                if "cluster transport paths" in l:
                    section = "paths"; continue
                if "resource groups" in l:
                    section = "rgs"; continue
                if "network interfaces" in l:
                    section = "nics"; continue
    
                if l.startswith("---") or set(l) <= set("- "):
                    continue
                if "status" in l and ("node name" in l or "source node" in l or "group name" in l or "interface name" in l):
                    continue
    
                parts = line.split()
                if not parts or section is None:
                    continue
    
                if section == "nodes":
                    if len(parts) >= 2:
                        counts["nodes"] += 1
                        status = parts[-1].lower()
                        if status != node_ok:
                            is_pass = 0
                            message_list.append(f"❌Node {parts[0]}: {status}")
    
                elif section == "paths":
                    if len(parts) >= 4:
                        counts["paths"] += 1
                        status = " ".join(parts[-2:]).lower()
                        if status != path_ok:
                            is_pass = 0
                            message_list.append(f"❌ Path {parts[0]} ->{parts[1]}: {status}")
    
                elif section == "rgs":
                    if len(parts) >= 3:
                        counts["rgs"] += 1
                        status = parts[-1].lower()
                        if status != rg_ok:
                            is_pass = 0
                            message_list.append(f"❌ RG {parts[0]}({parts[1]}): {status}")
    
                elif section == "nics":
                    if len(parts) >= 3:
                        counts["nics"] += 1
                        status = parts[-1].lower()
                        if status != nic_ok:
                            is_pass = 0
                            message_list.append(f"❌ NIC {parts[0]}({parts[1]}): {status}")
            
            if counts["nodes"] == 0:
                is_pass = 0
                message = f"❌ scstat 클러스터 정보 수집 실패: Cluster Nodes 데이터 없음"
                result = message
                return is_success, is_pass, result, message

            if is_pass == 1:
                message = f"✅ scstat 클러스터 정상 확인"
            else:
                message = "\n".join(message_list)
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 클러스터 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
