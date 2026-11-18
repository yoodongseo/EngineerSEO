#!/usr/bin/python

import sys
sys.path.append('/fap/ansible/projects/custom_modules/ansible_collections/fap/custom/plugins/modules')

from ansible.module_utils.basic import AnsibleModule
from filters import filter_registry   # __init__.py 에서 가져옴


def filter_execute(stdout_lines, inspection_items, host, host_name,
                   report_type, system, file_path, sid=None):

    results = []

    for index, item in enumerate(inspection_items):
        stdout_data = stdout_lines[index]

        merged_params = dict(item)
        merged_params.update({
            'host': host,
            'host_name': host_name,
            'report_type': report_type,
            'system': system,
            'file_path': file_path,
            'sid': sid
        })

        # 키워드 탐색 → 필터 자동 선택
        matched_filter = None
        for keyword, filter_class in filter_registry.items():
            #if keyword.lower() in item['name'].lower():
            if keyword.lower() == item['filter_key'].lower():
                matched_filter = filter_class
                break

        if matched_filter:
            result = matched_filter(merged_params).evaluate(stdout_data)
        else:
            result = {
                'cmd_id': item.get('cmd_id'),
                'host': host,
                'host_name': host_name,
                'name': item.get('name'),
                'command': item.get('command'),
                'report_type': item.get('report_type'),
                'system': item.get('system'),
                'message': '지원하지 않는 점검 항목',
                'inspection_criteria': item.get('inspection_criteria'),
                'file_path': '',
                'is_pass': 0,
                'is_success': 0,
                'result': 'Unknown check'
            }

        results.append(result)

    return results


def main():
    module_args = dict(
        stdout_lines=dict(type='list', required=True),
        inspection_items=dict(type='list', required=True),
        host=dict(type='str', required=True),
        host_name=dict(type='str', required=True),
        report_type=dict(type='str', required=True),
        system=dict(type='str', required=True),
        file_path=dict(type='str', required=True),
        sid=dict(type='str', required=False)
    )

    module = AnsibleModule(argument_spec=module_args)

    stdout_lines = module.params['stdout_lines']
    inspection_items = module.params['inspection_items']
    host = module.params['host']
    host_name = module.params['host_name']
    report_type = module.params.get('report_type')
    system = module.params.get('system')
    file_path = module.params.get('file_path')
    sid = module.params.get('sid')

    try:
        results = filter_execute(
            stdout_lines,
            inspection_items,
            host,
            host_name,
            report_type,
            system,
            file_path,
            sid
        )
        module.exit_json(changed=True, result=results)

    except Exception as e:
        module.fail_json(msg=f'필터 실행 중 오류: {str(e)}')


if __name__ == '__main__':
    main()
