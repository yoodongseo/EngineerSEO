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

#python 테스트
# hostname = '192.168.1.55' 
# username = 'admin'
# password = 'admin'
# raw = 'show environment'
# port = '22'
# become_password = 'admin'
# vendor = 'Cisco'
# sec = '1'




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

def command_line(hostname, port, username, password, become_password):
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
        
        if become_password != '' and vendor == 'Cisco':
            ssh.send(b"enable \n")
            time.sleep(1)
            ssh.send(become_password.encode('utf-8') + b'\n')
            time.sleep(1)            

        # root 패스워드 입력
        if become_password != '' and vendor != 'Veritas' and vendor != 'Hitachi' and vendor != 'Cisco':
            ssh.send(b"su -\n")
            time.sleep(1)
            ssh.send(become_password.encode('utf-8') + b'\n')
            time.sleep(1)
        
        if vendor == 'Hitachi':
            value, prompt = wait_for_prompt(ssh, "$")
            if not value:
                return
            # \x03 --- ctrl + c 전송
            ssh.send("\x03")
            time.sleep(1)  # 1초 대기
            ### bash 진입 성공 유무 확인
            value, prompt = wait_for_prompt(ssh, "bash")
            if not value:
                return

        # Veritas 장비 로그인 방식
        if vendor == 'Veritas':
            ssh.send(b"\n")
            value, prompt = wait_for_prompt(ssh, ["login:",">"]) ### "#" 추가 필요
            if not value:
                ### 로그인 오류 세션 종료
                ssh.send("exit".encode('utf-8') + b'\n')
                return
            if "login:" in prompt:
                ### admin 로그인
                ssh.send("admin".encode('utf-8') + b'\n')
                time.sleep(1)
                ssh.send(password.encode('utf-8') + b'\n')
                time.sleep(8)
            elif ">" in prompt:
                ### 이전 세션에서 Maintenance 에서 종료된 상태
                pass
            else: 
                ### 현재까지 예상된 프롬프트 없음 // 작업종료
                return
            ### admin 로그인 성공 Support -> Maintenance -> su 입력
            ssh.send("Support".encode('utf-8') + b'\n')
            time.sleep(1)
            ssh.send("Maintenance".encode('utf-8') + b'\n')
            time.sleep(2)
            ssh.send(password.encode('utf-8') + b'\n')
            time.sleep(2)
            ssh.send("su".encode('utf-8') + b'\n')
            time.sleep(1)
            ssh.send(password.encode('utf-8') + b'\n')
            ### Veritas장비 잔여 버퍼 존재, 1차 버퍼 비우기
            while ssh.recv_ready():
                ssh.recv(4096)
                time.sleep(0.1)  # 버퍼가 완전히 비워졌는지 확인하기 위해 잠시 대기
            
### 조건 추가 --- 현재 Veritas 장비 로그인 시 login 이 return될 수도 있으며, 프롬프트가 나올수도 있음

        # L3, SDN 터미널 결과값 길이 조절
        if vendor == "L3" or vendor == 'L3_aruba' or vendor == "Cisco" or vendor == "Sdn_controller" or vendor == "Sdn_switch":
            ssh.send(b"terminal length 0\n")
            time.sleep(1)

        if vendor == "L3_hp":
            ssh.send(b"screen-length disable\n")
            time.sleep(1)

        # L4 터미널 결과값 길이 조절
        if vendor == "L4":
            ssh.send(b"configure\n")
            time.sleep(1)
            ssh.send(b"terminal length 0\n")
            time.sleep(1)

        # Netapp 설정
        if vendor == "Netapp":
            ssh.send(b"set -rows 0\n")
            time.sleep(1)
        
        # Axgate 설정
        if vendor == "Axgate":
            ssh.send(password.encode('utf-8') + b'\n')

                
        # 이전 명령어 실행 결과 버퍼 비우기
        while ssh.recv_ready():
            ssh.recv(65536)

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
            result += ssh.recv(65536)

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

command_line(hostname, port, username, password, become_password)
