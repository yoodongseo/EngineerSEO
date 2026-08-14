#!/usr/bin/python
# -*- coding: utf-8 -*-

from ansible.module_utils.basic import AnsibleModule
import paramiko
import socket
import time

def han_command(module, hostname, port, username, password, enable_password, commands, timeout=5, auth_timeout=5):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=hostname, port=port, username=username, password=password, timeout=timeout, auth_timeout=auth_timeout)
        time.sleep(5)
        chan = ssh.invoke_shell()
        chan.send('enable' + "\n")
        time.sleep(1)
        chan.send(enable_password + "\n")
        time.sleep(1)
        output = ""
        for command in commands:
            chan.send(command + "\n")
            time.sleep(1)  # 각 명령어 실행 후 충분한 시간을 줄 수 있도록 sleep 추가
            while chan.recv_ready():
                output += chan.recv(65534).decode("utf-8")
        return output.strip()  # 출력값에서 앞뒤 공백 제거 후 반환

    except paramiko.ssh_exception.AuthenticationException as e:
        module.fail_json(msg=f"Authentication failed: {e}")
    except paramiko.ssh_exception.NoValidConnectionsError as e:
        module.fail_json(msg=f"Connection failed: {e}")
    except socket.gaierror as e:
        module.fail_json(msg=f"Failed to find hostname: {e}")
    except Exception as e:
        module.fail_json(msg=f"Unknown error occurred: {e}")

def main():
    module_args = dict(
        hostname=dict(type='str', required=True),
        port=dict(type='int', default=2022),  # 포트 인자를 추가하고 기본값을 2022로 설정
        username=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        enable_password=dict(type='str', required=True, no_log=True),
        commands=dict(type='list', required=True),  # 여러 개의 명령어를 리스트로 받음
        timeout=dict(type='int', default=5),
        auth_timeout=dict(type='int', default=5)
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    hostname = module.params['hostname']
    port = module.params['port']  # port 인자 추가
    username = module.params['username']
    password = module.params['password']
    enable_password = module.params['enable_password']
    commands = module.params['commands']
    timeout = module.params['timeout']
    auth_timeout = module.params['auth_timeout']

    result = han_command(module, hostname, port, username, password, enable_password, commands, timeout, auth_timeout)

    module.exit_json(changed=False, stdout=result)

if __name__ == '__main__':
    main()