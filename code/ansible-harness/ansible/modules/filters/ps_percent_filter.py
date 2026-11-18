from .base_filter import BaseFilter, filter_result

class PsPercentFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "ps -p" in self.command:
            is_success, is_pass, result, message = self.linux_type1(stdout_data)
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

    def linux_type1(self, stdout_data):
        try:
            is_success = 1

            if isinstance(self.inspection_criteria, bool) or not isinstance(self.inspection_criteria, (int, float)):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            threshold = float(self.inspection_criteria)
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]

            if not lines:
                is_pass = 0
                message = "❌ 점검 필요: ps -p 출력 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            header_parts = lines[0].split()
            if not header_parts:
                is_pass = 0
                message = "❌ 점검 필요: ps -p 헤더를 파싱하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            metric_name = header_parts[0]
            if len(lines) == 1:
                is_pass = 0
                message = "❌ 점검 필요: ps -p 결과에 대상 프로세스 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            overused = []
            parsed_count = 0

            for line in lines[1:]:
                data_parts = line.split()
                if not data_parts:
                    continue

                try:
                    metric_value = float(data_parts[0])
                except Exception:
                    continue

                parsed_count += 1
                if metric_value > threshold:
                    overused.append(
                        f"- 점검 항목: {metric_name}\n"
                        f"  출력값: {metric_value:.2f}\n"
                        f"  기준값: {threshold:.2f}\n"
                    )

            if parsed_count == 0:
                is_pass = 0
                message = "❌ 점검 필요: ps -p 첫 번째 컬럼 값을 숫자로 변환하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            if overused:
                is_pass = 0
                message = f"❌ 점검 필요: {metric_name} 값이 기준을 초과했습니다.\n" + "\n".join(overused)
            else:
                is_pass = 1
                message = (
                    f"✅ 정상: {metric_name} 값이 기준 이내입니다.\n"
                    f"- 점검 항목: {metric_name}\n"
                    f"  출력값: 전체 {parsed_count}건 기준 이내\n"
                    f"  기준값: {threshold:.2f}%"
                )

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ ps -p 자원 평가 중 오류 발생: {str(e)}"
            result = message
                
        return is_success, is_pass, result, message
