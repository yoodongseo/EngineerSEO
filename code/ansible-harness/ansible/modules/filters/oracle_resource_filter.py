from .base_filter import BaseFilter, filter_result

class OracleResourceFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "ps -aux | grep -v grep | awk '{ print $2, $11, $4, $6, $5 }'" in self.command:
            is_success, is_pass, result, message = self.oracle_memory_type1(stdout_data)
        elif "ps -aux | grep -v grep | awk '{ print $2, $11, $3 }'" in self.command:
            is_success, is_pass, result, message = self.oracle_cpu_type1(stdout_data)
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

    def oracle_memory_type1(self, stdout_data):
        try:
            is_success = 1

            if isinstance(self.inspection_criteria, bool) or not isinstance(self.inspection_criteria, (int, float)):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(%MEM 임계값)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            threshold = float(self.inspection_criteria)
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]

            if not lines:
                is_pass = 0
                message = "❌ 점검 필요: Oracle 프로세스 메모리 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            overused = []
            parsed_count = 0

            for line in lines:
                parts = line.split()
                if len(parts) < 5:
                    continue

                pid = parts[0]
                command = parts[1]
                mem_text = parts[2]
                rss = parts[3]
                vsz = parts[4]

                try:
                    mem_value = float(mem_text)
                except Exception:
                    continue

                parsed_count += 1
                if mem_value > threshold:
                    overused.append(
                        f"- PID: {pid}, CMD: {command}, 기준값: {threshold:.2f}%, 출력값: {mem_value:.2f}%, RSS: {rss}KB, VSZ: {vsz}KB"
                    )

            if parsed_count == 0:
                is_pass = 0
                message = "❌ 점검 필요: Oracle 프로세스 메모리 데이터 파싱에 실패했습니다."
                result = message
                return is_success, is_pass, result, message

            if overused:
                is_pass = 0
                message = "❌ 점검 필요: 메모리 사용률(%MEM)이 기준을 초과한 Oracle 프로세스가 있습니다.\n\n" + "\n".join(overused)
            else:
                is_pass = 1
                message = f"✅ 정상: 모든 Oracle 프로세스의 %MEM이 기준({threshold:.2f}%) 이내입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 프로세스 자원 평가 중 오류 발생: {str(e)}"
            result = message
                
        return is_success, is_pass, result, message
    
    def oracle_cpu_type1(self, stdout_data):
        try:
            is_success = 1

            if isinstance(self.inspection_criteria, bool) or not isinstance(self.inspection_criteria, (int, float)):
                is_pass = 0
                message = "❌ 점검 필요: inspection_criteria는 숫자(%MEM 임계값)로 선언해야 합니다."
                result = message
                return is_success, is_pass, result, message

            threshold = float(self.inspection_criteria)
            lines = [line.strip() for line in stdout_data.splitlines() if line.strip()]

            if not lines:
                is_pass = 0
                message = "❌ 점검 필요: Oracle 프로세스 메모리 데이터가 없습니다."
                result = message
                return is_success, is_pass, result, message

            overused = []
            parsed_count = 0

            for line in lines:
                parts = line.split()
                if len(parts) < 3:
                    continue

                pid = parts[0]
                command = parts[1]
                cpu_text = parts[2]

                try:
                    cpu_value = float(cpu_text)
                except Exception:
                    continue

                parsed_count += 1
                if cpu_value > threshold:
                    overused.append(
                        f"- PID: {pid}, CMD: {command}, 기준값: {threshold:.2f}%, 출력값: {cpu_value:.2f}%"
                    )

            if parsed_count == 0:
                is_pass = 0
                message = "❌ 점검 필요: Oracle 프로세스 메모리 데이터 파싱에 실패했습니다."
                result = message
                return is_success, is_pass, result, message

            if overused:
                is_pass = 0
                message = "❌ 점검 필요: CPU 사용률(%CPU)이 기준을 초과한 Oracle 프로세스가 있습니다.\n\n" + "\n".join(overused)
            else:
                is_pass = 1
                message = f"✅ 정상: 모든 Oracle 프로세스의 %CPU이 기준({threshold:.2f}%) 이내입니다."

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ Oracle 프로세스 자원 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
