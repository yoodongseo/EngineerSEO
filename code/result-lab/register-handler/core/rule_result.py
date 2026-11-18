def build_unsupported_command(params):
    command = params.get("command", "")
    command_text = str(command or "-").strip() or "-"

    return {
        "is_success": 0,
        "is_pass": 0,
        "reason_text": f"지원하지 않는 명령어입니다: {command_text}",
    }


def build_not_applicable(reason_lines):
    lines = reason_lines or ["해당 항목의 구성이 확인되지 않았습니다."]
    if isinstance(lines, str):
        reason_text = lines.strip() or "해당 항목의 구성이 확인되지 않았습니다."
    else:
        filtered = [str(line).strip() for line in lines if str(line or "").strip()]
        reason_text = filtered[0] if filtered else "해당 항목의 구성이 확인되지 않았습니다."

    return {
        "is_success": 1,
        "is_pass": -1,
        "reason_text": reason_text,
    }
