import requests
import json
from datetime import datetime, timedelta

# SSL 경고 무시
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 로그 검색 시작 함수
def start_log_search(api_url, api_token, filters, columns, start_time, end_time):
    headers = {
        'Authorization': api_token,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    data = {
        'filters': filters,
        'columns': columns,
        'stime': start_time,
        'etime': end_time,
        'order_by': 'asc',
        'log_type': 'your_log_type'
    }

    response = requests.post(f'{api_url}/lr/log/start', headers=headers, data=json.dumps(data), verify=False)
    
    # 요청이 성공했는지 확인
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP 에러 발생: {err}")
        return None

    return response.json()['result']['request_id']

# 로그 검색 상태 확인 함수
def get_log_status(api_url, api_token, request_id):
    headers = {
        'Authorization': api_token,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    response = requests.get(f'{api_url}/lr/log/{request_id}/status', headers=headers, verify=False)
    
    # 요청이 성공했는지 확인
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP 에러 발생: {err}")
        return None

    return response.json()

# 로그 결과 가져오는 함수
def fetch_log_results(api_url, api_token, request_id, start, end):
    headers = {
        'Authorization': api_token,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
    }

    response = requests.get(f'{api_url}/lr/log/{request_id}/page/{start}/to/{end}', headers=headers, verify=False)
    
    # 요청이 성공했는지 확인
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        print(f"HTTP 에러 발생: {err}")
        return None

    return response.json()['result']['log']

# 메인 함수
def main():
    api_url = 'https://your-api-url/api'
    api_token = 'your_api_token'

    # 필터와 컬럼 정의
    filters = [
        {
            'key': 'Application Control',
            'value': ['http', 'https'],
            'is_not': False
        },
        {
            'key': 'User Authentication',
            'value': ['user1', 'user2'],
            'is_not': False
        },
        {
            'key': 'File Format Control',
            'value': ['pdf', 'docx'],
            'is_not': False
        }
    ]
    columns = ['time', 'mach_id', 'cpu_usage']

    # 7일 전부터 현재까지의 시간 계산
    end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    start_time = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    # 로그 검색 시작
    request_id = start_log_search(api_url, api_token, filters, columns, start_time, end_time)
    if request_id is None:
        return
    
    # 검색 상태 확인
    status = get_log_status(api_url, api_token, request_id)
    if status is None:
        return
    
    while status['result']['status'] != 'DONE':
        status = get_log_status(api_url, api_token, request_id)
        if status is None:
            return

    # 로그 결과 가져오기
    logs = fetch_log_results(api_url, api_token, request_id, 0, 100)  # 범위 조정 가능
    if logs is not None:
        for log in logs:
            print(log)

if __name__ == '__main__':
    main()
