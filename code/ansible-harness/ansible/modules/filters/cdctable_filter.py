from multiprocessing.reduction import duplicate
from .base_filter import BaseFilter, filter_result
import re
from collections import Counter

class CdcTableFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""

        if "grep -i 'TABLE'" in self.command:
            is_success, is_pass, result, message = self.cdctable_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message
        
        return {
            'message': result,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success
        }
    
    def cdctable_type1(self, stdout_data):
        try:
            is_success = 1
            lines = [line.strip() for line in stdout_data.trip().splitlines() if line.strip]

            if not lines:
                is_pass = 0
                message = "❌ 점검할 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            line_counts = Counter(lines)
            duplicates = {line for line, count in line_counts.items() if count > 1}

            if duplicates:
                is_pass = 0
                duplicate_messages = [f"❌ 중복된 항목이 발견되었습니다.:\n {self.command}"]
                for line in sorted(list(duplicates)):
                    duplicate_messages.append(f"- {line}")
                message = "\n".join(duplicate_messages)
            else:
                is_pass = 1
                message = f"✅ 중복된 항목이 없습니다.\n {self.command}"
            
            result = message
        
        except Exception as e:
            is_pass = 0
            message = f"❌ CDC Table 중복 점검 분석 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message