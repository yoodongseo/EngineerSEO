from .base_filter import BaseFilter, filter_result
import re

class SunRedundancyFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "ipmpstat" in self.command:
            is_success, is_pass, result, message = self.ipmpstat_type1(stdout_data)
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

    def ipmpstat_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌점검 기준{inspection_criteria} 이(가) 누락되었거나 형식이 맞지 않습니다."
                result = message
                return is_success, is_pass, result, message

            min_n = int(self.inspection_criteria.get("min_ifaces_per_group", 2))
            req_active = str(self.inspection_criteria.get("required_active", "yes")).lower()
            req_link = str(self.inspection_criteria.get("required_link", "up")).lower()
            req_state = str(self.inspection_criteria.get("required_state", "ok")).lower()

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 1
                message = f"✅ipmpstat 출력정보 없음: IPMP 구성상태 확인 필요"
                result = message
                return is_success, is_pass, result, message

            if stdout_data and "not found" in stdout_data.lower() or "없음" in stdout_data.lower():
                is_pass = 1
                message = f"✅ 명령어 미존재: IPMP 구성상태 확인 필요"
                result = message
                return is_success, is_pass, result, message

            lines = [l.strip() for l in stdout_data.splitlines() if l.strip()]

            group_count = {}

            for l in lines:
                parts = l.split()
                if len(parts) < 6:
                    continue

                iface = parts[0]
                active = parts[1].lower()
                group = parts[2]
                link = parts[-2].lower()
                state = parts[-1].lower()

                group_count[group] = group_count.get(group, 0) + 1

                if active != req_active:
                    is_pass = 0
                    message_list.append(f"❌ {iface}({group}): ACTIVE={active}")
                if link != req_link:
                    is_pass = 0
                    message_list.append(f"❌ {iface}({group}): LINK={link}")
                if state != req_state:
                    is_pass = 0
                    message_list.append(f"❌ {iface}({group}): STATE={state}")

            if not group_count:
                is_pass = 1
                message = "✅ IPMP 구성상태 확인 필요(그룹 미존재)"
                result = message
                return is_success, is_pass, result, message

            for g, cnt in group_count.items():
                if cnt < min_n:
                    is_pass = 0
                    messages_list.append(f"❌IPMP 그룹 '{g}' 인터페이스 수 부족: {cnt}")

            if is_pass == 1:
                message = f" IPMP 정상: {len(group_count)} 개 그룹 정상 동작"
            else:
                message = "\n".join(message_list)

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ IPMP 이중화 상태 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
