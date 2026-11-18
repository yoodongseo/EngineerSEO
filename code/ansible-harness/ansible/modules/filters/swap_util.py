from .base_filter import BaseFilter, filter_result
import re

class SwapFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "swapinfo -tam" in self.command:
            is_success, is_pass, result, message = self.swapinfo_type1(stdout_data)
        elif "lsps -a" in self.command:
            is_success, is_pass, result, message = self.lsps_type1(stdout_data)
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
            message = f"❌ 디스크 Swap 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def lsps_type1(self, stdout_data):
        try:
            is_success = 1
            lines = stdout_data.strip().splitlines()
            results_fail = []
            is_pass = 1

            criteria = float(self.inspection_criteria)

            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 5 and "%" in parts[4]:
                    try:
                        usage_percent = float(parts[4].replace("%", ""))
                        page_space_name = parts[0]
                        if usage_percent > criteria:
                            is_pass = 0
                            results_fail.append(f"❌ {page_space_name} 사용률: {usage_percent:.1f}% (기준 {criteria:1.f}%)")
                    except ValueError:
                        continue

            if not results_fail:
                message = f"✅ 모든 Swap 사용량이 임계값({criteria:.1f}%) 이하입니다."
            else:
                message = "\n".join(results_fail)

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 디스크 Swap 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
