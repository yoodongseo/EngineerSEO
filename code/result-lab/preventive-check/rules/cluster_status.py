from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class ClusterStatusRule:
    RULE_KEY = "cluster_status"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def allow_not_found(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        return "Cluster 데몬 정상 상태"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip().lower()

        if "get-service clussvc" in command or "get-clusternode" in command or "get-clusterresource" in command:
            if os_type == "windows":
                return cls._run_windows_cluster_status(params, stdout_data)
            return build_unsupported_command(params)

        if "crm_mon" in command:
            if os_type in ("linux", "linux5"):                
                return cls._run_crm_mon(params, stdout_data)
            return build_unsupported_command(params)

        if "lssrc -g cluster" in command:
            if os_type == "aix":
                return cls._run_lssrc_aix(params, stdout_data)
            return build_unsupported_command(params)

        if "scstat" in command:
            if os_type == "solaris":                    
                return cls._run_scstat_solaris(params, stdout_data)
            return build_unsupported_command(params)

        if "cmviewcl" in command:
            if os_type == "hpux":
                return cls._run_cmviewcl_hpux(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _run_windows_cluster_status(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            if not output:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "클러스터 상태 출력이 비어 있습니다.",
                }

            criteria = params.get("inspection_criteria") or {}
            if not isinstance(criteria, dict):
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "inspection_criteria는 Dict 형식이어야 합니다.",
                }

            ok_if_missing = bool(criteria.get("ok_if_command_missing", True))
            bad_tokens = [
                str(token).strip().lower()
                for token in str(criteria.get("errormsg", "Down,Paused,Offline,Failed")).split(",")
                if str(token).strip()
            ]

            lowered = output.lower()
            no_cluster_markers = [
                "\ud574\ub2f9 \uc5c6\uc74c",
                "\ud574\ub2f9\uc5c6\uc74c",
                "not applicable",
                "cannot find any service with service name 'clussvc'",
                "service cannot be found",
                "no service found for given name",
                "get-service :",
            ]
            if any(marker in lowered for marker in no_cluster_markers):
                if ok_if_missing:
                    return {
                        "is_success": 1,
                        "is_pass": -1,
                        "reason_text": output,
                    }
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": "Cluster 상태",
                    "judgement_text": "점검 필요",
                    "detail_lines": [output],
                    "criteria_items": [f"비정상 상태 미검출: {', '.join(bad_tokens)}"],
                }

            non_prompt_lines = []
            for raw_line in output.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("[") or line == "---":
                    continue
                if line.startswith("C:\\") or line.startswith("PS ") or line.startswith(">>"):
                    continue
                non_prompt_lines.append(line)

            if ok_if_missing and non_prompt_lines and all(":" not in line for line in non_prompt_lines):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "\n".join(non_prompt_lines),
                }

            detail_lines = []
            failed_lines = []
            for raw_line in output.splitlines():
                line = raw_line.strip()
                if not line or line.startswith("[") or line == "---":
                    continue
                if ":" not in line:
                    continue
                detail_lines.append(line)
                line_lower = line.lower()
                for token in bad_tokens:
                    if token and token in line_lower:
                        failed_lines.append(f"비정상 상태 감지: {line}")
                        break

            if not detail_lines:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "클러스터 노드/서비스 상태 데이터를 찾을 수 없습니다.",
                }

            return {
                "is_success": 1,
                "is_pass": 0 if failed_lines else 1,
                "check_target": "Cluster 상태",
                "criteria_items": [f"비정상 상태 미검출: {', '.join(bad_tokens)}"],
                "judgement_text": "점검 필요" if failed_lines else "정상",
                "detail_lines": detail_lines + failed_lines,
            }

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Windows Cluster 평가 실패: {err}",
            }

    @classmethod
    def _run_crm_mon(cls, params, stdout_data):
        try:
            output = (stdout_data or "")
            low = output.lower()

            criteria = params.get("inspection_criteria")
            if criteria is None:
                criteria = {}

            if not isinstance(criteria, dict):
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "점검 기준 형식이 올바르지 않습니다. inspection_criteria는 Dict 여야 합니다.",
                }

            ok_if_missing = bool(criteria.get("ok_if_command_missing", True))
            bad_tokens = [
                str(x).strip().lower()
                for x in criteria.get(
                    "bad_tokens",
                    ["maintenance", "offline", "stopped", "failed"],
                )
                if str(x).strip()
            ]

            missing_markers = ["command not found", "not found", "no such", "crm_mon unavailable", "찾을 수 없습니다", "명령을 찾을 수 없습니다"]
            if ok_if_missing and any(marker in low for marker in missing_markers):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "crm_mon 명령어 미존재(미설치)",
                }

            message_list = []
            is_pass = 1

            if "maintenance" in low:
                is_pass = 0
                message_list.append("클러스터가 Maintenance 모드로 동작 중입니다.")

            lines = str(output).splitlines()

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
                    if s.startswith("Full List of Resources:") or (s.endswith(":") and not s.startswith("*")):
                        in_node_list = False

                    if "offline:" in s.lower():
                        offline_nodes.append(s)

            if offline_nodes:
                is_pass = 0
                message_list.append("Offline 노드 존재")
                message_list.extend(offline_nodes)

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
                message_list.append("비정상 리소스 상태 감지")
                message_list.extend(bad_res_lines)

            extra_hits = [token for token in bad_tokens if token and token in low]
            if extra_hits and is_pass == 1:
                is_pass = 0
                message_list.append(f"비정상 키워드 감지: {sorted(set(extra_hits))}")

            criteria_items = []
            if bad_tokens:
                criteria_items.append(f"비정상 토큰({', '.join(sorted(set(bad_tokens)))}) 미포함")
            if ok_if_missing:
                criteria_items.append("명령어 미설치 시 제외")

            if is_pass == 1:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": "Cluster 상태",
                    "criteria_items": criteria_items,
                    "judgement_text": "정상",
                    "detail_lines": ["Cluster 상태가 정상입니다."],
                }

            detail_lines = message_list or [f"알 수 없는 오류로 Cluster 점검에 실패했습니다. (출력값:{str(output).strip()[:200]}...)" ]
            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "Cluster 상태",
                "criteria_items": criteria_items,
                "judgement_text": "점검 필요",
                "detail_lines": detail_lines,
            }

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"클러스터 평가 실패: {err}",
            }

    @classmethod
    def _run_scstat_solaris(cls, params, stdout_data):
        try:
            output = (stdout_data or "")
            low = output.lower()

            criteria = params.get("inspection_criteria")
            if not isinstance(criteria, dict) or not criteria:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "점검 기준 형식이 올바르지 않습니다. inspection_criteria는 Dict 여야 합니다.",
                }

            ok_if_missing = bool(criteria.get("ok_if_command_missing", True))
            node_ok = str(criteria.get("node_ok", "online")).strip().lower()
            path_ok = str(criteria.get("path_ok", "path online")).strip().lower()
            rg_ok = str(criteria.get("rg_ok", "online")).strip().lower()
            nic_ok = str(criteria.get("nic_ok", "online")).strip().lower()

            if not str(output).strip():
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": "Cluster 상태",
                    "criteria_items": [
                        f"Node 상태 {node_ok}",
                        f"Path 상태 {path_ok}",
                        f"RG 상태 {rg_ok}",
                        f"NIC 상태 {nic_ok}",
                    ],
                    "judgement_text": "점검 필요",
                    "detail_lines": ["scstat 출력이 비어있습니다. (수집 실패)"],
                }

            if ok_if_missing and ("not found" in low or "없음" in output):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "scstat 명령어 미존재(클러스터 존재여부 확인 필요)",
                }

            shell_error_markers = ["ksh: scstat", "scstat:", "command not found", "not found"]
            if ok_if_missing and any(marker in low for marker in shell_error_markers):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "Solaris Cluster 구성이 확인되지 않았습니다.",
                }

            section = None
            counts = {"nodes": 0, "paths": 0, "rgs": 0, "nics": 0}
            message_list = []
            is_pass = 1

            for raw_line in output.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                lowered = line.lower()

                if "cluster nodes" in lowered:
                    section = "nodes"
                    continue
                if "cluster transport paths" in lowered:
                    section = "paths"
                    continue
                if "resource groups" in lowered:
                    section = "rgs"
                    continue
                if "network interfaces" in lowered:
                    section = "nics"
                    continue

                if lowered.startswith("---") or set(lowered) <= set("- "):
                    continue
                if "status" in lowered and (
                    "node name" in lowered
                    or "source node" in lowered
                    or "group name" in lowered
                    or "interface name" in lowered
                ):
                    continue

                parts = line.split()
                if not parts or section is None:
                    continue

                if section == "nodes" and len(parts) >= 2:
                    counts["nodes"] += 1
                    status = parts[-1].lower()
                    if status != node_ok:
                        is_pass = 0
                        message_list.append(f"Node {parts[0]}: {status}")

                elif section == "paths" and len(parts) >= 4:
                    counts["paths"] += 1
                    status = " ".join(parts[-2:]).lower()
                    if status != path_ok:
                        is_pass = 0
                        message_list.append(f"Path {parts[0]} -> {parts[1]}: {status}")

                elif section == "rgs" and len(parts) >= 3:
                    counts["rgs"] += 1
                    status = parts[-1].lower()
                    if status != rg_ok:
                        is_pass = 0
                        message_list.append(f"RG {parts[0]}({parts[1]}): {status}")

                elif section == "nics" and len(parts) >= 3:
                    counts["nics"] += 1
                    status = parts[-1].lower()
                    if status != nic_ok:
                        is_pass = 0
                        message_list.append(f"NIC {parts[0]}({parts[1]}): {status}")

            criteria_items = [
                f"Node 상태 {node_ok}",
                f"Path 상태 {path_ok}",
                f"RG 상태 {rg_ok}",
                f"NIC 상태 {nic_ok}",
            ]
            if ok_if_missing:
                criteria_items.append("명령어 미설치 시 제외")

            if counts["nodes"] == 0:
                if ok_if_missing:
                    return {
                        "is_success": 1,
                        "is_pass": -1,
                        "reason_text": "Solaris Cluster 구성이 확인되지 않았습니다.",
                    }
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": "Cluster 상태",
                    "criteria_items": criteria_items,
                    "judgement_text": "점검 필요",
                    "detail_lines": ["scstat 클러스터 정보 수집 실패: Cluster Nodes 데이터 없음"],
                }

            if is_pass == 1:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": "Cluster 상태",
                    "criteria_items": criteria_items,
                    "judgement_text": "정상",
                    "detail_lines": ["scstat 클러스터 정상 확인"],
                }

            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "Cluster 상태",
                "criteria_items": criteria_items,
                "judgement_text": "점검 필요",
                "detail_lines": message_list,
            }

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"클러스터 평가 실패: {err}",
            }

    @classmethod
    def _run_lssrc_aix(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            if not output:
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": "Cluster 상태",
                    "judgement_text": "점검 필요",
                    "detail_lines": ["명령어 결과가 없습니다."],
                }

            lines = [line.strip() for line in output.splitlines() if line.strip()]
            first_line = lines[0] if lines else ""
            if first_line.startswith("0513-086"):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "Cluster 구성이 확인되지 않았습니다.",
                }

            criteria = params.get("inspection_criteria")
            if not criteria:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "검사할 키워드가 지정되지 않았습니다.",
                }

            if isinstance(criteria, list):
                criteria_list = [str(item).strip().lower() for item in criteria if str(item).strip()]
            else:
                criteria_list = [
                    item.strip().lower()
                    for item in str(criteria).split(",")
                    if item.strip()
                ]

            if not criteria_list:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "검사할 키워드가 지정되지 않았습니다.",
                }

            failed_lines = []
            for line in lines:
                lowered = line.lower()
                if all(keyword in lowered for keyword in criteria_list):
                    continue
                failed_lines.append(line)

            criteria_text = ", ".join(criteria_list)
            if failed_lines:
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": "Cluster 상태",
                    "criteria_items": [f"모든 라인에 키워드 포함: {criteria_text}"],
                    "judgement_text": "점검 필요",
                    "detail_lines": [
                        f"({criteria_text}) 상태가 아닌 시스템.",
                        *failed_lines,
                    ],
                }

            return {
                "is_success": 1,
                "is_pass": 1,
                "check_target": "Cluster 상태",
                "criteria_items": [f"모든 라인에 키워드 포함: {criteria_text}"],
                "judgement_text": "정상",
                "detail_lines": ["모든 시스템이 정상입니다."],
            }

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"AIX Cluster 평가 실패: {err}",
            }

    @classmethod
    def _run_cmviewcl_hpux(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            lowered = output.lower()
            if not output:
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "Cluster 구성이 확인되지 않았습니다.",
                }

            missing_markers = ["cmviewcl:  not found", "cmviewcl: not found", "command not found", "not found"]
            if any(marker in lowered for marker in missing_markers):
                return {
                    "is_success": 1,
                    "is_pass": -1,
                    "reason_text": "Cluster 구성이 확인되지 않았습니다.",
                }

            criteria = params.get("inspection_criteria") or ["offline", "hard error", "transport error"]
            if isinstance(criteria, list):
                bad_tokens = [str(item).strip().lower() for item in criteria if str(item).strip()]
            else:
                bad_tokens = [item.strip().lower() for item in str(criteria).split(",") if item.strip()]

            failed_lines = []
            detail_lines = []
            for raw_line in output.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                line_lower = line.lower()
                if any(token in line_lower for token in bad_tokens):
                    failed_lines.append(line)
                elif "cluster" in line_lower or "node" in line_lower or "package" in line_lower or "up" in line_lower:
                    detail_lines.append(line)

            return {
                "is_success": 1,
                "is_pass": 0 if failed_lines else 1,
                "check_target": "Cluster 상태",
                "criteria_items": [f"비정상 키워드 미검출: {', '.join(bad_tokens)}"],
                "judgement_text": "점검 필요" if failed_lines else "정상",
                "detail_lines": failed_lines if failed_lines else (detail_lines or ["cmviewcl 출력에서 비정상 상태가 발견되지 않았습니다."]),
            }

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"HP-UX Cluster 평가 실패: {err}",
            }

RULE_KEY = ClusterStatusRule.RULE_KEY
RULE_CLASS = ClusterStatusRule
