from .base_filter import BaseFilter, filter_result
import re

class JampHeapFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "jmap -heap" in self.command:
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

    def _get_thresholds(self):
        criteria = self.inspection_criteria
        if isinstance(criteria, dict):
            young = criteria.get('young_threshold', criteria.get('young'))
            old = criteria.get('old_threshold', criteria.get('old'))
            if young is None or old is None:
                raise ValueError("inspection_criteria에 young / old threshold 값을 모두 선언해야 합니다.")
            return float(young), float(old)
        if isinstance(criteria, (int, float)):
            value = float(criteria)
            return value, value
        raise ValueError("inspection_criteria는 숫자 또는 young / old threshold 딕셔너리여야 합니다.")

    def _extract_capacity_used(self, lines, markers):
        for idx, line in enumerate(lines):
            lowered = line.lower()
            if any(marker in lowered for marker in markers):
                cap = None
                used = None
                end_idx = min(len(lines), idx + 15)
                for j in range(idx + 1, end_idx):
                    if cap is None:
                        cap_maatch = re.search(r'capacity\s*=\s*(\d+)', lines[j], re.IGNORECASE)
                        if cap_match:
                            cap = int(cap_match.group(1))
                    if used is None:
                        used_match = re.search(r'used\s*=\s*(\d+)', lines[j], re.IGNORECASE)
                        if used_match:
                            used = int(used_match.group(1))
                    if cap is not None and used is not None:
                        return cap, used
        return None, None

    def linux_type1(self, stdout_data):
        try:
            is_success = 1
            output_lower = stdout_data.lower()

            negative_keywords = [
                "error",
                "exception",
                "failed",
                "cannot",
                "can't",
                "could not",
                "unable",
                "denied",
            ]
            attach_context_keywords = [
                "attach",
                "hotspot",
                "debugger",
                "sun.jvm.hotspot",
                "jmap",
                "vm",
            ]
            has_negative = any(keyword in output_lower for keyword in negative_keywords)
            has_attach_context = any(keyword in output_lower for keyword in attach_context_keywords)

            if has_negative and has_attach_context:
                is_pass = 0
                message = (
                    "❌ 점검 필요: Java Heap 정보를 조회하지 못 했습니다.\n"
                    "- 원인: 프로세스가 HotSpot JVM이 아니거나 PID 권한/상태 문제일 수 있습니다.\n"
                    "- 조치: 대상 PID와 실행 계정 권한을 확인하세요."
                )
                result = message
                return is_success, is_pass, result, message

            if "heap usage:" not in output_lower:
                is_pass = 0
                message = "❌ 점검 필요: Heap Usage 정보를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            young_threshold, old_threshold = self._get_thresholds()
            lines = stdout_data.splitlines()

            young_markers = [
                "ps young generation",
                "eden space:"
                "defnew generation",
                "g1 eden space",
            ]
            old_markers = [
                "ps old generation",
                "tenured gen",
                "cms old gen",
                "g1 old gen",
            ]

            young_capacity, young_used = self._extract_capacity_used(lines, young_markers)
            old_capacity, old_used = self._extract_capacity_used(lines, old_markers)

            if not young_capacity or not old_capacity:
                is_pass = 0
                message = "❌ 점검 필요: Young/Old Generation 용량 정보를 파싱하지 못 했습니다."
                result = message
                return is_success, is_pass, result, message

            young_pct = (young_used / young_capacity) * 100.0
            old_pct = (old_used / old_capacity) * 100.0

            exceeds = (young_pct >= young_threshold) or (old_pct >= old_threshold)
            if exceeds:
                is_pass = 0
                message = (
                    "❌ 점검 필요: Heap 사용률이 기준을 초과했습니다.\n"
                    "- Young Generation\n"
                    f" 기준값: {young_threshold:.1f}%\n"
                    f" 출력값: {young_pct:.1f}%\n"
                    "- Old Generation\n"
                    f" 기준값: {old_threshold:.1f}%\n"
                    f" 출력값: {old_pct:.1f}%"
                )
            else:
                is_pass = 1
                message = (
                    "✅ 정상: Heap 사용률이 기준 이내입니다.\n"
                    "- Young Generation\n"
                    f" 기준값: {young_threshold:.1f}%\n"
                    f" 출력값: {young_pct:.1f}%\n"
                    "- Old Generation\n"
                    f" 기준값: {old_threshold:.1f}%\n"
                    f" 출력값: {old_pct:.1f}%"
                )

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ jmap heap 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message


