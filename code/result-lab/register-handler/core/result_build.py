class ResultBuild:
    @classmethod
    def _append_labeled_block(cls, lines, label, values):
        if not values:
            return

        if isinstance(values, list):
            filtered_values = [value for value in values if str(value or "").strip()]
            if not filtered_values:
                return
            lines.append(f"- {label}:")
            for value in filtered_values:
                lines.append(f"  {value}")
            return

        value_text = str(values).strip()
        if value_text:
            lines.append(f"- {label}: {value_text}")

    @classmethod
    def _append_check_lines(cls, lines, check_target, criteria_text, criteria_items, judgement_text):
        if criteria_items:
            cls._append_labeled_block(lines, "판정 기준", criteria_items)
        elif check_target and criteria_text:
            lines.append(f"- 판정 기준: {check_target} {criteria_text}")
        if judgement_text:
            lines.append(f"- 판정 결과: {judgement_text}")

    @classmethod
    def run(cls, params, processed, stdout_data=""):
        is_success = processed.get("is_success", 0)
        is_pass = processed.get("is_pass", 0)
        check_target = (processed.get("check_target") or "").strip()
        criteria_text = (processed.get("criteria_text") or "").strip()
        criteria_items = processed.get("criteria_items") or []
        judgement_text = (processed.get("judgement_text") or "").strip()
        reason_text = (processed.get("reason_text") or processed.get("processed_result") or "").strip()
        detail_lines = processed.get("detail_lines") or []

        lines = []

        if is_success == 0:
            lines.append("⛔ 명령어 실패")
            if reason_text:
                lines.append(f"- 실패 사유: {reason_text}")
        elif is_pass == 1:
            lines.append("✅ 정상")
            cls._append_check_lines(lines, check_target, criteria_text, criteria_items, judgement_text)
        elif is_pass == 0:
            lines.append("❌ 점검 필요")
            cls._append_check_lines(lines, check_target, criteria_text, criteria_items, judgement_text)
        elif is_pass == -1:
            lines.append("⚪ 해당 없음")
            if reason_text:
                lines.append(f"- 제외 사유: {reason_text}")
        else:
            lines.append("⚠️ 결과 확인 필요")

        cls._append_labeled_block(lines, "상세 내용", detail_lines)

        final_text = "\n".join(lines).strip()
        stdout_text = (stdout_data or "").strip()
        formatted_result = (
            f"점검 결과:\n{final_text}\n\n"
            f"명령어 결과값:\n\n{stdout_text}\n"
        )

        return {
            "id": params.get("cmd_id"),
            "cmd_name": params.get("name"),
            "host": params.get("host"),
            "host_name": params.get("host"),
            "real_host_name": params.get("host_name"),
            "name": params.get("name"),
            "command": params.get("command"),
            "report_type": params.get("report_type"),
            "system": params.get("system"),
            "file_path": params.get("file_path", ""),
            "message": params.get("message", ""),
            "fail_reason": final_text,
            "os": params.get("os", ""),
            "is_compare": params.get("is_compare", ""),
            "inspection_criteria": params.get("inspection_criteria"),
            "data4": processed.get("check_rules") or params.get("check_rules", ""),
            "data5": params.get("report_target", ""),
            "before_data": processed.get("before_data", ""),
            "after_data": processed.get("after_data", ""),
            "is_pass": is_pass,
            "is_success": True,
            "result": formatted_result,
        }
