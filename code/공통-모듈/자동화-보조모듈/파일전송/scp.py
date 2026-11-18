import pexpect
import os

local_file = os.environ.get('script_path', '')
remote_file = os.environ.get('output_path', '')
remote_host = os.environ.get('host_ip')
remote_user = os.environ.get('user', '')
remote_password = os.environ.get('password', '')
port = os.environ.get('port', '')

# SCP 명령어 실행
command = f'scp -P{port} {local_file} {remote_user}@{remote_host}:{remote_file}'

try:
    # SCP 명령어 실행 및 expect로 패스워드 입력
    child = pexpect.spawn(command)
    
    # "connecting 프롬프트 대기"
    index = child.expect(['continue connecting', pexpect.TIMEOUT], timeout=3)

    # connecting 안나오면 패스
    if index == 0:
        child.sendline('yes')

    child.expect('password:')
    child.sendline(remote_password)
    child.expect(pexpect.EOF)
    print("파일 전송 완료")
except pexpect.ExceptionPexpect as e:
    print("파일 전송 중 오류 발생:", e)
