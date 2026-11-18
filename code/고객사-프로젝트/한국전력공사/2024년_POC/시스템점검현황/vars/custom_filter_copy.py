import psutil
import json
import os
import re
import textwrap

# 환경 변수에서 필요한 값들을 가져옴
host = os.environ.get('host', '')
host_name = os.environ.get('host_name', '')
name = os.environ.get('name', '')
command = os.environ.get('command', '')
report_type = os.environ.get('report_type', '')
system = os.environ.get('system', '')
total_items = os.environ.get('total_item', '')
com_value = os.environ.get('com_value', '')
copy = os.environ.get('copy', '')
inspection_criteria = os.environ.get('criteria', '')
# 함수를 사용하여 CPU 또는 Memory 정보를 가져오고 결과를 반환
def get_usage_info(copy, total_items):
    source = ''
    destinations = []
    success_count = 0
    fail_count = 0
    is_pass = 0
    if total_items:
          total_item = f"{total_items}"
    else:
          return {
                'is_pass': '0',
                'file_path': '불량',
                'result': "명령어 수행 결과가 없습니다."
          }
    match copy:
        case 'Netapp':
            sources = []
            for line in total_item.split('\n'):
                if "svm1:" in line:  # svm1 라인인 경우
                        # ":" 다음의 데이터를 가져와 source 변수에 저장
                        lines = re.split(r'[:\s\t]+', line.strip())
                        sources.append(lines[1])
                        # source_value = source[int(1)]
                        # print(f"source_value", source_value)
                if "nas_data_svm_dr" in line:
                    # ":" 다음의 데이터를 가져와 destination 변수에 저장
                        lines = re.split(r'[:\s\t]+', line.strip())
                        destinations.append(lines[4])
                if "true" in line:  # Snapmirrored InSync 문자열이 있는 경우
                        is_pass = 1
                        success_count += 1
                if com_value in line: # Snapmirrored InSync 문자열이 있는 경우
                        is_pass = 0
                        fail_count += 1
                else:
                    pass
            result = textwrap.dedent(f"""\
                복제 카운트: {success_count + fail_count}
                복제 성공: {success_count}
                복제 실패: {fail_count}""")
            source = '\n'.join(sources) if sources else ''
            destination = '\n'.join(destinations) if destinations else ''
        case "Veritas":
            copy_result = []
            piece_copy_result = []
            fail_copy_result = []
            lines = total_item.strip().split('\n')
            for line in lines[3:]:
                parts = line.split()
                try:
                    # 3번째 배열이 int로 변환 가능한지 확인
                    status_value_3rd = int(parts[3])
                    if status_value_3rd == 0:
                        copy_result.append(line)
                    elif status_value_3rd == 1:
                        piece_copy_result.append(line)
                    else:
                        fail_copy_result.append(line)
                except (ValueError, IndexError):
                    try:
                        # 4번째 배열이 int로 변환이 가능한지 확인
                        status_value_4th = int(parts[4])
                        if status_value_4th == 0:
                            copy_result.append(line)
                        elif status_value_4th == 1:
                            piece_copy_result.append(line)
                        else:
                            fail_copy_result.append(line)
                            is_pass = '0'
                    except (ValueError, IndexError):
                        fail_copy_result.append(line)
            copy_results = "\n".join(copy_result)
            piece_copy_results = "\n".join(piece_copy_result)
            fail_copy_results = "\n".join(fail_copy_result)
            result = f"""\
            복제 성공: 
            {copy_results}

            복제 부분 성공: 
            {piece_copy_results}"""

            if fail_copy_results:
                result += f"""
            복제 실패: 
            {fail_copy_results}"""
        case "Ibm":
            if total_item == "consistent_copying":
                is_pass = '1'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 일치 복제 중"""
            elif total_item == "inconsistent_stopped":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 불일치 중지 상태"""
            elif total_item == "inconsistent_copying":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 불일치 복제 중"""
            elif total_item == "consistent_stopped":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 일치 중지 상태"""
            elif total_item == "consistent_synchronized":
                is_pass = '1'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 일치 복제 완료"""
            elif total_item == "idling":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 유휴 상태"""
            elif total_item == "idling_disconnected":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 유휴 복제 끊김 상태(비정상 상태)"""
            elif total_item == "inconsistent_disconnected":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 불일치 복제 끊김 상태(비정상 상태)"""
            elif total_item == "consistent_disconnected":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 일치 복제 끊김 상태(비정상 상태)"""
            elif total_item == "empty":
                is_pass = '0'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 복제 관계가 비어있는 상태"""
            else:
                is_pass = 'none'
                result = f"""\
                복제 상태 결과:
                {total_item}
                - 기준 값이 없습니다(확인 필요)"""
                 

    #   1. consistent_copying – 일치 복제 중
    #   2. inconsistent_stopped – 불일치 중지 상태
    #   3. inconsistent_copying – 불일치 복제 중
    #   4. consistent_stopped – 일치 중지 상태
    #   5. consistent_synchronized – 일치 복제 완료
    #   6. idling – 유휴 상태
    #   7. idling_disconnected – 유휴 복제 끊김 상태(비정상 상태)
    #   8. inconsistent_disconnected – 불일치 복제 끊김 상태(비정상 상태)
    #   9. consistent_disconnected – 일치 복제 끊김 상태(비정상 상태)
    #   10. empty – 복제 관계가 비어있는 상태 
            
            
    is_success = "양호" if total_item is not None else "불량"
    
    if source != '':
        return {
            'before_data': source,
            'after_data': destination,
            'file_path': is_success,
            'is_pass': is_pass,
            'result': result
        }
    else:
        return {
            'before_data': host,
            'after_data': host,
            'file_path': is_success,
            'is_pass': is_pass,
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
    'inspection_criteria': inspection_criteria,
}

merged_value.update(get_usage_info(copy, total_items))

# 결과를 출력
print(json.dumps(merged_value, ensure_ascii=False))