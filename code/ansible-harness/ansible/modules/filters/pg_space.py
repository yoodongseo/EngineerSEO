from .base_filter import BaseFilter, filter_result
import re

class PgspaceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        message = ""
        if "swapinfo -tam" in self.command:
            is_success, is_pass, result, message = self.swapinfo_type1(stdout_data)
        elif "svmon -G" in self.command:
            is_success, is_pass, result, message = self.svmon_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }

    def swapinfo_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            message = ""
            result = ""

            target_line_name = "total"
            threshold = 80

            if isinstance(self.inspection_criteria, list) and len(self.inspection_criteria) == 2:
                target_line_name = str(self.inspection_criteria[0]).lower()
                try:
                    threshold = float(self.inspection_criteria[1])
                except ValueError:
                  pass
            elif isinstance(self.inspection_criteria, dict):
                target_line_name = self.inspection_criteria.get('target_line', 'total').lower()
                threshold = self.inspection_criteria.get('threshold', 80).lower()
            elif isinstance(self.inspection_criteria, (int, float)):
                threshold = self.inspection_criteria

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            if not stdout_data or "USED" not in stdout_data:
                is_pass = 0
                message = f"❌ 명령어 실패: 필수 헤더 라인 'Filesystem' 을 찾을 수 없습니다.(출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()
            pct_used_value = None

            for line in lines:
                stripped_line = line.strip()
                match = re.match(rf"^{target_line_name}\s+", stripped_line.lower())
                if match:
                    parts = stripped_line.split()
                    if len(parts) >= 5:
                      pct_used_str = parts[4]
                      if pct_used_str.endswith("%"):
                          pct_used_value = float(pct_used_str.replace("%", ""))
            
            if pct_used_value is None:
                is_pass = 0
                message = f"❌ 메모리 정보 확인 실패: 'momory' 행의 'USED' 값을 찾을 수 없습니다.(출력값:{str(stdout_data).strip()[:200]}...)"
                result = message
            else:
                if pct_used_value < threshold:
                    is_pass = 1
                    status = "✅"
                    message = f"{status} {target_line_name.capitalize()} PCT USED: {pct_used_value}% (기준: {threshold}%)"
                else:
                    is_pass = 1
                    status = "❌"
                    message = f"{status} {target_line_name.capitalize()} PCT USED: {pct_used_value}% (기준: {threshold}%)"
                result = message
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 파일시스템 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def svmon_type1(self, stdout_data):
        try:
            is_success = 1
            keyword = 'pg space'
            entity_name = 'Paging Space'
            threshold = self.inspection_criteria

            lines = stdout_data.strip().splitlines()
            target_line = next((line for line in lines if line.strip().startswith(keyword)), None)

            if target_line:
                # 'pg space' 키워드 이후의 숫자 부분만 잘라내어 처리
                data_part = target_line.strip()[len(keyword):].strip()
                parts = data_part.split()

                if len(parts) < 2:
                    is_pass = 0
                    message = f"❌ {entity_name} 정보 파싱 실패: 데이터 값을 찾을 수 없습니다."
                    result = message
                    return is_success, is_pass, result, message

                size = int(parts[0])
                inuse = int(parts[1])

                if size > 0:
                    usage = (inuse / size) * 100
                    is_pass = 1 if usage <= threshold else 0
                    status = "✅" if is_pass else "❌"
                    message = f"{status} {entity_name} 사용률: {usage:.1f}% (기준: {threshold}%)"
                    if not is_pass:
                        message += " - 기준값 초과"
                    result = message
                else:
                    is_pass = 0
                    message = f"❌ {entity_name} 'size' 값이 0이므로 사용률을 계산할 수 없습니다."
                    result = message
            else:
                is_pass = 0
                message = f"❌ '{self.command}' 출력에서 '{keyword}' 라인을 찾을 수 없습니다."
                result = message

        except (ValueError, IndexError) as e:
            is_pass = 0
            is_success = 0
            message = f"❌ {entity_name} 평가 실패: 데이터 파싱 중 오류가 발생했습니다. ({e})"
            result = message
        except Exception as e:
             is_success = 0
             is_pass = 0
             message = f"❌ {entity_name} 평가 실패: {str(e)}"
             result = message

        return is_success, is_pass, result, message
