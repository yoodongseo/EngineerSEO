from .base_filter import BaseFilter, filter_result

class InterfaceStatusFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        'show interfaces terse' 또는 'stat interface' 명령어 결과를 파싱합니다.
        이 필터는 상태 비교나 양불 판정을 하지 않고, 데이터 존재 유무만 확인합니다.
        """
        is_success = 1
        message = ""
        
        if "show interfaces terse" in self.command:
            is_success, is_pass, result, message = self.juniper_type1(stdout_data)
        elif "stat interface" in self.command:
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
        """'show interfaces terse' 출력에서 데이터 라인의 존재 여부만 확인합니다."""
        try:
            is_success = 1
            
            # 첫 줄(헤더)을 제외한 나머지 라인 중 내용이 있는 라인이 하나라도 있는지 확인
            lines = stdout_data.strip().splitlines()
            has_data = any(line.strip() for line in lines[1:])

            if has_data:
                is_pass = 1
                message = "✅ 인터페이스 상태 정보를 성공적으로 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 정보를 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 인터페이스 상태 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def citrix_type1(self, stdout_data):
        """'stat interface' 출력에 'Interface Summary'가 있는지 확인하여 데이터 유효성을 검증합니다."""
        try:
            is_success = 1

            # 1. 출력이 비어있는지 또는 특정 헤더를 포함하는지 확인 (대소문자 무시)
            if stdout_data and "interface summary" in stdout_data.lower():
                is_pass = 1
                message = "✅ 인터페이스 상태 정보를 성공적으로 확인했습니다."
            else:
                is_pass = 0
                message = "❌ 유효한 'Interface Summary' 헤더를 찾을 수 없습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 인터페이스 상태 파싱 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
