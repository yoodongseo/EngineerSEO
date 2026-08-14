from .base_filter import BaseFilter, filter_result

class ConfigurationFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        명령어 결과를 파싱하여 설정 정보의 존재 여부만 확인합니다.
        이 필터는 상태 비교나 양불 판정을 하지 않고, 데이터 존재 여부만 반환합니다.
        """
        is_success = 1
        message = ""
        
        if "show configuration" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "show ns ns.conf" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
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
        """'show configuration' 출력에서 데이터 라인의 존재 여부만 확인합니다."""
        try:
            is_success = 1
            
            lines = stdout_data.strip().splitlines()
            has_data = any(line.strip() for line in lines)

            if has_data:
                is_pass = 1
                message = "✅ 설정 정보를 성공적으로 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 정보를 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 설정 정보 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def citrix_type1(self, stdout_data):
        """'show ns ns.conf' 출력의 마지막에 'Done'이 있는지 확인합니다."""
        try:
            is_success = 1
            
            # 마지막 줄이 'Done'으로 끝나는지 확인
            if stdout_data and stdout_data.strip().endswith('Done'):
                is_pass = 1
                message = "✅ 설정 정보를 성공적으로 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 명령어 출력이 비정상적이거나 마지막 라인에서 'Done'을 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 설정 정보 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
