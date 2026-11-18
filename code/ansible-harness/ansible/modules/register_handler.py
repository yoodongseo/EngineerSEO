#!/usr/bin/python

from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.command_check import CommandCheck                                                                                                                
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.result_build import ResultBuild                                                                                                                  
from ansible_collections.fap.custom.plugins.module_utils.register_handler_core.rules import RULES_MAP       

def _item_label(item):
    command = (item or {}).get("command", "")
    cmd_id = (item or {}).get("cmd_id", "")
    return f"command='{command}', cmd_id='{cmd_id}'"


class RegisterHandler:
    def __init__(self, params):
        self.params = params

    def handle(self, result_item):
        command = self.params.get("command", "")
        rule_key = (self.params.get("rule_key") or "").strip().lower()
        rules_class = RULES_MAP.get(rule_key)
        stdout_data = (result_item or {}).get("output", "")

        if not rules_class:
            return ResultBuild.run(
                self.params,
                {
                    "is_success": 0,
                    "is_pass": 0,
                    "processed_result": f"지원하지 않는 rule_key 입니다: {rule_key or '(empty)'}",
                },
                stdout_data,
            )

        checked = CommandCheck.run(
            stdout_data=stdout_data,
            inspection_criteria=self.params.get("inspection_criteria"),
            criteria_required=rules_class.criteria_required(command),
        )
        if checked is not None:
            return ResultBuild.run(self.params, checked, stdout_data)

        processed = rules_class.run(self.params, stdout_data)
        return ResultBuild.run(self.params, processed, stdout_data)


def build_params(item, result_item, module_params):
    merged_params = dict(item)
    merged_params.update(
        {
            "host": module_params["host"],
            "host_name": module_params["host_name"],
            "report_type": module_params["report_type"],
            "system": module_params["system"],
            "file_path": module_params.get("file_path", ""),
            "result_command": (result_item or {}).get("command", ""),
        }
    )
    return merged_params


def validate_pair(item, result_item):
    label = _item_label(item)

    if not isinstance(result_item, dict):
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": f"명령 결과 형식이 올바르지 않습니다. {label}",
        }

    item_command = (item.get("command") or "").strip()
    result_command = (result_item.get("command") or "").strip()

    if not item.get("rule_key"):
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": f"rule_key 가 선언되지 않았습니다. {label}",
        }

    if not item_command:
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": f"inspection item 에 command 가 선언되지 않았습니다. {label}",
        }

    if not result_command:
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": f"명령 결과에 command 가 없습니다. {label}",
        }

    if item_command != result_command:
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": (
                f"명령 매칭 불일치. inspection='{item_command}', result='{result_command}', "
                f"cmd_id='{item.get('cmd_id', '')}'"
            ),
        }

    if "output" not in result_item:
        return {
            "is_success": 0,
            "is_pass": 0,
            "processed_result": f"명령 결과에 output 이 없습니다. {label}",
        }

    return None


def register_execute(result_items, inspection_items, module_params):
    if len(result_items) != len(inspection_items):
        raise ValueError(
            f"result_items({len(result_items)}) 와 inspection_items({len(inspection_items)}) 개수가 다릅니다."
        )

    results = []
    for index, item in enumerate(inspection_items):
        result_item = result_items[index]
        params = build_params(item, result_item, module_params)
        pair_error = validate_pair(item, result_item)

        if pair_error is not None:
            results.append(
                ResultBuild.run(params, pair_error, (result_item or {}).get("output", ""))
            )
            continue

        handler = RegisterHandler(params)
        results.append(handler.handle(result_item))

    return results


def main():
    from ansible.module_utils.basic import AnsibleModule

    module = AnsibleModule(
        argument_spec=dict(
            result_items=dict(type="list", required=True),
            inspection_items=dict(type="list", required=True),
            host=dict(type="str", required=True),
            host_name=dict(type="str", required=True),
            report_type=dict(type="str", required=True),
            system=dict(type="str", required=True),
            file_path=dict(type="str", required=False, default=""),
        )
    )

    try:
        results = register_execute(
            result_items=module.params["result_items"],
            inspection_items=module.params["inspection_items"],
            module_params=module.params,
        )
        module.exit_json(changed=True, result=results)
    except Exception as err:
        module.fail_json(msg=f"register_handler 실행 중 오류: {err}")


if __name__ == "__main__":
    main()
