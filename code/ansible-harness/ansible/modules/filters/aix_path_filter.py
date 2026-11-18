from .base_filter import BaseFilter, filter_result

class AixPathFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        
        if "lspath" in self.command:
            is_success, is_pass, result, message = self._path_type1(stdout_data)
        else:
            is_pass = 0
            message = f"지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def _path_type1(self, stdout_data):
        is_success = 1
        try:
            if not self.inspection_criteria:
                is_pass = 0
                message = "❌ inspection_criteria가 정의되지 않았습니다. 허용 가능한 hdisk 상태(예: 'Enabled')를 지정해야 합니다."
                result = message
                return is_success, is_pass, result, message

            criteria_list = []
            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(c).lower() for c in self.inspection_criteria]
            else:
                criteria_list = [c.strip().lower() for c in str(self.inspection_criteria).split(',')]

            if not criteria_list:
                is_pass = 0
                message = f"❌ inspection_criteria가 유효한 상태 목록을 생성하지 못 했습니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            failures = []
            found_hdisk = False

            for line in stdout_data.splitlines():
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                if "hdisk" in stripped_line:
                    found_hdisk = True
                    parts = stripped_line.split()
                    if len(parts) >= 1:
                        status = parts[0].lower()
                        if status not in criteria_list:
                            failures.append(stripped_line)

            if not found_hdisk:
                is_pass = 0
                message = "❌ 'lspath' 출력에서 'hdisk' 관련 경로를 찾을 수 없습니다."
                result - message
                return is_success, is_pass, result, message

            if failures:
                is_pass = 0
                fail_summary = "\n- ".join(failures)
                message = f"❌ AIX 경로 이중화 점검 실패: 비정상 상태의 hdisk 경로가 발견되었습니다. (상태: {', '.join(criteria_list)})\n- {fail_summary}"
            else:
                is_pass = 1
                message = f"✅ AIX 모든 hdisk 경로가 정상 상태 ({', '.join(criteria_list)}) 입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ AIX Path 이중화 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message
