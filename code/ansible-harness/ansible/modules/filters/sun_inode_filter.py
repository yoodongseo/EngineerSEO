from .base_filter import BaseFilter, filter_result
import re

class SunInodeFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "df -o" in self.command:
            is_success, is_pass, result, message = self.df_o_type1(stdout_data)
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

    def df_o_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message_list = []

            if not isinstance(self.inspection_criteria, int):
                is_pass = 0
                message = f"❌ inspection_criteria 오류(임계치 필요): {self.inspection_criteria}"
                result = message
                return is_success, is_pass, result, message

            threshold = self.inspection_criteria

            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌ df -o i 출력이 비어있습니다."
                result = message
                return is_success, is_pass, result, message

            lines = [l.strip() for l in stdout_data.splitlines() if l.strip()]

            ignore_tokens = [
                    "operation not applicable for FSType",
                    "operation not applicable for fstype",
                    "사용할수 없는"
            ]

            data_lines = []
            ignore_lines = []

            for l in lines:
                low = l.lower()
                if any(t in low for t in ignore_tokens):
                    ignore_lines.append(1)
                else:
                    data_lines.append(1)

            if not data_lines and ignore_lines:
                message = "✅ I-Node 점검 대상 파일시스템 미존재: 정상 판단"
                result = message
                return is_success, is_pass, result, message

            checked = 0

            for s in data_lines:
                if "%" not in s:
                    continue
                if s.lower().startswith("fliesystem") or s.startswith("파일시스템"):
                    continue
                parts = s.split()

                pct_token = None
                for p in parts:
                    if p.endswith("%"):
                        pct_oken = p
                        break

                if not pct_token:
                    continue

                try:
                    pct = int(pct_token.replace("%", ""))
                except ValueError:
                    continue

                checked += 1
                fs = parts[0]
                mount = parts[-1]

                if pct >= threshold:
                    is_pass = 0
                    message_list.append(f"❌{fs} ({mount}): I-Node 사용률 {pct}% (기준: < {threshold}%)")

            if checked == 0:
                message = "✅ I-Node 점검 대상 파일시스템 미존재: 정상 판단"
                result = message
                return is_success, is_pass, result, message

            if is_pass == 1:
                message = f"✅ I-Node 사용률 정상: 모든 파일시스템 {threshold}% 미만"
            else:
                message = "\n".join(message_list)
            
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ I-Node 필터 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
