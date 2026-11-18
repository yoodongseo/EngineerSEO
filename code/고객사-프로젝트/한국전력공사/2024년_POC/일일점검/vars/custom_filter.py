import psutil
import json
import os
import re

# 환경 변수에서 필요한 값들을 가져옴
host = os.environ.get('host', '')
host_name = os.environ.get('host_name', '')
name = os.environ.get('name', '')
command = os.environ.get('command', '')
report_type = os.environ.get('report_type', '')
system = os.environ.get('system', '')
message = os.environ.get('message', '')
total_items = os.environ.get('total_item', '')
com_value = os.environ.get('com_value', '')
form_value = os.environ.get('value', '')
arr_num = os.environ.get('arr_num', '')
inspection_criteria = os.environ.get('criteria', '')
grep = os.environ.get('grep', '')
unit = os.environ.get('unit', '')
raw = os.environ.get('raw', '')

# 함수를 사용하여 점검 결과값을 가져오고 결과를 반환
def get_usage_info(form_value, total_items):
    if total_items:
            total_item = f"{total_items}"
    else:
        return {
            'is_pass': 'none',
            'is_success': '0',
            'result': f"명령어:\n{raw}\n명령어 수행 결과가 없습니다.\n점검 기준 확인 필요합니다."
        }
    fail_items = []
    match form_value:
        # 숫자 비교
        case 'int':
            is_pass = '1' if float(total_item) < float(com_value) else '0'
            fail_item = 'fail' if is_pass == '0' else ''
        # 문자열 비교(grep)
        case 'str':
            is_pass = '1'
            for line in total_item.split('\n'):
                for cv in com_value.split('\n'):
                    if cv.strip():  # 빈 문자열이 아닐 때만 실행
                        if cv.strip() in line and line not in fail_items:  # 대소문자 구분 없이 비교
                            fail_items.append(line)
                            is_pass = '0'
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 행 출력 후 com_value가 포함되지 않으면 Fail
        case 'notstr':
            is_pass = '1'
            grep_found = False
            for line in total_item.split('\n'): 
                for cv in com_value.split('\n'):
                    if grep:
                        if grep in line:
                            grep_found = True
                            if cv.strip():  # 빈 문자열이 아닐 때만 실행
                                if cv.strip() not in line and line not in fail_items:  # 대소문자 구분 없이 비교
                                    fail_items.append(line)
                                    is_pass = '0'
            if not grep_found:
                fail_items = ["설정된 값이 존재하지 않습니다."]
                is_pass = '0'
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 리스트형 문자열 비교(행별 grep)
        case 'list_str':
            is_pass = '1'
            lines = total_item.split('\n')
            if lines:
                # 첫 번째 라인을 건너뜁니다.
                lines = lines[1:]
                for line in lines:
                    data_info = re.split(r'[:\s]+', line)  # 행 별 데이터를 :, 공백 기준으로 분리
                    data_name = data_info[int(arr_num)]  # arr_num 배열 수를 기준으로 비교 설정
                    if data_name in com_value:
                        fail_items.append(line)
                        is_pass = '0'
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 리스트형 문자 분리 후 비교
        case 'list_int':
            is_pass = '1'
            lines = total_item.split('\n')
            for line in lines:
                # 주석이면 건너뜁니다.
                if line.strip().startswith('#'):
                    continue
                data_info = re.split(r'[:\s\t]+', line.strip())  # 행 별 데이터를 : 기준으로 분리
                data_name = data_info[int(arr_num)].rstrip(unit) # arr_num 배열 수를 기준으로 비교 설정
                try:
                    data_value = float(data_name)  # 데이터를 실수로 변환합니다.
                    if float(data_value) > float(com_value):
                        fail_items.append(line)
                        is_pass = '0'
                except ValueError:
                    # 숫자로 변환할 수 없는 경우는 건너뜁니다.
                    pass
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 배열 숫자 정확한 일치할 때
        case 'list_sameint':
            is_pass = '1'
            lines = total_item.split('\n')
            for line in lines:
                # 공란이면 건너뜁니다.
                if not line.strip():
                    continue
                # 주석이면 건너뜁니다.
                if line.strip().startswith('#'):
                    continue
                data_info = re.split(r'[:\s\t]+', line.strip())  # 행 별 데이터를 : 기준으로 분리
                data_name = data_info[int(arr_num)].rstrip(unit) # arr_num 배열 수를 기준으로 비교 설정
                for cv in com_value.split('\n'):
                    if not cv.strip():  # com_value 공란인 경우 건너뜁니다.
                        continue
                    try:
                        data_value = float(data_name)  # 데이터를 실수로 변환합니다.
                        if float(data_value) == float(cv):
                            fail_items.append(line)
                            is_pass = '0'
                    except ValueError:
                        # 숫자로 변환할 수 없는 경우는 건너뜁니다.
                        pass
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 기준별로 잘라서 특정 내용 비교
        case 'line_str':
            for line in range(0, len(lines), 4):
                if lines[line+1].strip().split(':')[1].strip() == 'down' and lines[line+2].strip().split(':')[1].strip() == com_value:
                    fail_items.append('\n'.join(lines[line:line+4]))
            fail_item = '\n'.join(fail_items) if fail_items else ''
        # 실패 기준이 없는 점검항목 처리
        case 'check':
            is_pass = 'none'
            fail_item = total_item if is_pass != 'none' else ''

    # 점검 성공유무 확인 > total_item 변수 미 정의 시 실패 판단
    is_success = '1' if total_item is not None else '0'

    # output data 삽입
    result = f"{name.capitalize()} Total:\n{total_item}\n"
    if fail_item:
        result += f"\nFail Total:\n{fail_item}"

    return {
        'is_pass': is_pass,
        'is_success': is_success,
        'result': result
    }

# 각각의 정보를 merged_value에 추가
merged_value = {
    'host': host,
    'host_name': host_name,
    'name': name,
    'command': command,
    'report_type': report_type,
    'system': system,
    'message': message,
    'inspection_criteria': inspection_criteria,
}

# if name and total_items:
merged_value.update(get_usage_info(form_value, total_items))

# 결과를 출력
print(json.dumps(merged_value, ensure_ascii=False))