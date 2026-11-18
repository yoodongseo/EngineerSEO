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
become_password = os.environ.get('root_passwd', '')
new_password = os.environ.get('new_passwd', '')
port = os.environ.get('port', '')
change_user = os.environ.get('change_user', '')

#2024 -03-25 추가
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
            # 2024-04-01 다중 조건 추가
            for target_prompts in target_prompt:
                if target_prompts in prompt:
                    return True, prompt
    if datetime.now() >= target_time or ready is None:
        print("프롬프트를 찾을 수 없습니다.")
        return False, None

def change_password(hostname, port, username, password, become_password, change_user, new_password):
    try:
        # SSH 클라이언트 생성 및 연결
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname, port=port, username=username, password=password, timeout=30)
        ssh = client.invoke_shell()
        time.sleep(1)

        # 이전 명령어 실행 결과 버퍼 비우기
        while ssh.recv_ready():
            ssh.recv(4096) 

        # root 패스워드 입력
        ssh.send(b"su -\n")
        time.sleep(1)
        ssh.send(become_password.encode('utf-8') + b'\n')
        
        # SU - 명령어 출력
        recvs = ssh.recv(4096)
        print(recvs.decode('utf-8'))
        # Prompt 값 저장 변수
        results = []

        # "#" 프롬프트 대기
        value, prompt = wait_for_prompt(ssh, ["#",">",":","/"])
        if not value:
            return
        results.append(prompt)

        # passwd 명령어 실행
        ssh.send(f"passwd {change_user}\n".encode('utf-8'))

        # ":" 대기
        value, prompt = wait_for_prompt(ssh, ":")
        if not value:
            return
        results.append(prompt)

        # 새로운 패스워드 입력
        ssh.send(f"{new_password}\n".encode('utf-8'))

        # ":" 대기
        value, prompt = wait_for_prompt(ssh, ":")
        if not value:
            return
        results.append(prompt)

        # 패스워드 재입력
        ssh.send(f"{new_password}\n".encode('utf-8'))

        # "#" 프롬프트 대기
        value, prompt = wait_for_prompt(ssh, ["#",">",":","/"])
        if not value:
            return
        results.append(prompt)

        # root 권한 해제
        ssh.send(b"exit\n")
 
        # 결과 수집
        result = '\n'.join(results) if results else ''

        # ANSI 이스케이프 시퀀스 제거
        cleaned_result = remove_ansi_escape(result)

        # 결과를 프롬프트 제외하고 출력
        result_lines = cleaned_result.split('\n')

        # result_lines --- 명령어 결과를 각각 split한 list 값으로 비교대상 list로 선언
        success_keywords = ["successfully", "완료", "성공"]
        success_flag = False

        # result_lines과 success_keywords를 각각 비교해서 일치하는 배열이 있을경우
        # success_flag 를 True로 변경
        for line in result_lines:
            if any(keyword in line for keyword in success_keywords):
                success_flag = True

        result_line = '\n'.join(result_lines) if result_lines else ''

        # success_flag 가 True 일 경우에 성공
        if success_flag:
            print("결과 :\n", result_line)
            print("패스워드 변경이 완료되었습니다.")
        else:
            print("결과 :\n", result_line)
            print("패스워드 변경 확인이 필요합니다.")

    except Exception as e:
        print(f"오류 발생: {e}")

    finally:
        # SSH 세션 종료
        if client.get_transport() is not None and client.get_transport().is_active():
            client.close()

# 함수 호출
change_password(hostname, port, username, password, become_password, change_user, new_password)
