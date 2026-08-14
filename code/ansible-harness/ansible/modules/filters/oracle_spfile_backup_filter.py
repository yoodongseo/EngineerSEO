from .base_filter import BaseFilter, filter_result
from datetime import date
import re

class OracleSpfileBackupFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "sh /home/oracle/oracle_ansible.sh" in self.command:
            is_success, is_pass, result, message = self.oracle_spfile_type1(stdout_data)
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

    def oracle_spfile_type1(self, stdout_data):
        try:
            is_success = 1
            
            if not stdout_data or not str(stdout_data).strip():
                is_pass = 0
                message = "❌ RMAN SPFILE 백업 조회 출력이 비어있습니다."
                return is_success, is_pass, message, message

            if not isinstance(self.inspection_criteria, dict) or not self.inspection_criteria:
                is_pass = 0
                message = f"❌ inspection_criteria(dict) 확인 필요: {self.inspection_criteria}"
                return is_success, is_pass, message, message

            max_age_days = int(self.inspection_criteria.get("max_age_days", 1))

            lines = [l.rstrip("\n") for l in str(stdout_data).splitlines()]
            candidates = []
            parse_failed_rows = []

            MONTH_MAP = {
                "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
                "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
                "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
            }           # row_re = re.compile(r"^\d+\s+.*\s+(\d{2}-[A-Za-z]{3}-\d{2})\s*$")

            for raw in lines:
                line = raw.strip()
                if not line:
                    continue

                if not re.match(r"^\s*\d+\s+", raw):
                    continue

                parts = line.split()
                if len(parts) < 2:
                    parse_failed_rows.append(line)
                    continue

                d_str = parts[-1]
                
                if not re.match(r"^\d{2}-[A-Za-z]{3}-\d{2}$", d_str):
                    parse_failed_rows.append(line)
                    parse_failed_rows.append(d_str)
                    continue
                
                try:
                    day = int(d_str[0:2])
                    mon = MONTH_MAP[d_str[3:6].upper()]
                    year = 2000 + int(d_str[7:9])
                    
                    d = date(year, mon, day)
                    candidates.append((d, line))

                except Exception as e:
                    parse_failed_rows.append(d_str)
                    parse_failed_rows.append(line)


            if not candidates:
                is_pass = 0
                message = "❌ Completion Time 파싱 실패 또는 데이터 행이 없습니다."
                if parse_failed_rows:
                    message += "\n\n❌ 파싱 실패 행:\n" + "\n".join(parse_failed_rows)
                return is_success, is_pass, message, message

            latest_date, latest_row  = max(candidates, key=lambda x: x[0])

            today = date.today()
            age_days = (today - latest_date).days

            if age_days <= max_age_days:
                is_pass = 1
                message = (
                    f"✅ 환경설정 파일 백업 완료 시각이 기준 일수 이내입니다.\n"
                    f"- 기준값:  {max_age_days}일 이하\n"
                    f"- 최신 백업: {latest_date.strftime('%Y-%m-%d')}\n"
                    f"- 경과일:  {age_days}"  
                )

            else:
                is_pass = 0
                message = (
                    f"❌ 환경설정 파일 백업본이 오래되었습니다.\n"
                    f"- 기준값:  {max_age_days}일 이하\n"
                    f"- 최신 백업: {latest_date.strftime('%Y-%m-%d')}\n"
                    f"- 경과일:  {age_days}"  
                )
        
            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ SPFILE 백업  점검 중 오류 발생: {str(e)}"
            result = message
                
        return is_success, is_pass, result, message
