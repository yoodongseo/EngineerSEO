import paramiko
import os
import time
import re
from datetime import datetime, timedelta
import select
import logging

# 로깅 활성화
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("paramiko")
logger.setLevel(logging.DEBUG)

# 변수
hostname = os.environ.get('hostname', '')
username = os.environ.get('username', '')
password = os.environ.get('password', '')
become_password = os.environ.get('root_passwd', '')
port = os.environ.get('port', '')

#2024 -03-25 추가
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

def change_password(hostname, port, username, password, become_password):
    try:
        # 결과를 저장할 변수 정의
        results = []

        # SSH 클라이언트 생성 및 연결
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, timeout=30)
        ssh = client.invoke_shell()
        value, prompt = wait_for_prompt(ssh, ["$","#",">",":"])
        if not value:
            print("접속오류")
            return

        # root 패스워드 입력
        ssh.send(b"su -\n")

        # 프롬프트 대기
        value, prompt = wait_for_prompt(ssh, ["assword","암호"])
        if not value:
            print("패스워드 프롬프트 인식오류")
            return
        # results.append(prompt)

        ssh.send(become_password.encode('utf-8') + b'\n')

        # 데이터를 수신하여 인코딩을 결정
        recvs = ssh.recv(4096)
        try:
            decoded_result = recvs.decode('utf-8')
        except UnicodeDecodeError:
            decoded_result = recvs.decode('euc-kr', errors='replace')
            decoded_result = decoded_result.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        
        # 이전 명령어 실행 결과 버퍼 비우기
        while ssh.recv_ready():
            ssh.recv(4096) 

        # "#" 프롬프트 대기
        value, prompt = wait_for_prompt(ssh, ["~","]",">","#"])
        if not value:
            print("su - 전환 후")
            return
        # results.append(prompt)

        # passwd 명령어 실행
        ssh.send(f"hostname\n".encode('euc-kr').decode('utf-8', 'ignore'))

        # "#" 프롬프트 대기
        value, prompt = wait_for_prompt(ssh, ["~","]",">","#"])
        if not value:
            print("명령어 입력 후")
            return
        results.append(prompt)

        # root 권한 해제
        ssh.send(b"exit\n")
 
        # 결과 수집
        result = '\n'.join(results) if results else ''

        # ANSI 이스케이프 시퀀스 제거
        cleaned_result = remove_ansi_escape(result)

        # 결과를 프롬프트 제외하고 출력
        # result_lines = cleaned_result.split('\n')
        result_lines = cleaned_result.split('\n')[1:-1]
        result_line = '\n'.join(result_lines) if result_lines else ''

        # success_flag 가 True 일 경우에 성공
        print(result_line)

    except Exception as e:
        print(f"오류 발생: {e}")

    finally:
        # SSH 세션 종료
        if client.get_transport() is not None and client.get_transport().is_active():
            client.close()

# 함수 호출
change_password(hostname, port, username, password, become_password)