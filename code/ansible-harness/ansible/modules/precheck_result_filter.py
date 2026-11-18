#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule


def _merge_error_text(task_result):
    parts = []
    for key in ["msg", "stderr", "stdout", "exception"]:
        value = task_result.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _classify_result(task_result):
    text = _merge_error_text(task_result)
    text_lower = text.lower()

    if task_result.get("unreachable") is True:
        if any(token in text_lower for token in [
            "invalid/incorrect password",
            "incorrect password",
            "permission denied",
            "authentication failed",
            "please try again",
            "bad authentication",
        ]):
            return "AUTH_FAIL", text or "authentication failed"

        if any(token in text_lower for token in ["timed out", "timeout"]):
            return "TIMEOUT", text or "connection timed out"

        return "UNREACHABLE", text or "host unreachable"

    if task_result.get("failed") is True or int(task_result.get("rc", 0) or 0) != 0:
        if any(token in text_lower for token in [
            "su: 인증 실패",
            "authentication failure",
            "su: authentication failure",
            "sorry, try again",
            "sudo:",
            "become",
        ]):
            return "BECOME_FAIL", text or "privilege escalation failed"

        if any(token in text_lower for token in [
            "invalid/incorrect password",
            "incorrect password",
            "permission denied",
            "authentication failed",
            "please try again",
            "bad authentication",
        ]):
            return "AUTH_FAIL", text or "authentication failed"

        if any(token in text_lower for token in ["timed out", "timeout"]):
            return "TIMEOUT", text or "connection timed out"

        return "UNKNOWN_CONNECT_ERROR", text or "connection failed"

    return "NORMAL", text


def _display_status(status_code):
    mapping = {
        "NORMAL": "정상",
        "AUTH_FAIL": "계정 인증 실패",
        "BECOME_FAIL": "권한 상승 실패",
        "TIMEOUT": "접속 시간 초과(접속 정보 불일치 등)",
        "UNREACHABLE": "호스트 경로 없음",
        "CONNECTION_REFUSED": "접속 거부",
        "INVALID_HOST": "호스트 정보 확인 필요",
        "UNKNOWN_CONNECT_ERROR": "알 수 없는 접속 오류",
    }
    return mapping.get(status_code, "알 수 없는 접속 오류")


def build_result(task_result, host, host_name, report_type, system, file_path="", cmd_id="0000", name="00.연결상태", command="raw", message="00. 연결 상태", os_name=""):
    status, reason = _classify_result(task_result)
    return {
        "id": cmd_id,
        "cmd_id": cmd_id,
        "cmd_name": name,
        "host": host,
        "host_name": host,
        "real_host_name": host_name,
        "name": name,
        "command": command,
        "report_type": report_type,
        "system": system,
        "file_path": file_path,
        "message": message,
        "result": _display_status(status),
        "status_code": status,
        "fail_reason": reason,
        "is_pass": 1 if status == "NORMAL" else 0,
        "is_success": 1 if status == "NORMAL" else 0,
        "os": os_name,
        "is_compare": False,
        "raw_result": task_result,
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            task_result=dict(type='dict', required=True),
            host=dict(type='str', required=True),
            host_name=dict(type='str', required=True),
            report_type=dict(type='str', required=True),
            system=dict(type='str', required=True),
            file_path=dict(type='str', required=False, default=''),
            cmd_id=dict(type='str', required=False, default='0000'),
            name=dict(type='str', required=False, default='00.연결상태'),
            command=dict(type='str', required=False, default='raw'),
            message=dict(type='str', required=False, default='00. 연결 상태'),
            os=dict(type='str', required=False, default=''),
        ),
        supports_check_mode=False,
    )

    try:
        result = build_result(
            task_result=module.params['task_result'],
            host=module.params['host'],
            host_name=module.params['host_name'],
            report_type=module.params['report_type'],
            system=module.params['system'],
            file_path=module.params['file_path'],
            cmd_id=module.params['cmd_id'],
            name=module.params['name'],
            command=module.params['command'],
            message=module.params['message'],
            os_name=module.params['os'],
        )
        module.exit_json(changed=False, result=result)
    except Exception as e:
        module.fail_json(msg=f'precheck result filter failed: {str(e)}')


if __name__ == '__main__':
    main()
