from .base_filter import BaseFilter, filter_result
import re

class ProcessFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        프로세스 점검 필터
        'show system processes extensive' 명령어 결과를 검사합니다.
        """
        is_success = 1
        message = ""
        
        if "show system processes extensive" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        if "ps " in self.command:
            is_success, is_pass, result, message = self.process_check_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def juniper_type1(self, stdout_data):
        """'show system processes extensive' 출력에서 필수 프로세스가 실행 중인지 확인합니다."""
        try:
            is_success = 1
            
            if not self.inspection_criteria:
                is_pass = 0
                is_success = 0
                message = "❌ 점검 기준(inspection_criteria)이 설정되지 않았습니다."
                result = message
                return is_success, is_pass, result, message

            required_processes = {p.strip() for p in self.inspection_criteria.split(',') if p.strip()}
            
            running_processes = set()
            lines = stdout_data.strip().splitlines()
            header_found = False
            for line in lines:
                if 'pid' in line.lower() and 'command' in line.lower():
                    header_found = True
                    continue
                
                if header_found:
                    parts = line.split()
                    if len(parts) > 0:
                        running_processes.add(parts[-1])

            if not header_found:
                is_pass = 0
                is_success = 0
                message = "❌ 프로세스 목록을 찾을 수 없습니다. (헤더 파싱 실패)"
                result = message
                return is_success, is_pass, result, message

            missing_processes = required_processes - running_processes
            
            if not missing_processes:
                is_pass = 1
                message = f"✅ 모든 필수 프로세스({', '.join(sorted(list(required_processes)))})가 실행 중입니다."
            else:
                is_pass = 0
                message = f"❌ 일부 필수 프로세스가 실행 중이 아닙니다. (누락: {', '.join(sorted(list(missing_processes)))})"
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 프로세스 점검 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def process_check_type1(self, stdout_data):
        """출력에서 데이터 라인의 존재 여부만 확인합니다."""
        try:
            is_success = 1

            # 첫 줄(헤더)을 제외한 나머지 라인 중 내용이 있는 라인이 하나라도 있는지 확인
            lines = stdout_data.splitlines()
            has_data = any(line.strip() for line in lines)

            if has_data:
                is_pass = 1
                message = "✅ 프로세스 정보를 성공적으로 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 프로세스 정보를 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 프로세스 파싱 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
