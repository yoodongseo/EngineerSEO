from .base_filter import BaseFilter, filter_result
import re

class LogFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    def _keyword_matches(self, line, keyword):
        if not keyword:
            return False

        keyword = keyword.strip().lower()
        escaped = re.escape(keyword)

        if re.fullmatch(r'[a-z0-9_]+', keyword):
            pattern = rf'(?<![a-z0-9_]){escaped}(?![a-z0-9_])'
            return re.search(pattern, line, re.IGNORECASE) is not None

        return escaped in line

    @filter_result
    def evaluate(self, stdout_data):
        """
        로그 검사 필터
        'show system alarms', 'show chassis alarms', 'show log' 명령어 결과를 검사합니다.
        """
        is_success = 1
        message = ""
        result = ""
        
        if "errpt" in self.command:
            is_success, is_pass, result, message = self.log_type1(stdout_data)
        elif "syslog" in self.command:
            is_success, is_pass, result, message = self.syslog_type1(stdout_data)
        elif "dmesg" in self.command:
            is_success, is_pass, result, message = self.log_type1(stdout_data)
        elif "tail" in self.command:
            is_success, is_pass, result, message = self.log_type1(stdout_data)
        elif "java.lang.Thread.State" in self.command:
            is_success, is_pass, result, message = self.linux_log_type1(stdout_data)
        else:
            is_pass = 0
            message = f"❌지원하지 않는 명령어입니다: {self.command}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,
            'result': result
        }

    def juniper_type1(self, stdout_data):
        """'show system alarms' 또는 'show chassis alarms' 출력에서 'no alarms'를 확인하고, 알람 발생 시 내용을 추출합니다."""
        try:
            is_success = 1
            
            if "no alarms" in stdout_data.lower():
                is_pass = 1
                message = "✅ 알람이 발견되지 않았습니다."
            else:
                is_pass = 0
                alarm_lines = []
                parsing_error = None
                try:
                    lines = stdout_data.strip().splitlines()
                    header_index = -1
                    for i, line in enumerate(lines):
                        if 'description' in line.lower():
                            header_index = i
                            break
                    
                    if header_index != -1:
                        for i in range(header_index + 1, len(lines)):
                            if lines[i].strip():
                                alarm_lines.append(lines[i].strip())
                except Exception as e:
                    parsing_error = e

                if alarm_lines:
                    message = f"❌ 시스템 또는 섀시에서 다음 알람이 발견되었습니다:\n" + "\n".join(alarm_lines)
                elif parsing_error:
                    message = f"❌ 알람 세부 내용 파싱 중 오류 발생: {parsing_error}"
                else:
                    message = f"❌ 알람이 발견되었으나, 세부 내용을 찾지 못했습니다."
            
            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 알람 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def log_type1(self, stdout_data):
        """로그 내용에서 inspection_criteria 키워드를 검색하고, 명령어 자체의 오류도 확인합니다."""
        try:
            is_success = 1

            if not stdout_data or not stdout_data.strip():
                is_pass = 1
                message = "✅ 시스템  로그가 없습니다."
                result = message
                return is_success, is_pass, result, message

            first_line = stdout_data.strip().splitlines()[0].strip()
            if first_line.startswith(('ERROR:', '%')):
                is_pass = 0
                message = f"❌ 로그 조회 명령어 실행 중 오류가 발생했습니다: {first_line}"
                result = message
                return is_success, is_pass, result, message

            if not self.inspection_criteria:
                is_pass = 1
                message = "✅ 검사할 키워드가 지정되지 않았지만, 로그 내용은 존재합니다."
                result = message
                return is_success, is_pass, result, message

            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(c).lower() for c in self.inspection_criteria]
            else:
                criteria_list = [c.strip().lower() for c in str(self.inspection_criteria).split(',')]

            found_lines = []
            for line in stdout_data.strip().splitlines():
                line_lower = line.lower()
                for keyword in criteria_list:
                    if self._keyword_matches(line_lower, keyword):
                        found_lines.append(line.strip())
                        break
            
            if found_lines:
                is_pass = 0
                criteria_str = ", ".join(criteria_list)
                message = f"❌ 로그에서 비정상 키워드({criteria_str})가 포함된 다음 라인을 발견했습니다:\n" + "\n".join(found_lines)
            else:
                is_pass = 1
                message = "✅ 로그에서 특이사항이 발견되지 않았습니다."

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 로그 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message

    def syslog_type1(self, stdout_data):
        try:
            is_success = 1
            is_pass = 1
            messages_list = []
            
            abnormal_keywords = []
            if isinstance(self.inspection_criteria, list):
                abnormal_keywords = [str(item).upper() for item in self.inspection_criteria]

            if not stdout_data or not stdout_data.strip():
                is_pass = 0
                message = "❌ 로그 파일이 비어있거나, 접근할 수 없습니다."
                result = message
                return is_success, is_pass, result, message

            if stdout_data and "not found" in stdout_data.lower():
                is_pass = 0
                message = f"❌ 명령어 실패: 'command not found' (출력값: {str(stdout_data).strip()[:200]}...)"
                result = message
                return is_success, is_pass, result, message

            lines = stdout_data.splitlines()

            for line in lines:
                stripped_line = line.strip().lower()
                
                for keyword in abnormal_keywords:
                    if keyword in stripped_line:
                        is_pass = 0
                        messages_list.append(f"❌ 비정상 로그 키워드 '{keyword}' 발견: {line}")  
                        break

            if is_pass == 1:
                message = "✅ 로그에서 특이사항이 발견되지 않았습니다."
            else:
                message = "\n".join(message_list) if message_list else f"❌ 알 수 없는 오류로 로그 점검에 실패했습니다. (출력값:{str(stdout_data).strip()[:200]}...)"

            result = message

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ 로그 평가 중 오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message


    def linux_log_type1(self, stdout_data):
        try:
            is_success = 1
    
            if not stdout_data or not stdout_data.strip():
                message = "❌ Thread dump 출력이 비어있습니다."
                result = message
    
            if not self.inspection_criteria:
                message = "❌ inspection_criteria가 비어있습니다."
                result = message
    
            if isinstance(self.inspection_criteria, list):
                criteria_list = [str(x).strip().lower() for x in self.inspection_criteria if str(x).strip()]
            else:
                criteria_list = [
                    x.strip().lower()
                    for x in str(self.inspection_criteria).split(",")
                    if x.strip()
                ]
    
            if not criteria_list:
                message = "❌ inspection_criteria가 비어있습니다."
                result = message
    
            blocks = re.split(
                r'(?=^\s*java\.lang\.Thread\.State\s*:)',
                stdout_data,
                flags=re.M | re.I
            )
    
            state_line_re = re.compile(
                r'^\s*java\.lang\.Thread\.State\s*:\s*([A-Z_]+)',
                re.I | re.M
            )
    
            offenders = []
            parsed_any = False
    
            for block in blocks:
                block = block.strip()
                if not block:
                    continue
    
                m_state = state_line_re.search(block)
                if not m_state:
                    continue
    
                parsed_any = True
    
                state_val = (m_state.group(1) or "").strip().lower()
    
                if state_val in criteria_list:
                    offenders.append(block)
    
            if not parsed_any:
                is_pass = 0
                message = "❌ java.lang.Thread.State 블록을 찾을 수 없습니다."
                result = message
    
            if offenders:
                is_pass = 0
                message = (
                    f"❌ 비정상 Thread 상태 발견 ({', '.join(criteria_list)}): {len(offenders)}개\n\n"
                    + "\n\n".join(offenders)
                    )
                result = message
            else:
                is_pass = 1
                message = "✅ Thread 상태 정상"
                result = message
    

        except Exception as e:
            is_pass = 0
            is_success = 0
            message = f"❌ Thread 상태 점검 중  오류 발생: {str(e)}"
            result = message
        
        return is_success, is_pass, result, message



    
