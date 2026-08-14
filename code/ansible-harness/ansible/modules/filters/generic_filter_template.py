from .base_filter import BaseFilter, filter_result
import re

# 1. 클래스 이름 변경 (예: DiskFilter)
class GenericFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success, is_pass, result, message = self.handle_command_output(stdout_data)

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
        }

    def handle_command_output(self, stdout_data):
        # =================== 핸들러 설정 (새 필터 작성 시 이 부분을 주로 수정) ===================
        
        # 처리할 라인을 찾기 위한 키워드 (없으면 None)
        TARGET_LINE_KEYWORD = "/dev/" 

        # 라인을 컬럼으로 분리할 구분자 (공백/탭이 기본값이면 None)
        DELIMITER = None # 특별히 ':'나 ',' 등이 필요할 때만 수정
        
        # 값을 추출할 컬럼 인덱스 (0부터 시작)
        COLUMN_INDEX_FOR_VALUE = 4 
        
        # 추출한 값에서 제거할 문자 (예: '%')
        CHARS_TO_REMOVE = '%'
        
        # 최종적으로 비교할 값의 타입 (int, float, str)
        VALUE_TYPE = int

        # =====================================================================================

        try:
            is_success = 1
            results_list = [] # 결과(성공/실패 여부, 메시지)를 저장할 리스트

            lines = stdout_data.strip().splitlines()

            for line in lines[1:]:
                if TARGET_LINE_KEYWORD is None or TARGET_LINE_KEYWORD in line:
                    
                    # 설정된 구분자를 사용하여 라인 분리
                    parts = line.split(DELIMITER)
                    
                    if len(parts) > COLUMN_INDEX_FOR_VALUE:
                        
                        # .strip()을 추가하여 값 주변의 불필요한 공백 제거
                        raw_value = parts[COLUMN_INDEX_FOR_VALUE].strip()
                        cleaned_value = raw_value.replace(CHARS_TO_REMOVE, '')
                        value_to_check = VALUE_TYPE(cleaned_value)
                        criteria = self.inspection_criteria

                        item_is_pass = 1 # 개별 항목의 성공 여부
                        
                        # 비교 로직
                        if value_to_check > criteria:
                            item_is_pass = 0
                            status = "❌"
                            message_line = f"{status} {line.split(DELIMITER)[0].strip()} 사용률 {value_to_check}% (기준: {criteria}% 초과)"
                        else:
                            item_is_pass = 1
                            status = "✅"
                            message_line = f"{status} {line.split(DELIMITER)[0].strip()} 사용률 {value_to_check}% (기준: {criteria}% 이하)"
                        
                        results_list.append((item_is_pass, message_line))

            # --- 결과 취합 및 정렬 ---
            if not results_list:
                is_pass = 0
                message = f"❌ 점검할 항목({TARGET_LINE_KEYWORD})을 찾지 못했습니다."
            else:
                results_list.sort(key=lambda x: x[0], reverse=True)
                is_pass = 1 if all(item[0] == 1 for item in results_list) else 0
                message = "\n".join(item[1] for item in results_list)

            result = message

        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"❌ 평가 중 오류 발생: {str(e)}"
            result = message

        return is_success, is_pass, result, message
