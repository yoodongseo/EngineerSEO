from functools import wraps

def filter_result(func):
    @wraps(func)
    def wrapper(self, stdout_data):
        result = func(self, stdout_data)

        def parse_result_output(self, stdout_data):
            """
            result 딕셔너리를 받아 점검 결과 output을 파싱하여 포맷팅된 문자열을 반환합니다.
            """
            message = result.get('message', "")
            stdout_text = result.get('stdout_data', stdout_data).strip()
            data = result.get('data')

            ## MW 재기동 자동화 파싱 코드
            if '(인스턴스' in message and stdout_text[0] == '1':
                stdout_text = stdout_text[1:]

            formatted = (
                f"점검 결과:\n{message}\n\n"
                f"명령어 결과값:\n\n{stdout_text}\n"
                # f"명령어 결과값:\n{stdout_data}\n\n"
            )
            return formatted

        # 공통 필드 추가
        common_fields = {
            'id': self.id,
            'cmd_name': self.cmd_name,
            'host': self.host,
            'host_name': self.host,
            'real_host_name': self.real_host_name,
            'name': self.name,
            'command': self.command,
            'report_type': self.report_type,
            'system': self.system,
            'file_path': self.file_path,
            'result': parse_result_output(self, stdout_data),
            'message': self.message,
            'is_pass': result.get('is_pass', 0),
            'fail_reason': result.get('message', ""),
            'os': self.os,
            'is_compare': self.is_compare
        }

        # 기존 결과와 공통 필드 병합
        return {**result, **common_fields}

    return wrapper


class BaseFilter:
    def __init__(self, params):
        self.id = params.get('cmd_id')
        self.cmd_name = params.get('name')
        self.host = params.get('host')
        self.host_name = params.get('host')
        self.real_host_name = params.get('host_name')
        self.name = params.get('name')
        self.command = params.get('command')
        self.report_type = params.get('report_type')
        self.system = params.get('system')
        self.file_path = params.get('file_path', "")
        self.message = params.get('message', "")
        self.os = params.get('os', "")
        self.is_compare = params.get('is_compare', "")

        if 'sid' in params and params['sid']:
            self.sid = params['sid']

        try:
            self.inspection_criteria = int(params.get('inspection_criteria'))
        except Exception as e:
            self.inspection_criteria = params.get('inspection_criteria', "")
