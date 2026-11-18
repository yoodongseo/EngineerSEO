from .base_filter import BaseFilter, filter_result
import re

class MessagesFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _keyword_matches(self, line, keyword):
        if not keyword:
            return False

        keyword = keyword.strip().lower()
        escaped = re.escape(keyword)

        if re.fullmatch(r'[a-z0-9_]+', keyword):
            pattern = rf'(?<![a-z0-9_]){escaped}(?![a-z0-9_])'
            return re.search(pattern, line, re.IGNORECASE) is not None

        return escaped in line

    @filter_result
    def evaluate(self, stdout_data):
        """로그 메시지를 검사하는 필터입니다."""
        is_success = 1
        message = ""

        if "show log messages" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "cat /var/log/messages" in self.command:
            is_success, is_pass, result, message = self.message_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': result,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success
        }

    def juniper_type1(self, stdout_data):
        #""'show log messages' 출력에서 inspection_criteria에 정의된 이상 로그 키워드를 확인합니다."""
        try:
            is_success = 1
            
            if not self.inspection_criteria:
                is_pass = 1
                message = "✅ 검사할 키워드가 지정되지 않았습니다."
                result = message
                return is_success, is_pass, result, message

            keywords_to_find = [kw.strip().lower() for kw in str(self.inspection_criteria).split(',') if kw.strip()]
            
            found_lines = []
            for line in stdout_data.strip().splitlines():
                line_lower = line.lower()
                for keyword in keywords_to_find:
                    if self._keyword_matches(line_lower, keyword):
                        found_lines.append(line.strip())
                        break
            
            if found_lines:
                is_pass = 0
                criteria_str = ", ".join(keywords_to_find)
                message = f"❌ 로그에서 비정상 키워드({criteria_str})가 포함된 다음 라인을 발견했습니다:\n" + "\n".join(found_lines)
            else:
                is_pass = 1
                message = "✅ 이상 로그가 발견되지 않았습니다."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 로그 점검 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def message_type1(self, stdout_data):
        """cat /var/log/messages 출력에서 inspection_criteria 키워드를 검색하고, 명령어 자체의 오류도 확인합니다."""
        try:
            is_success = 1

            if not stdout_data or not stdout_data.strip():
                is_pass = 1
                message = "✅ 오늘 날짜에 해당하는 로그가 없습니다."
                result = message
                return is_success, is_pass, result, message

            output_lower = stdout_data.lower()
            if "no such file or directory" in output_lower or "permission denied" in output_lower:
                is_pass = 0
                message = f"❌ 로그 파일 조회 중 오류가 발생했습니다: {stdout_data.strip()}"
                result = message
                return is_success, is_pass, result, message

            if not self.inspection_criteria:
                is_pass = 1
                message = "✅ 검사할 키워드가 지정되지 않았지만, 로그 내용은 존재합니다."
                result = message
                return is_success, is_pass, result, message

            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(c).lower() for c in self.inspection_criteria]
            else:
                criteria_list = [c.strip().lower() for c in str(self.inspection_criteria).split(',')]

            found_lines = []
            for line in stdout_data.strip().splitlines():
                line_lower = line.lower()
                for keyword in criteria_list:
                    if self._keyword_matches(line_lower, keyword):
                        found_lines.append(line.strip())
                        break
            
            if found_lines:
                is_pass = 0
                criteria_str = ", ".join(criteria_list)
                message = f"❌ 로그에서 비정상 키워드({criteria_str})가 포함된 다음 라인을 발견했습니다:\n" + "\n".join(found_lines)
            else:
                is_pass = 1
                message = "✅ 로그에서 특이사항이 발견되지 않았습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 로그 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
