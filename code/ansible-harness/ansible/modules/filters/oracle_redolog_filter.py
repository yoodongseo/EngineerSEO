from .base_filter import BaseFilter, filter_result
import re

class OracleRedologFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "SELECT l.GROUP#, f.MEMBER, l.BYTES/1024/1024 AS SIZE_MB, l.STATUS FROM V$LOG l JOIN V$LOGFILE f ON l.GROUP# = f.GROUP# ORDER BY l.GROUP#" in self.command:
            is_success, is_pass, result, message = self.oracle_redolog_type1(stdout_data)
        else:
            is_pass = 0
            is_success = 0
            message = f"❌ 지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def oracle_redolog_type1(self, stdout_data):
        try:
            is_success = 1

            if not stdout_data or not stdout_data.strip():
                is_pass = 0
                message = "❌ 출력이 비어있습니다."

            if not self.inspection_criteria:
                is_pass = 0
                message = "❌ 출력이 비어있습니다."

            criteria_set = {
                x.strip().lower()
                for x in str(self.inspection_criteria).split(",")
                if x.strip()
            }

            raw_lines = [l.strip() for l in stdout_data.splitlines()]
            lines = []

            for l in raw_lines:
                s = l.strip()
                if not s:
                    continue

                if re.match(r"^-{2,}$", s):
                    continue

                if s.lower() in ("group#", "member", "size_mb status", "done"):
                    continue

                lines.append(s)

            if not lines:
                is_pass = 0
                message = "❌ 데이터 라인을 찾을 수 없습니다."

 #            for line in lines:
 #                if re.match(r"^\d+$", line) or \
 #                        re.match(r"^\+", line) or \
 #                        re.match(r"^\d+\s", line) or \
 #                        re.match(r"^\d{3,}$", line) or \
 #                        re.match(r"^\d+\s*$", line):
 #                            data_lines.append(line)
 #                elif re.match(r"", line):
 #                    data_lines.append(line)
 #                else:
 #                    if line.startswith("+") or re.match(r"^\d+\s+[A-Z_]+", line, re.I):
 #                        data_lines.append(line)

            blocks = []
            cur = []
 #           temp = []

 #            for line in data_lines:
 #                temp.append(line)
 #                if len(temp) == 4:
 #                    blocks.append(temp)
 #                    temp = []

            for line in lines:
                if re.match(r'^\d+\s*$', line):
                    if cur:
                        blocks.append(cur)
                    cur = [line]
                else:
                    if cur:
                        cur.append(line)

            if cur:
                blocks.append(cur)

            if not blocks:
                is_pass = 0
                message = "❌ 로그 그룹 블록을 파싱하지 못했습니다."

            offenders = []
            parsed_any = False

            for block in blocks:
                if len(block) < 2:
                    continue

                parsed_any = True

                status_line = block[-1]
                status_tokens = status_line.split()

                if len(status_tokens) < 2:
                    offenders.append("\n".join(block))
                    continue

                status_val = status_tokens[-1].strip().lower()

                if status_val in criteria_set:
                    offenders.append("\n".join(block))

            if not parsed_any:
                is_pass = 0
                message = "❌ 유효한 로그 그룹 블록을 찾지 못했습니다."


            if offenders:
                is_pass = 0
                message = (
                    f"❌ 비정상 STATUS 발견 ({', '.join(criteria_set)}): {len(offenders)}개\n\n"
                    + "\n\n".join(offenders)
                )

            else:
                is_pass = 1
                message = "✅ 트랜젝션 로그 상태 정상"

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 트랜젝션 로그 점검 중 오류 발생: {str(e)}"
            result = message
                
        return is_success, is_pass, result, message
