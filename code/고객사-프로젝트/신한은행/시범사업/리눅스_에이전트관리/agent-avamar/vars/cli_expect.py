#!/usr/bin/python3
import sys
import paramiko
import time
import os
import json
import re

# ANSI 제어 문자를 제거하는 정규 표현식
ansi_escape = re.compile(r'''
    \x1B  # ESC 문자
    (     # 두 가지 옵션:
        [@-Z\\-_]  # CSI 이스케이프 코드 (단일 문자)
        |          # 또는
        \[ [0-?]* [ -/]* [@-~]  # CSI 이스케이프 시퀀스
    )
''', re.VERBOSE)

username = os.environ.get('username', '')
password = os.environ.get('password', '')
hostname = os.environ.get('hostname', '')
port = os.environ.get('port', '')
command_expect = os.environ.get('command_expect', '[]') ## List of Dict
su_password = os.environ.get('su_password', '')

# JSON 데이터를 Python 리스트로 변환
command_expect = json.loads(command_expect)

# 세션 내용 수집 및 문자 검색 함수
def wait_append_output(channel, output, found, timeout):
    end_time = time.time() + timeout
    while time.time() < end_time:
        if channel.recv_ready():
            recv_bytes = channel.recv(4096)
            output_data = recv_bytes.decode('utf-8')
            output.append(output_data)  # 새로운 출력 누적

            # 1. found가 None이 아닌 경우에만 검증 수행
            if found is not None:  # found가 문자열인 경우
                if isinstance(found, str):  
                    if found in output_data:
                        return True
                else: # found가 리스트인 경우의 처리
                    for target_string in found:  # found가 리스트인 경우
                        if target_string in output_data:
                            return True
        # time.sleep(0.1)
    
    # 2. 세션에서 찾지 못했을때 output 리스트의 마지막 요소에서 문자열 검증
    if found is not None and output:
        last_output = output[-1]  # 가장 마지막 요소를 가져옴
        
        if isinstance(found, str):  
            if found in last_output:
                return True
        else:  
            for target_string in found:
                if target_string in last_output:
                    return True
    
    # 타임아웃이 지나고도 검증되지 않으면 False 반환
    return False

# 에러 출력 및 작업 종료 함수
def check_and_exit(result, output, error_message):
    if not result:
        clean_output = ansi_escape.sub('', ''.join(output))  # 제어 문자 제거
        print(clean_output)
        print(f"err_msg: {error_message}")
        sys.exit(1)  # 작업 중단
        
# SSH 클라이언트 설정 및 연결
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    # 서버에 연결
    client.connect(hostname=hostname, port=port, username=username, password=password)
    channel = client.invoke_shell()

    # output 리스트 변수 선언
    output = []

    # 1. 초기 프롬프트 대기
    result_wait = wait_append_output(channel, output, ["]$", "]#"], timeout=3)
    # result_wait = wait_append_output(channel, output, ["$", "#"], timeout=3)  ## 임시 주석 처리 진행, 프롬프트 문자열 패턴은 보완 필요
    check_and_exit(result_wait, output, "Prompt not found.")  

    # 2. root 계정 처리
    if su_password:
        channel.send("su -\n")
        result_wait = wait_append_output(channel, output, ["assword:", "암호"], timeout=3)
        check_and_exit(result_wait, output, "Password prompt not found.")

        channel.send(f"{su_password}\n")
        result_wait = wait_append_output(channel, output, ["]#"], timeout=3)
        # result_wait = wait_append_output(channel, output, ["#"], timeout=3)  ## 임시 주석 처리 진행, 프롬프트 문자열 패턴은 보완 필요 
        check_and_exit(result_wait, output, "Failed to switch to root user.")
    
    # 3. 명령어 수행
    for index, cli_list in enumerate(command_expect['cmd']):
        cli_command = cli_list['cli']

        # 두번째 명령 부터는 프롬프트 점검
        if index > 0:
            result_wait = wait_append_output(channel, output, ["]#"], timeout=10)
            # result_wait = wait_append_output(channel, output, ["#", "$", ">"], timeout=10)  ## 임시 주석 처리 진행, 프롬프트 문자열 패턴은 보완 필요
            check_and_exit(result_wait, output, "Prompt not found.")

        # 명렁어 실제 수행
        channel.send(cli_command + '\n')

        # 4. 대화형 처리 (세션에 특정 문자열 찾기)
        for found_list in cli_list['found_list']:
            found = found_list['found']
            answer = found_list['answer']

            # 대화형 처리 대상이 아닌경우 스킵
            if not found:
                wait_append_output(channel, output, None, timeout=1)
                break

            # 대화형 키워드 검색
            result_wait = wait_append_output(channel, output, found, timeout=3)
            check_and_exit(result_wait, output, f"Not found keyword: {found}")
            
            # 세션에 응답 전송
            if answer == 'Enter':
                channel.send('\n')
                wait_append_output(channel, output, None, timeout=1)
            else:
                channel.send(answer + '\n')
                wait_append_output(channel, output, None, timeout=1)

    # 5. 메세지 OUTPUT
    # 제어 문자를 제거한 후 출력
    clean_output = ansi_escape.sub('', ''.join(output))  # 제어 문자 제거
    print(clean_output)

except paramiko.AuthenticationException:  
    print("Authentication error: Invalid SSH login credentials.")
except paramiko.SSHException as ssh_error:  
    print(f"SSH connection error: {ssh_error}")
except Exception as e:  
    print(f"An unknown error occurred: {e}")
finally:
    client.close()

# Try 구문 내에서 sys.exit(1)로 작업이 중단되지 않았을 경우 성공
sys.exit(0)
