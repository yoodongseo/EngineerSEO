from .base_filter import BaseFilter, filter_result
import re
import sys

class RHEL6NetworkLinkFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""

        if "link" in self.command:
            is_success, is_pass, result, message = self.link_type1(stdout_data)
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
    
    def link_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if isinstance(self.inspection_criteria, list):
                targets = [str(x).strip().lower() for x in self.inspection_criteria if str(x).strip()]

            elif isinstance(self.inspection_criteria, dict):
                match_type = str(self.inspection_criteria.get("match_type", "exact")).strip().lower()
                values = self.inspection_criteria.get("values", [])
                if isinstance(values, list):
                  targets = [str(x).strip().lower() for x in values if str(x).strip()]
                else:
                  targets = []
            else:
                is_pass = 0
                message = f"❌점검 기준이 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            critical_ifaces = [str(x).strip() for x in self.inspection_criteria if str(x).strip()]
            critical_set = set([x.lower() for x in critical_ifaces])

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message
            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = f"❌ 명령어 실패: 명령어 출력이 비어있습니다."
                result = message
                return is_success, is_pass, result, message
            
            header_re = re.compile(r"^\d+:\s*([^:]+):\s*<([^>]*)>.*\bstate\s+(\S+)", re.IGNORECASE)

            found = {}
            for raw in stdout_data.splitlines():
                line = raw.strip()
                m = header_re.match(line)
                if not m:
                    continue

                iface = m.group(1).strip()
                flags_str = m.group(2).strip()
                state = m.group(3).strip()
                
                flags = [f.strip().upper() for f in flags_str.split(",") if f.strip()]
                found[iface.lower()] = {"iface": iface, "flags": flags, "state": state.upper()}

            target_ifaces = []
            if match_type == "exact":
                for t in targets:
                    if t in found:
                        target_ifaces.append(t)
                missing = [i for i in critical_ifaces if i.lower() not in found]
                if missing:
                    is_pass = 0
                    message_list.append(f"❌출력에서 대상 NIC 블록을 찾을 수 없습니다.: {missing} (장치 인식/표기 불안정 가능)")

            elif match_type == "prefix":
                for iface in found:
                    if any(iface.startswith(t) for t in targets):
                        target_ifaces.append(iface)

                if not target_ifaces:
                    is_pass = 0
                    message_list.append(f"❌출력에서 대상 NIC 블록을 찾을 수 없습니다. {targets}")

#            missing = [i for i in critical_ifaces if i.lower() not in found]
#            if missing:
#                is_pass = 0
#                message_list.append(f"❌출력에서 대상 NIC 블록을 찾을 수 없습니다.: {missing} (장치 인식/표기 불안정 가능) {critical_ifaces}")

            for target in critical_ifaces:
                key = target.lower()
                if key not in found:
                    continue

                info = found[key]
                state = info["state"]
                flags = info["flags"]

                if state != "UP":
                    is_pass = 0
                    message_list.append(f"❌{info['iface']}: state={state} (기준: UP)")
                if "UP" not in flags:
                    is_pass = 0
                    message_list.append(f"❌{info['iface']}: flags에 UP 없음 (flags={flags})")
                if "LOWER_UP" not in flags:
                    is_pass = 0
                    message_list.append(f"❌{info['iface']}: flags에 LOWER_UP 없음(물리 링크 비정상 가능성) (flags={flags})")

            if is_pass == 1:
                message = f"✅NW 링크 상태 정상: 대상NIC {len(critical_ifaces)}개 모두 UP/LOWER_UP 정상"
            else:
                message = "\n".join(message_list) if message_list else f"❌알 수 없는 오류로 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"
            
            result = message
        
        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ fail action: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
