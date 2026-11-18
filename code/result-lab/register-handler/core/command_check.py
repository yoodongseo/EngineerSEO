import re


class CommandCheck:
    STATIC_ERROR_PATTERNS = [
        re.compile(r"\bcommand not found\b", re.IGNORECASE),
        re.compile(r"\bis not recognized as an internal or external command\b", re.IGNORECASE),
        re.compile(r"\b명령을 찾을 수 없습니다\b", re.IGNORECASE),
        re.compile(r"\bno such file or directory\b", re.IGNORECASE),
        re.compile(r"\bcannot open\b", re.IGNORECASE),
        re.compile(r"\baccess is denied\b", re.IGNORECASE),
        re.compile(r"\b액세스가 거부되었습니다\b", re.IGNORECASE),
        re.compile(r"\billegal option\b", re.IGNORECASE),
        re.compile(r"\binvalid option\b", re.IGNORECASE),
        re.compile(r"\bunknown option\b", re.IGNORECASE),
    ]

    @classmethod
    def run(cls, command, stdout_data, inspection_criteria, criteria_required=False, allow_empty_output=False, allow_not_found=False):
        output = (stdout_data or "").strip()
        matched_error_line = cls._find_error_line(command, output)
        if matched_error_line:
            if allow_not_found:
                # VIP 통과: 에러 문자열이 룰 로직 안에서 처리될 수 있도록 command_check는 간섭하지 않음
                pass
            else:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "processed_result": f"명령어 실패: {matched_error_line}",
                }

        if not output and not allow_empty_output:
            return {
                "is_success": 0,
                "is_pass": 0,
                "processed_result": "명령어 결과가 없습니다.",
            }

        if criteria_required:
            if inspection_criteria is None:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "processed_result": "점검 기준값이 선언되지 않았습니다.",
                }

            if isinstance(inspection_criteria, str) and not inspection_criteria.strip():
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "processed_result": "점검 기준값이 선언되지 않았습니다.",
                }

        return None

    @classmethod
    def _find_error_line(cls, command, output):
        if not output:
            return ""

        command_names = cls._extract_command_names(command)

        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            if cls._matches_command_not_found(command_names, stripped):
                return stripped

            for pattern in cls.STATIC_ERROR_PATTERNS:
                if pattern.search(stripped):
                    return stripped

        return ""

    @staticmethod
    def _extract_command_names(command):
        raw = str(command or "").strip().lower()
        if not raw:
            return []

        tokens = re.findall(r"[a-z0-9_./-]+", raw)
        names = []
        ignore_tokens = {
            "for", "do", "done", "if", "then", "else", "fi", "while", "read", "echo",
            "grep", "awk", "xargs", "powershell", "powershell.exe", "cmd", "cmd.exe",
            "sh", "bash", "ksh", "c", "command",
        }

        for token in tokens:
            normalized = token.strip().strip("\"'")
            if not normalized or normalized in ignore_tokens:
                continue
            base = normalized.split("/")[-1]
            if base in ignore_tokens:
                continue
            if base not in names:
                names.append(base)

        return names

    @staticmethod
    def _matches_command_not_found(command_names, line):
        lowered = str(line or "").strip().lower()
        if not lowered:
            return False

        for name in command_names:
            if lowered == f"{name}: not found":
                return True

        return False