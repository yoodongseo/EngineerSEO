import paramiko
import os
import time
import re
from datetime import datetime, timedelta
import select
import json
import sys

# 변수
hostname = os.environ.get('hostname', '')
username = os.environ.get('username', '')
password = os.environ.get('password', '')
raw = os.environ.get('raw', '')
multi_raw = os.environ.get('multi_raw', '[]') ## List of Dict
port = os.environ.get('port', '')
become_password = os.environ.get('root_passwd', '')
vendor = os.environ.get('vendor', '')
sec = os.environ.get('time', '')
expected_prompt = os.environ.get('prompt', '')

# JSON 데이터를 Python 리스트로 변환
multi_raw = json.loads(multi_raw)

def remove_ansi_escape(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def wait_for_prompt(rlist, target_prompt):
    current_time = datetime.now()
    target_time = current_time + timedelta(seconds=5)
    while datetime.now() < target_time:
        time.sleep(0.1)
        ready, _, _ = select.select([rlist], [], [], 0.1)
        if rlist in ready:
            prompt = rlist.recv(4096)
            try:
                prompt = prompt.decode('utf-8')  # UTF-8로 디코딩 시도
            except UnicodeDecodeError:
                prompt = prompt.decode('euc-kr', 'replace')  # 실패할 경우 EUC-KR로 디코딩
            for target_prompts in target_prompt:
                if target_prompts in prompt:
                    return True, prompt
    if datetime.now() >= target_time or ready is None:
        print(f"프롬프트 로그: : {prompt}") 
        print(f"타겟 프롬프트: : {target_prompt}")
        print("프롬프트를 찾을 수 없습니다.")
        return False, None

def change_remote_password(hostname, port, username, password, become_password):
    try:
        if expected_prompt:
            results = []
        else:
            results = b''
        # SSH 클라이언트 생성
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # SSH로 원격 서버에 접속
        client.connect(hostname, port=port, username=username, password=password, timeout=60)

        # root 권한 얻기 위해 su 명령어 실행
        ssh = client.invoke_shell()
        if expected_prompt:
            ## 프롬프트 대기 사용
            value, prompt = wait_for_prompt(ssh, expected_prompt)
            if not value:
                print("invoke shell 오류")
                sys.exit(1)
        else:
            ## 대기 시간 사용
            time.sleep(int(sec))

        # root 패스워드 입력
        if become_password != '' and vendor != 'Veritas' and vendor != 'Hitachi':
            ssh.send(b"su -\n")
            if expected_prompt:
                ## 프롬프트 대기 사용
                value, prompt = wait_for_prompt(ssh, ["assword","암호"])
                if not value:
                    print("프롬프트 오류")
                    sys.exit(1)
                ssh.send(become_password.encode('utf-8') + b'\n')
            else:
                ## 대기 시간 사용
                time.sleep(int(sec))
                ssh.send(become_password.encode('utf-8') + b'\n')
            ### 전역 sec 대기
            time.sleep(int(sec))

        if vendor == 'cisco':
            ssh.send(b"enable\n")
            time.sleep(1)
            ssh.send(password.encode('utf-8') + b'\n')
            time.sleep(1)

        # L3, SDN 터미널 결과값 길이 조절
        if vendor != "axgate" and vendor != "juniper":
            ssh.send(b"terminal length 0\n")
            time.sleep(1)

        # Juniper length
        if vendor == "juniper":
            ssh.send(b"set cli screen-length 0\n")
            while ssh.recv_ready():
                ssh.recv(8192)
            time.sleep(1)

        if vendor == "axgate":
            ssh.send(password.encode('utf-8') + b'\n')
                
        # 이전 명령어 실행 결과 버퍼 비우기
        while ssh.recv_ready():
            ssh.recv(4096)

        # 명령어 실행 SDN User name 별도를 위한 조건문 수정
        if multi_raw[0] != '':
            for cli in multi_raw: # index: 0,1,2,3,4  cli: 
                # 명렁어 실제 수행
                ssh.send(cli.encode('utf-8') + b'\n')
                if expected_prompt:
                    ## 프롬프트 대기 사용
                    value, prompt = wait_for_prompt(ssh, expected_prompt)
                    if not value:
                        print("프롬프트 오류")
                        sys.exit(1)
                    results.append(prompt)
                else:
                    ## 대기 시간 사용
                    time.sleep(int(sec))
                    while ssh.recv_ready():
                        results += ssh.recv(4096)

        else:
            # ssh.send(raw + '\n')
            ssh.send(raw.encode('utf-8') + b'\n')
            if expected_prompt:
                ## 프롬프트 대기 사용
                value, prompt = wait_for_prompt(ssh, expected_prompt)
                if not value:
                    print("프롬프트 오류")
                    sys.exit(1)
                results.append(prompt)
            else:
                ## 대기 시간 사용
                time.sleep(int(sec))
                while ssh.recv_ready():
                    results += ssh.recv(4096)

        # root 권한 해제
        ssh.send(b"exit\n")
         
        # 결과 수집
        if expected_prompt:
            result = '\n'.join(results) if results else ''
            # ANSI 이스케이프 시퀀스 제거
            cleaned_result = remove_ansi_escape(result)
        else:
            cleaned_result = remove_ansi_escape(results.decode('utf-8'))

        # 결과를 프롬프트 제외하고 출력
        result_lines = cleaned_result.split('\n')[1:-1]
        result_line = '\n'.join(result_lines) if result_lines else ''

        # success_flag 가 True 일 경우에 성공
        print(result_line)
            
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)

    finally:
        # SSH 세션 종료
        if client.get_transport() is not None and client.get_transport().is_active():
            client.close()

change_remote_password(hostname, port, username, password, become_password)

# Try 구문 내에서 sys.exit(1)로 작업이 중단되지 않았을 경우 성공
sys.exit(0)
