import paramiko
import os
import time
import re
from datetime import datetime, timedelta
import select

# 변수
hostname = os.environ.get('hostname', '')
username = os.environ.get('username', '')
password = os.environ.get('password', '')
raw = os.environ.get('raw', '')
port = os.environ.get('port', '')
become_password = os.environ.get('root_passwd', '')
vendor = os.environ.get('vendor', '')
sec = os.environ.get('time', '')

def remove_ansi_escape(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def wait_for_prompt(rlist, target_prompt):
    current_time = datetime.now()
    target_time = current_time + timedelta(seconds=3)
    while datetime.now() < target_time:
        time.sleep(0.1)
        ready, _, _ = select.select([rlist], [], [], 0.1)
        if rlist in ready:
            prompt = rlist.recv(4096).decode('utf-8', 'ignore')  # 새로운 값으로 갱신
            for target_prompts in target_prompt:
                if target_prompts in prompt:
                    return True, prompt
    if datetime.now() >= target_time or ready is None:
        print("프롬프트를 찾을 수 없습니다.")
        return False, None
    
def execute_command(ssh, command):
    ssh.send(command + "\n")
    time.sleep(1)
    output = ssh.recv(65535).decode("utf-8")
    return output

def change_remote_password(hostname, port, username, password, become_password):
    try:
        results = []
        # SSH 클라이언트 생성
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # SSH로 원격 서버에 접속
        client.connect(hostname, port=port, username=username, password=password, timeout=60)

        # root 권한 얻기 위해 su 명령어 실행
        ssh = client.invoke_shell()
        time.sleep(1)

        # root 패스워드 입력
        if become_password != '' and vendor != 'Veritas' and vendor != 'Hitachi':
            ssh.send(b"su -\n")
            time.sleep(1)
            ssh.send(become_password.encode('utf-8') + b'\n')
            time.sleep(1)

        if vendor == 'cisco':
            ssh.send(b"enable\n")
            time.sleep(1)
            ssh.send(password.encode('utf-8') + b'\n')
            time.sleep(1)

        # L3, SDN 터미널 결과값 길이 조절
        if vendor != "axgate" and vendor != "juniper":
            ssh.send(b"terminal length 0\n")
            time.sleep(1)

        if vendor == "axgate":
            ssh.send(password.encode('utf-8') + b'\n')
                
        # 이전 명령어 실행 결과 버퍼 비우기
        while ssh.recv_ready():
            ssh.recv(4096)

        # 명령어 실행 SDN User name 별도를 위한 조건문 수정
        if vendor == "Sdn_controller" and raw == "show username":
            command = "show username ?"
            output = execute_command(ssh, command)
            extracted_values = [value.strip() for value in output.split('\n') if value.strip()]
            for value in extracted_values[1:-3]:
                # 명령어 실행
                ssh.send(f"{raw} {value} detail".encode('utf-8') + b'\n')
                time.sleep(int(sec))  
        else:
            ssh.send(raw.encode('utf-8') + b'\n')
            time.sleep(int(sec))

        # 결과 수집
        result = b''
        while ssh.recv_ready():
            result += ssh.recv(4096)

        # ANSI 이스케이프 시퀀스 제거
        cleaned_result = remove_ansi_escape(result.decode('utf-8'))

        # 결과를 프롬프트를 제외하고 출력
        result_lines = cleaned_result.split('\n')[1:-1]
        print('\n'.join(result_lines))
            
    except Exception as e:
        print(f"오류 발생: {e}")

    finally:
        # SSH 세션 종료
        if client.get_transport() is not None and client.get_transport().is_active():
            client.close()

change_remote_password(hostname, port, username, password, become_password)
