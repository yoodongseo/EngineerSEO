from .base_filter import BaseFilter, filter_result
import re

class SunMemoryFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)
    
    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1

        if "vmstat" in self.command:
            is_success, is_pass, result, message = self.sun_vmstat_type1(stdout_data)
        elif "prtdiag" in self.command:
            is_success, is_pass, result, message = self.sun_prtdiag_type1(stdout_data)
        elif "swap" in self.command:
            is_success, is_pass, result, message = self.sun_swap_type1(stdout_data)
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

    def sun_vmstat_type1(self, stdout_data):
        is_success = 1
        try:
            try:
                criteria = float(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = f"❌ 점검 기준값(inspection_criteria)이 올바른 숫자가 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            total_memory = None
            free_memory = None

            for line in lines:
                if "Total Memory:" in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        total_memory = int(match.group(1))
                elif "Free Memory" in line:
                    match = re.search(r'(\d+)', line)
                    if match:
                        free_memory = int(match.group(1))

            if total_memory is None or free_memory is None:
                is_pass = 0
                message = "❌ 메모리 정보 파싱 실패: 출력에서 'Total Memory' 또는 'Free Memory' 라인을 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            if total_memory == 0:
                is_pass = 0
                message = "❌ 'Total Memory' 값이 0이므로 사용률을 계산할 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            free_percent = (free_memory / total_memory) * 100

            if free_percent >= criteria:
                is_pass = 1
                message = f"✅ 정상: 여유 메모리 비율이  {free_percent:.2f}%로, 기준({criteria}%) 이상입니다."
            else:
                is_pass = 0
                message = f"❌ 점검 필요: 여유 메모리 비율이 {free_percent:.2f}%로, 기준({criteria}%)을 미만입니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 메모리 평가 실패: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def sun_prtdiag_type1(self, stdout_data):
        is_success = 1
        try:
            lines = stdout_data.strip().splitlines()
            found_line = None

            for line in lines:
                if "Memory size:" in line or "메모리 크기" in line:
                    found_line = line.strip()
                    break

            if found_line:
                is_pass = 1
                message = f"✅ 정상: 메모리 인식 정보 확인\n {found_line}"
            else:
                is_pass = 0
                message = "❌ 점검 필요: 'Memory size' 또는 '메모리 크기' 정보를 찾을 수 없습니다."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 메모리 상태 평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message

    def sun_swap_type1(self, stdout_data):
        try:
            is_success = 1
            try:
                criteria = float(self.inspection_criteria)
            except (ValueError, TypeError):
                is_pass = 0
                message = f"❌ 점검 필요: 점검 기준값(inspection_criteria)이 올바른 숫자가 아닙니다: '{self.inspection_criteria}'"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.strip().splitlines()
            if len(lines) < 2:
                is_pass = 0
                message = "❌ 점검 필요: 'swap -l' 출력 내용을 분석할 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            header_line = lines[0].lower()
            header_parts = header_line.split()

            blocks_idx = -1
            free_idx = -1

            if 'blocks' in header_parts and 'free' in header_parts:
                blocks_idx = header_parts.index('blocks')
                free_idx = header_parts.index('free')
            elif '블록' in header_parts and '사용' in header_parts:
                blocks_idx = header_parts.index('블록')
                free_idx = header_parts.index('사용')
            else:
                is_pass = 0
                message = "❌ 점검 필요: 스왑 헤더를 찾을 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            failed_swaps = []
            for line in  lines[1:]:
                parts = line.split()
                if len(parts) <= max(blocks_idx, free_idx):
                    continue

                swap_file = parts[0]
                try:
                    blocks = int(parts[blocks_idx])
                    free = int(parts[free_idx])

                    if blocks == 0:
                        continue

                    usage_percent = ((blocks - free) / blocks) * 100

                    if usage_percent > criteria:
                        failed_swaps.append(f" - {swap_file} (사용률: {usage_percent:.2f}%)")
                except (ValueError, IndexError):
                    continue

            if failed_swaps:
                is_pass = 0
                fail_list_str = "\n".join(failed_swaps)
                message = f"❌ 점검 필요: 일부 스왑 영역의 사용률이 기준({criteria}%)을 초과했습니다:\n{fail_list_str}"
            else:
                is_pass = 1
                message = f"✅ 정상: 모든 스왑 영역의 사용률이 기준({criteria}%) 이하입니다.\n사용률: {usage_percent:.2f}%"

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Solaris 스왑 사용량  평가 실패: {str(e)}"
            result = message

        return is_success, is_pass, result, message
