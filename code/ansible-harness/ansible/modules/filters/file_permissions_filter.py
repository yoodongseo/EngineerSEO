
from .base_filter import BaseFilter, filter_result

class CriticalFilePermissionFilter(BaseFilter):
    def __init__(self, params):
        super().__init__(params)

    @filter_result
    def evaluate(self, stdout_data):
        is_success = 1
        result_messages = []
        is_pass = 1  # 전체 결과 기준
        message = ""

        try:
            lines = stdout_data.strip().splitlines()

            # U-06: 소유자 없는 파일
            orphan_files = [l for l in lines if 'nouser' in l or 'nogroup' in l]
            if orphan_files:
                is_pass = 0
                result_messages.append("[U-06] 소유자 없는 파일 존재")
                result_messages += orphan_files
            else:
                result_messages.append("[U-06] 모든 파일 소유자 정상")

            # U-07: /etc/passwd 소유자 root, 권한 644 이하
            passwd_line = next(
                (l for l in lines if '/etc/passwd' in l and l.strip().startswith(('-', 'd'))),
                None
            )
            if passwd_line:
                parts = passwd_line.split()
                perms, owner = parts[0], parts[2]
                if not (owner == 'root' and perms.startswith('-rw-r--r--')):
                    is_pass = 0
                    result_messages.append(f"[U-07] /etc/passwd 권한 오류: {perms}, 소유자: {owner}")
                else:
                    result_messages.append("[U-07] /etc/passwd 권한 정상")
            else:
                is_pass = 0
                result_messages.append("[U-07] /etc/passwd 항목 누락")

            # U-08: /etc/shadow 소유자 root, 권한 400 이하
            shadow_line = next(
                (l for l in lines if '/etc/shadow' in l and l.strip().startswith(('-', 'd'))),
                None
            )
            if shadow_line:
                parts = shadow_line.split()
                perms, owner = parts[0], parts[2]
                if not (owner == 'root' and perms == '-r--------'):
                    is_pass = 0
                    result_messages.append(f"[U-08] /etc/shadow 권한 오류: {perms}, 소유자: {owner}")
                else:
                    result_messages.append("[U-08] /etc/shadow 권한 정상")
            else:
                is_pass = 0
                result_messages.append("[U-08] /etc/shadow 항목 누락")

            result = "\n".join(result_messages)
            message = f"점검 완료: {'양호' if is_pass else '취약'}"
            print("[DEBUG] passwd_line:", passwd_line)
            print("[DEBUG] shadow_line:", shadow_line)
            
        except Exception as e:
            is_success = 0
            is_pass = 0
            message = f"파일 권한 점검 실패: {str(e)}"
            result = message

        return {
            'message': message,
            'inspection_criteria': str(self.inspection_criteria),
            'is_pass': is_pass,
            'is_success': is_success,            
        }
