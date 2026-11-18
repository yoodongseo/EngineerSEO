from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rule_result import build_unsupported_command

class KernelParameterRule:
    RULE_KEY = "kernel_parameter"

    @classmethod
    def criteria_required(cls, command):
        return False

    @classmethod
    def build_check_rules(cls, params):
        return "기본 Kernel Parameter 적용 상태"

    @classmethod
    def run(cls, params, stdout_data):
        command = (params.get("command") or "").strip().lower()
        os_type = (params.get("os") or "").strip().lower()

        if "kctune" in command:
            if os_type == "hpux":                
                return cls._run_kernel_info(stdout_data)            

        if "lsattr -el sys0" in command:
            if os_type == "aix":                
                return cls._run_kernel_info(stdout_data)            

        if "sysctl -a" in command:
            if os_type in ("linux", "linux5"):                
                return cls._run_kernel_info(stdout_data)            

        if "sysdef" in command:
            if os_type == "solaris":
                return cls._run_kernel_info(stdout_data)          

        if "netsh int tcp show global" in command or "netsh int ip show global" in command:
            if os_type == "windows":                
                return cls._run_windows_kernel_collection(stdout_data)            

        return build_unsupported_command(params)

    @classmethod
    def _run_kernel_info(cls, stdout_data):
        try:
            lines = (stdout_data or "").strip().splitlines()
            data_lines = [line.strip() for line in lines if line.strip()]

            if not data_lines:
                return {
                    "is_success": 0,
                    "is_pass": 0,
                    "reason_text": "Kernel parameter 명령 결과가 비어 있어 커널 파라미터 정보를 확인할 수 없습니다.",
                }

            if data_lines:
                return {
                    "is_success": 1,
                    "is_pass": 1,
                    "check_target": "커널 파라미터 정보",
                    "criteria_text": "커널 파라미터 출력 존재",
                    "judgement_text": "정보 확인",
                    "detail_lines": ["커널 정보를 성공적으로 확인했습니다."],
                }

            return {
                "is_success": 1,
                "is_pass": 0,
                "check_target": "커널 파라미터 정보",
                "criteria_text": "커널 파라미터 출력 존재",
                "judgement_text": "정보 없음",
                "detail_lines": ["헤더 다음 커널 정보가 없습니다."],
            }
        except Exception as exc:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": f"Kernel parameter 평가 실패: {exc}",
            }

    @classmethod
    def _run_windows_kernel_collection(cls, stdout_data):
        output = (stdout_data or "").strip()
        if not output:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "명령어 결과가 비어 있어 커널 파라미터 수집 여부를 확인할 수 없습니다.",
            }

        data_lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
            and not line.strip().startswith("C:\\")
            and not line.strip().startswith("PS ")
            and not line.strip().startswith(">>")
        ]
        if not data_lines:
            return {
                "is_success": 0,
                "is_pass": 0,
                "reason_text": "명령어 실행 흔적만 있고 수집된 커널 파라미터 내용이 없습니다.",
            }

        return {
            "is_success": 1,
            "is_pass": 1,
            "check_target": "커널 파라미터 수집",
            "criteria_text": "커널 파라미터 출력 존재",
            "judgement_text": "수집 완료",
            "detail_lines": [
                "netsh/레지스트리 커널 파라미터 수집 결과가 확인되었습니다.",
                f"수집 라인 수: {len(data_lines)}",
            ],
        }

RULE_KEY = KernelParameterRule.RULE_KEY
RULE_CLASS = KernelParameterRule
