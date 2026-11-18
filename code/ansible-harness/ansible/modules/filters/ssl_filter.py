from .base_filter import BaseFilter, filter_result
from datetime import datetime

class SslFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        """
        SSL 인증서의 만료일을 점검합니다.
        """
        is_success = 1
        message = ""
        
        if "show ssl certkey -summary" in self.command:
            is_success, is_pass, result, message = self.citrix_type1(stdout_data)
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

    def citrix_type1(self, stdout_data):
        """'show ssl certkey -summary' 명령어 출력을 파싱하여 인증서 만료일을 확인합니다."""
        try:
            is_success = 1
            failing_certs = []
            header_found = False
            
            try:
                criteria_days = int(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                is_success = 0
                message = f"❌ 점검 기준(inspection_criteria) '{self.inspection_criteria}'이(가) 유효한 숫자가 아닙니다."
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 헤더 라인 확인
                if "DaysToExp" in line and "CertPath" in line:
                    header_found = True
                    continue
                
                if not header_found or "Done" in line or line.startswith(">"):
                    continue

                # 데이터 라인 처리
                parts = line.split()
                if len(parts) >= 2: # 최소한 Name과 DaysToExp가 있다고 가정
                    try:
                        cert_name = parts[1]
                        days_to_exp = int(parts[-1])
                        
                        if days_to_exp <= criteria_days:
                            failing_certs.append(f"{cert_name} (만료까지 {days_to_exp}일 남음)")
                    except (ValueError, IndexError):
                        # 파싱 오류가 있는 라인은 건너뜁니다.
                        continue
            
            if not header_found:
                 is_pass = 0
                 message = "❌ SSL 인증서 정보를 찾을 수 없습니다. (헤더 누락)"
            elif failing_certs:
                is_pass = 0
                message = f"❌ 다음 SSL 인증서의 만료일이 임박했습니다 (기준: {criteria_days}일 이하):\n" + "\n".join(failing_certs)
            else:
                is_pass = 1
                message = f"✅ 모든 SSL 인증서의 만료일이 정상입니다 (기준: {criteria_days}일 초과)."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ SSL 인증서 점검 중 오류 발생: {str(e)}"
            
        return is_success, is_pass, result, message
