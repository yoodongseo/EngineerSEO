from .base_filter import BaseFilter, filter_result
import re
from datetime import datetime

class OracleBackupFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "oracle_ansible.sh" in self.command:
            is_success, is_pass, result, message = self.oracle_type1(stdout_data)
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

    def oracle_type1(self, stdout_data):
        try:
            is_success = 1
            month_map = {
                "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4,
                "MAY": 5, "JUN": 6, "JUL": 7, "AUG": 8,
                "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
            }

            if isinstance(self.inspection_criteria, bool):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(일)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message
            
            try:
                threshold_days = float(self.inspection_criteria)
            except Exception:
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(일)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            backup_entries = []
            debug_total_lines = 0
            debug_data_lines = 0
            debug_date_tokens = []
            debug_sample_data_lines = []
            #debug_parse_errors = []

            for line in stdout_data.splitlines():
                debug_total_lines += 1
                normalized = " ".join(line.split())
                if not normalized:
                    continue
                upper_line = normalized.upper()
                if "COMPLETION TIME" in upper_line:
                    continue

                tokens = normalized.split()
                if not tokens or not tokens[0].isdigit():
                    continue
                debug_data_lines += 1
                if len(debug_sample_data_lines) < 5:
                    debug_sample_data_lines.append(normalized)

                parsed_dt = None
                for token in tokens:
                    date_match = re.fullmatch(r'\d{2}-[A-Za-z]{3}-\d{2}', token)
                    if not date_match:
                        continue
                    if len(debug_date_tokens) < 10:
                        debug_date_tokens.append(token)
                    try:
                        dd, mon, yy = token.upper().split("-")
                        day = int(dd)
                        month = month_map[mon]
                        year = 2000 + int(yy)
                        parsed_dt = datetime(year, month, day)
                        break
                    except Exception as e:
                        #if len(debug_parse_errors) < 3:
                        #    debug_parse_errors.append(f"{token} -> {str(e)}")
                        continue

                if parsed_dt:
                    backup_entries.append({
                        "dt": parsed_dt,
                        "raw_line": normalized
                    })

            if not backup_entries:
                is_pass = 0
                message = (
                    "❌ 점검 필요: 백업 완료 시간(DD-MON-YY)을 찾지 못 했습니다.\n"
                    f"- 디버그: 전체 라인 수={debug_total_lines}\n"
                    f"- 디버그: 데이터 후보 라인 수(첫 토큰 숫자)={debug_data_lines}\n"
                    f"- 디버그: 감지된 날짜 토큰(최대 10건)={', '.join(debug_date_tokens) if debug_date_tokens else '없음'}\n"
                    #f"- 디버그: 날짜 파싱 오류(최대 3건)={', '.join(debug_parse_errors) if debug_parse_errors else '없음'}\n"
                    "- 디버그: 데이터 후보 라인 샘플(최대 5건):\n"
                    + ("\n".join([f"  {x}" for x in debug_sample_data_lines]) if debug_sample_data_lines else "  없음")
                )
                result = message
                return is_success, is_pass, result, message

            now = datetime.now()
            latest_entry = max(backup_entries, key=lambda x: x["dt"])
            latest_backup = latest_entry["dt"]
            elapsed_days = (now - latest_backup).total_seconds() / 86400.0
            exceeded_items = []

            for entry in backup_entries:
                age_days = (now - entry["dt"]).total_seconds() / 86400.0
                if age_days > threshold_days:
                    exceeded_items.append(entry["raw_line"])

            if elapsed_days > threshold_days:
                is_pass = 0
                preview_limit = 10
                exceeded_preview = "\n".join([f" {line}" for line in exceeded_items[:preview_limit]]) if exceeded_items else " 없음"
                remaining_count = max(0, len(exceeded_items) - preview_limit)
                more_message = f"\n ... 외 {remaining_count}건 더 있음" if remaining_count > 0 else ""
                message = (
                    "❌ 점검 필요: 최근 백업 완료 시각이 기준 일수를 초과했습니다.\n"
                    f"- 기준값: {threshold_days}일 이하\n"
                    f"- 최신 백업: {latest_backup.strftime('%Y-%m-%d')}\n"
                    f"- 경과일: {elapsed_days}일\n"
                    #f"- 기준 초과 항목 수: {len(exceeded_items)}\n"
                    #f"- 기준 초과 라인(최대 {preview_limit}건):\n{exceeded_preview}{more_message}"
                )
            else:
                is_pass = 1
                message = (
                    "✅ 정상: 최근 백업 완료 시각이 기준 일수 이내입니다.\n"
                    f"- 기준값: {threshold_days}일 이하\n"
                    f"- 최신 백업: {latest_backup.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"- 경과일: {elapsed_days}일"
                )


            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 백업 상태  평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
