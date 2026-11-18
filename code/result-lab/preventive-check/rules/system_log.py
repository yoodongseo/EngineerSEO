import re
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class SystemLogRule:
    RULE_KEY = "system_log"
    CHECK_TARGET = "시스템 로그"

    @classmethod
    def criteria_required(cls, command):
        return True

    @classmethod
    def allow_empty_output(cls, command):
        return True

    @classmethod
    def build_check_rules(cls, params):
        return "시스템/커널/메모리/I-O 오류 로그 없음"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip().lower()

        if "get-eventlog" in command or "wevtutil qe system" in command:
            if os_type == "windows":
                return cls._run_windows_eventlog_check(params, stdout_data)
            return build_unsupported_command(params)

        if "errpt" in command:
            if os_type == "aix":                
                return cls._run_log_keyword_check(params, stdout_data)
            return build_unsupported_command(params)

        if "syslog" in command:
            if os_type in ("linux", "linux5"):                
                return cls._run_syslog_check(params, stdout_data)
            if os_type == "hpux":
                return cls._run_log_keyword_check(params, stdout_data)
            return build_unsupported_command(params)

        if "java.lang.thread.state" in command:
            if os_type in ("linux", "linux5"):                
                return cls._run_thread_state_check(params, stdout_data)
            return build_unsupported_command(params)

        if "dmesg" in command or "tail" in command:
            if os_type in ["linux", "linux5", "solaris", "hpux"]:
                return cls._run_log_keyword_check(params, stdout_data)
            return build_unsupported_command(params)

        return build_unsupported_command(params)

    @classmethod
    def _run_windows_eventlog_check(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            if not output:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "EventLog 출력이 비어 있습니다.",
                }

            keywords = cls._normalize_keywords(params.get("inspection_criteria"))
            if not keywords:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "정보 확인",
                    "detail_lines": ["검사 키워드가 없어 수집 성공으로만 판단합니다."],
                }

            expanded_keywords = list(keywords)
            if "error" in keywords and "오류" not in expanded_keywords:
                expanded_keywords.append("오류")

            found_lines = []
            for line in output.splitlines():
                line_text = line.strip()
                if not line_text:
                    continue
                for keyword in expanded_keywords:
                    if cls._keyword_matches(line_text, keyword):
                        found_lines.append(line_text)
                        break

            result = {
                "is_success": 1,
                "is_pass": 0 if found_lines else 1,
                "check_target": cls.CHECK_TARGET,
                "judgement_text": "비정상 로그 발견" if found_lines else "특이사항 없음",
                "detail_lines": found_lines or ["Error 레벨 로그가 발견되지 않았습니다."],
            }
            cls._attach_keyword_criteria(result, keywords)
            return result

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Windows EventLog 평가 실패: {err}",
            }

    @classmethod
    def _run_log_keyword_check(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            if not output:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "특이사항 없음",
                    "detail_lines": ["시스템 로그가 없습니다."],
                }

            first_line = output.splitlines()[0].strip()
            if first_line.startswith(("ERROR:", "%")):
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "로그 조회 오류",
                    "detail_lines": [f"로그 조회 명령어 실행 중 오류가 발생했습니다: {first_line}"],
                }

            keywords = cls._normalize_keywords(params.get("inspection_criteria"))
            if not keywords:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "정보 확인",
                    "detail_lines": ["검사할 키워드가 지정되지 않았지만, 로그 내용은 존재합니다."],
                }

            found_lines = []
            for line in output.splitlines():
                for keyword in keywords:
                    if cls._keyword_matches(line, keyword):
                        found_lines.append(line.strip())
                        break

            result = {
                "is_success": 1,
                "is_pass": 0 if found_lines else 1,
                "check_target": cls.CHECK_TARGET,
                "judgement_text": "비정상 로그 발견" if found_lines else "특이사항 없음",
                "detail_lines": found_lines or ["로그에서 특이사항이 발견되지 않았습니다."],
            }
            cls._attach_keyword_criteria(result, keywords)
            return result

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"시스템 로그 평가 실패: {err}",
            }

    @classmethod
    def _run_syslog_check(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            keywords = cls._normalize_keywords(params.get("inspection_criteria"))

            if not output:
                result = {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "점검 필요",
                    "detail_lines": ["로그 파일이 비어있거나, 접근할 수 없습니다."],
                }
                cls._attach_keyword_criteria(result, keywords)
                return result

            if "not found" in output.lower():
                result = {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "점검 필요",
                    "detail_lines": [f"명령어 실패로 해석되는 출력이 발견되었습니다: {output.splitlines()[0]}"],
                }
                cls._attach_keyword_criteria(result, keywords)
                return result

            found_lines = []
            for line in output.splitlines():
                for keyword in keywords:
                    if cls._keyword_matches(line, keyword):
                        found_lines.append(line.strip())
                        break

            result = {
                "is_success": 1,
                "is_pass": 0 if found_lines else 1,
                "check_target": cls.CHECK_TARGET,
                "judgement_text": "비정상 로그 발견" if found_lines else "특이사항 없음",
                "detail_lines": found_lines or ["로그에서 특이사항이 발견되지 않았습니다."],
            }
            cls._attach_keyword_criteria(result, keywords)
            return result

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"syslog 평가 실패: {err}",
            }

    @classmethod
    def _run_thread_state_check(cls, params, stdout_data):
        try:
            output = (stdout_data or "").strip()
            if not output:
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "점검 필요",
                    "detail_lines": ["Thread dump 출력이 비어있습니다."],
                }

            criteria_list = cls._normalize_keywords(params.get("inspection_criteria"))
            if not criteria_list:
                return {
                    "is_success": 1,
                    "is_pass": 0,
                    "check_target": cls.CHECK_TARGET,
                    "judgement_text": "점검 필요",
                    "detail_lines": ["inspection_criteria가 비어있습니다."],
                }

            blocks = re.split(
                r"(?=^\s*java\.lang\.Thread\.State\s*:)",
                output,
                flags=re.M | re.I,
            )
            state_line_re = re.compile(
                r"^\s*java\.lang\.Thread\.State\s*:\s*([A-Z_]+)",
                re.I | re.M,
            )

            offenders = []
            parsed_any = False

            for block in blocks:
                stripped_block = block.strip()
                if not stripped_block:
                    continue

                state_match = state_line_re.search(stripped_block)
                if not state_match:
                    continue

                parsed_any = True
                state_value = (state_match.group(1) or "").strip().lower()
                if state_value in criteria_list:
                    offenders.append(stripped_block)

            result = {
                "is_success": 1,
                "is_pass": 1,
                "check_target": cls.CHECK_TARGET,
                "judgement_text": "특이사항 없음",
                "detail_lines": ["Thread 상태가 정상입니다."],
            }
            cls._attach_keyword_criteria(result, criteria_list)

            if not parsed_any:
                result["is_pass"] = 0
                result["judgement_text"] = "점검 필요"
                result["detail_lines"] = ["java.lang.Thread.State 블록을 찾을 수 없습니다."]
                return result

            if offenders:
                result["is_pass"] = 0
                result["judgement_text"] = "비정상 Thread 상태 발견"
                result["detail_lines"] = offenders

            return result

        except Exception as err:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Thread 상태 점검 실패: {err}",
            }

    @staticmethod
    def _normalize_keywords(criteria):
        if isinstance(criteria, list):
            raw_items = criteria
        else:
            raw_items = str(criteria or "").split(",")

        return [str(item).strip().lower() for item in raw_items if str(item).strip()]

    @staticmethod
    def _keyword_matches(line, keyword):
        if not keyword:
            return False

        normalized_keyword = keyword.strip().lower()
        if re.fullmatch(r"[a-z0-9_]+", normalized_keyword):
            pattern = rf"(?<![a-z0-9_]){re.escape(normalized_keyword)}(?![a-z0-9_])"
            return re.search(pattern, line, re.IGNORECASE) is not None

        return re.search(re.escape(normalized_keyword), line, re.IGNORECASE) is not None

    @staticmethod
    def _attach_keyword_criteria(result, keywords):
        if not keywords:
            return

        if len(keywords) == 1:
            result["criteria_text"] = f"비정상 키워드 {keywords[0]} 미포함"
            return

        result["criteria_items"] = [f"비정상 키워드 {keyword} 미포함" for keyword in keywords]

RULE_KEY = SystemLogRule.RULE_KEY
RULE_CLASS = SystemLogRule
