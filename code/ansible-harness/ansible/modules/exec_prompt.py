#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2024 www.rtnet.co.kr
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

ANSIBLE_METADATA = {
  "metadata_version": "0.10.1",
  "status": ["stableinterface"],
  "supported_by": "community",
}

DOCUMENTATION = """
---
module: exec_prompt 
author:
- Eunhwa Sim (eh.sim@rtnet.co.kr)
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: A module to receive input from the user for values ??required to execute commands during playbook execution. 
description:
- This module is a module that receives input values ??from the user to use in executing commands during Playbook execution.
  You must declare the 'delegate_to = localhost' and 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
options:
  fap_vars:
    description:
    - Input FAP variables. {{ fap }}
    required: True
  ip:
    description:
    - Input target ip.
    required: True
  ssh_port:
    description:
    - Define the ssh port (default=22)
    required: false
    default: 22
  telnet_port:
    description:
    - Define the telnet port (default=23)
    required: false
    default: 23
  is_input:
    description:
    - User Input Flag 
    required: False 
  command:
    description:
    - Input command list.
    required: True
  user_id:
    description:
    - Input user id
    required: False
  user_password:
    description:
    - Input user password
    required: True
  become_method:
    description:
    - Input become method (su, enable, super, ...)
    required: False
  become_password:
    description:
    - Input become password
    required: False
"""

EXAMPLES = """
- fap.common.exec_prompt:
    fap_vars: "{{ fap }}"
    ip: "{{ fap.host_ip | default('') }}"
    ssh_port: 22
    telnet_port: 23
    is_input : false 
    command: "{{ command_list }}"
    user_id: "{{ ansible_user | default('') }}"
    user_password: "{{ ansible_password | default('') }}"
    become_method: "{{ ansible_become_method | default('') }}"
    become_password: "{{ ansible_become_password | default('') }}"
  delegate_to: localhost
"""

RETURN = """
result:
  description: Result data
  type: dict
  returned: always
"""


from ansible.module_utils.basic import AnsibleModule

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP 
from ansible_collections.fap.common.plugins.module_utils.fap_client_ssh import FapSshClient
from ansible_collections.fap.common.plugins.module_utils.fap_client_telnet import FapTelnetClient
from ansible_collections.fap.common.plugins.module_utils.fap_client_prompt import FapPromptClient

import sys, os, datetime, json, logging
import datetime
import os.path
import json
import time
import string
import random
import configparser


from io import StringIO

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text

HAS_HTTPLIB2 = True
try:
    import httplib2
except:
    HAS_HTTPLIB2 = False

logger = logging.getLogger(__name__)


def createUUID() :
  _LENGTH = 4
   
  string_pool = string.ascii_uppercase 
  result = "REQPRMT"
  now = datetime.datetime.now()

  result += now.strftime('%Y%m%d%H%M%S')

  for i in range (_LENGTH):
    result += random.choice(string_pool)
  
  return result

def checkCommandList(command_list):

  if command_list is None: 
    return None
  
  cmd_idx = 1 
  final_command_list = [] 
  for sub_command in command_list:
    cmd_type = type(sub_command)
    if isinstance(sub_command, str): 
      cmd_items = command_list.get(sub_command)
      final_command_list.append(createCommandList(cmd_items))  
    elif isinstance(sub_command, list):
      for sub_item in sub_command:
        if isinstance(sub_item['command'], list):
          for temp_cmd in sub_item['command']:
            temp_item = {} 
            temp_item['command'] = temp_cmd 
            temp_item['cmd_idx'] = cmd_idx 
            cmd_idx += 1
            temp_item['cmd_id'] = createSubCommandID(temp_item) 
            if sub_item['is_input'] is not None : 
              temp_item['is_input'] = sub_item['is_input']
            final_command_list.append(temp_item)
        else:
          sub_item['cmd_idx'] = cmd_idx 
          cmd_idx  += 1 
          sub_item['cmd_id'] = createSubCommandID(sub_item)
          final_command_list.append(sub_item)
    else:
      if sub_command.get('cmd_idx') is None:
        sub_command['cmd_idx'] = cmd_idx 
        cmd_idx += 1
        sub_command["cmd_id"] = createSubCommandID(sub_command)
      else:
        sub_command["cmd_id"] = createSubCommandID(sub_command)
        if sub_command.get('command') is None:
          raise ValueError("command must be define")
      final_command_list.append(sub_command)

  #  logger.info(f'## TEST : final_command_list : {final_command_list}')
  
  return final_command_list

def createCommandList(sub_command):

  #cmd_items = command_list.get(sub_command).keys()

  cmd_list = [] 
  list_len = len(sub_command)
  index = 1
  for cmd in sub_command:
    cmd_item = {} 
    cmd_item['cmd_idx'] = index
    cmd_item['command'] = cmd
    cmd_item['cmd_id'] = createSubCommandID(cmd_item)
    cmd_item['is_input'] = False

    index += 1

    cmd_list.append(cmd_item)

  return cmd_list

def createSubCommandID(sub_command):

  _LENGTH = 4

  if sub_command is None:
    return None
  
  cmd_idx =  sub_command.get('cmd_idx')
  command_id = str(cmd_idx)
  
  for i in range(_LENGTH):
    if len(command_id) < _LENGTH:
      command_id = '0'+command_id
    else:
      break

  command_id = 'PRMT_CMD_'+command_id 

  return command_id


def sendPromptCommandStart(url, api_token, params, is_connect):
  
  sendData = {} 
  sendData['req_id'] = FAP.getDicValue(params, 'req_id', None)
  sendData['job_id'] = FAP.getDicValue(params, 'job_id', None)
  sendData['host_ip'] = FAP.getDicValue(params, 'ip', None)
  sendData['cmd_idx'] = 1
  sendData['prompt_idx'] = 0
  sendData['is_connect'] = is_connect
  sendData['is_input'] = FAP.getDicValue(params, 'is_input', None)
  sendData['output'] = 'Start'

  content= sendRequest(url, 'POST',api_token, sendData)
  
  if content is not None : 
    return True
  else:
    return False

def checkPromptProcessEnd(client, config, req_id, job_id): 

    cmd_is_finished = False

    time_diff = 0
    start_time = datetime.datetime.now()
    timeout_min = start_time + datetime.timedelta(minutes=10)

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')
    
    logger.debug(f'----> checkPromptProcessEnd Start ')
    
    while cmd_is_finished == False:
    
      # Check session is closed
      if client == None or client.isConnected() == False: break
    
      sendData = {}
      sendData['req_id'] = req_id
      sendData['job_id'] = job_id
              
      url = api_url + '/api/fap_common/prompt/search'
       # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
            
      # Make header
      headers = {'Cache-Control':'no-cache','Connection':'close', 'x-auth-token':'Bearer '+api_token}

      # Send request
      get_content = None
      time.sleep(0.1)
      try:
        resp, get_content = http.request(uri=url, method='GET', headers=headers, body=json.dumps(sendData))
      except Exception as err:
        logger.exception(err)
        get_content = None
              
      if get_content is not None:
        prompt_data = json.loads(get_content)
      
        # Wait if the is_finished value is 0, and proceed if it is 1
        if prompt_data['data']['prompt']['is_finished'] == 1:
          cmd_is_finished = True
        # Stop if the prompt host's status is 'T'
        elif prompt_data['data']['prompt']['status'] == 'T':
          cmd_is_finished = True
        else:
          now_time = datetime.datetime.now()
          if now_time > timeout_min :
            cmd_is_finished = False
            break
    
      if cmd_is_finished == False:
        time.sleep(5)
    
    logger.debug(f'----> checkPromptProcessEnd End : result : {cmd_is_finished}')
    
    return cmd_is_finished     

def sendPromptExecuteResult(finish_url, api_token, params, result_status):

  # prompt end 
  sendData = {}
  sendData['req_id'] = FAP.getDicValue(params, 'req_id', None)
  sendData['job_id'] = FAP.getDicValue(params, 'job_id', None)
  sendData['host_ip'] = FAP.getDicValue(params, 'ip', None)
  sendData['status'] = result_status
  
  # finish_url '/api/fap_common/prompt/finish'
  content = sendRequest(finish_url, 'POST',api_token, sendData)

  if content is not None : 
    return True
  else:
    return False

def sendRequest(url, strMethod, api_token, sendData):
  try:
    # Http
    http = httplib2.Http(disable_ssl_certificate_validation=True)
          
    # Make header
    headers = {'Cache-Control':'no-cache', 'Connection':'close', 'x-auth-token':'Bearer '+api_token}
  
    # Send request
    time.sleep(0.1)
    resp, content = http.request(uri=url, method=strMethod, headers=headers, body=json.dumps(sendData))
    
    # OK=200, CREATED=201, ACCEPTED=202
    if resp.status == 200 or resp.status == 201 or resp.status == 202 :
        return content
    else:
        return None
  except Exception as err:  
    logger.exception(err)
    return None


def main():

  # Module arguments
  module_args = dict(
    fap_vars=dict(type='dict', required=True),
    protocol=dict(type='str', choices=['ssh', 'telnet', 'auto'], required=False, default='ssh'),    # not use
    ssh_port=dict(type='int', required=False, default=22),
    telnet_port=dict(type='int', required=False, default=23),
    ip=dict(type='str', required=True),
    command=dict(type='raw', required=True),
    is_input=dict(type='str',required=False, default=False),
    user_id=dict(type='str', required=False),
    user_password=dict(type='str', required=True, no_log=True),
    become_method=dict(type='str', required=False, default=None),
    become_password=dict(type='str', required=False, default=None, no_log=True)
  )

  # AnsibleModule
  module = AnsibleModule(
    argument_spec= module_args,
    supports_check_mode=False,
  )
  
  # Init result data
  result = dict(changed=False)

  client = None       # FapSshClient, FapTelnetClient
  output = None
  result_data = None
  
  # Parameters
  fap_vars = module.params.get('fap_vars', None)
  ssh_port = module.params.get('ssh_port', None)
  telnet_port = module.params.get('telnet_port', None)
  ip = module.params.get('ip', None)
  is_input = module.params.get('is_input',None)
  command_list = module.params.get('command', None)
  user_id = module.params.get('user_id', None)
  user_password = module.params.get('user_password', None)
  become_method = module.params.get('become_method', None)
  become_password = module.params.get('become_password', None)
  
  err_finish_url = None
 
  try :
    # Check mandatory parameters

    if not fap_vars:
      raise ValueError("fap_vars must be define")
    if not ip:
      raise ValueError("ip must be define")
    if not command_list:
      raise ValueError("command must be define")
    if not user_password:
      raise ValueError("user_password must be define")

    # Check Command List Data    
    # command_list = checkCommandList(command_list)

    # Initialze logger (/fap/logs/ansible/{yyyyMMdd}/~.log)
    module._verbosity = 1 # Debug Level 
    FAP.iniLogger(logger, module, 'exec_prompt', fap_vars)
    
    job_id = fap_vars.get('job_id', None)
    template_id = fap_vars.get('template_id',None)

    network_os = fap_vars.get('network_os', None)

    # Make execution parameters
    params = {}
    params['client_type']='prompt'
    params['ip'] = ip
    params['ssh_port'] = ssh_port
    params['telnet_port'] = telnet_port
    params['job_id'] = job_id 
    params['site_code'] = fap_vars.get('site_code', None)
    params['template_id'] = template_id
    params['user_id'] = user_id
    params['network_os'] = network_os
    params['user_password'] = user_password
    params['become_method'] = become_method
    params['become_password'] = become_password
    params['command_list'] = command_list 
    params['is_input'] = is_input 

    logger.info(f'-----------------------------------------------')
    logger.info(f'### Module started.')
    logger.info(f'- PARAMTERS.ip = {ip}')
    logger.info(f'- PARAMTERS.ssh_port = {ssh_port}')
    logger.info(f'- PARAMTERS.telnet_port = {telnet_port}')
    logger.info(f'- PARAMTERS.job_id = {job_id}')
    logger.info(f'- PARAMTERS.template_id = {template_id}')
    #logger.info(f'- PARAMTERS.user_id = {user_id}')
    #logger.info(f'- PARAMTERS.user_password = {user_password}')
    #logger.info(f'- PARAMTERS.become_method = {become_method}')
    #logger.info(f'- PARAMTERS.become_password = {become_password}')
    logger.info(f'- PARAMTERS.is_input = {is_input}')
    logger.info(f'- PARAMTERS.command = {command_list}')
    logger.info(f'')
    logger.info(f'')

    send_command_list = checkCommandList(command_list)

    if send_command_list is None : 
      module.fail_json(msg="Module failed: Not found command list", exception="NOT_FOUND_COMMAND_LIST")      

    
    logger.info(f'### command_list')
    logger.info(f'{send_command_list}')
    
    
    # Config parser
    iniPath = '/fap/ansible/conf/fap.conf'

    config = configparser.ConfigParser()
    config.read(iniPath)

    # Make data structure
    sendData = {}
    sendData['job_id'] = job_id
    sendData['template_id'] = template_id
    sendData['host_ip'] = ip 
    sendData['user_id'] = user_id
    sendData['user_password'] = user_password
    sendData['become_method'] = become_method 
    sendData['become_password'] = become_password
    sendData['is_input'] = is_input
    sendData['command_list'] = send_command_list
    

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    # API URL Setting 
    request_url = api_url + '/api/fap_common/prompt/request'

    # is_connect: 1 or 0
    is_connect = 0
    
    # Host Connect Check
    try :

      client = FapPromptClient(module, logger, params, send_command_list)
      
      if client.connect():
        is_connect = 1 
      else:
        is_connect = 0
        client.close()
        client = None

      if is_connect == 0: 
        if client is not None: client.close()

    except Exception as err:  
      logger.exception(err)

    sendData['is_connect'] = is_connect

    logger.info(f'* Connect Result : {is_connect}' )
    logger.info(f'* API SendData : {sendData}')

    content = sendRequest(request_url, 'POST', api_token, sendData)
      
    if content is None : 
      module.fail_json(msg="Module failed: Failed to input data", exception="FAILED_TO_INPUT_DATA")     
      if client != None:
        client.close()
        client = None
    else:
      logger.info(f'* API RecvData : {content}')

    result = json.loads(content)
      
    inputSuccess = result.get('isSuccess')

    if not inputSuccess or inputSuccess == False :
      module.fail_json(msg="Module failed: Failed to input data", exception="FAILED_TO_INPUT_DATA")
      if client != None:
        client.close()
        client = None   

    time.sleep(2)

    cmd_started = False 
    check_request = False
    logger.info(f'* RESULT : {result}')
    req_id = result.get('data').get('req_id')

    time_diff = 0
    start_time = datetime.datetime.now()
    timeout_min = start_time + datetime.timedelta(minutes=10)

    # is_cmd_start check (index : 0)
    while is_connect == 1 and cmd_started == False:
    
      # Check session is closed
      if client == None or client.isConnected() == False: break

      sendData = {}
      sendData['check_type'] = 'CMD_START'
      sendData['req_id'] = req_id
      sendData['job_id'] = job_id
      sendData['host_ip'] = ip
      sendData['cmd_idx'] = 0

      check_url = api_url + '/api/fap_common/prompt/check/input'
      get_content = sendRequest(check_url, 'GET', api_token, sendData)
      
      if get_content is not None:
        check_result_json = json.loads(get_content)
        #logger.info(f'** Check Input Data Result : {check_result_json}')
        if check_result_json['isSuccess'] == False:
          logger.info(f'** Request Prompt Input Failed ')
          cmd_started = True 
          check_request = False 
          break 
        else:
          cmd_status = check_result_json['data']['status']
          get_cmd_start = check_result_json['data']['cmd_start']
          
          if get_cmd_start == 1:
          #  logger.info(f'** check_result_json : {check_result_json}')
            cmd_started = True 
            check_request = True 
          elif get_cmd_start == 0:
            if cmd_status == 'P':
              logger.info(f'* PROMPT JOB CANCEL ')
              cmd_started = True 
              check_request = False 
              break
          else:
            now_time = datetime.datetime.now()
            if now_time > timeout_min :
              logger.info(f'* PROMPT JOB TIMEOUT ')
              cmd_started = True
              check_request = False 
              cmd_status='E'
              break
            #else:
            #  time.sleep(5)
      
      if cmd_started == False:
        client.send('\b')
        time.sleep(5) 
    
    finish_url = api_url + '/api/fap_common/prompt/finish'
    err_finish_url = api_url + '/api/fap_common/prompt/finish'

    # Failed to connect 
    if is_connect == 0 : 
      sendPromptExecuteResult(finish_url, api_token, params, 'D')
      module.fail_json(msg="Module failed: Failed to connect", exception="FAILED_TO_CONNECT")
      if client != None:
        client.close()
        client = None 
    
    # Failed to execute
    if cmd_started and check_request == False : 
      sendPromptExecuteResult(finish_url, api_token, params, 'E')
      module.fail_json(msg="Module failed: Failed to execute", exception="FAILED_TO_EXECUTE")
      if client != None:
        client.close()
        client = None 
      
    exec_result = None
    try:
      params['req_id'] = req_id
      client.setParams(params)

      # Send Prompt Command Start 
      send_url = api_url + '/api/fap_common/prompt/saveOutput'
      sendPromptCommandStart(send_url, api_token, params, is_connect)

      executeResult = client.execute()
      if executeResult is not None :
        exec_result = 'T' 
      else:
        exec_result = 'E'

    except Exception as ce :
      logger.exception(ce)
      sendPromptExecuteResult(finish_url, api_token, params, 'E')
      module.fail_json(msg="Module failed: {0}".format(str(ce)), exception=str(ce))
    finally:
      if client != None:
        client.close()
        client = None 
      
    # Command Process Finished Check   
    if exec_result == 'T':
      cmd_is_finished = checkPromptProcessEnd(client, config, req_id, job_id)
    
    # prompt end 
    result_data = sendPromptExecuteResult(finish_url, api_token, params, exec_result)

    if result_data is None:
      logger.info(f'* Finish Save Failed : {req_id}')  
 
    # Create result data
    result['changed'] = True
    
    result['is_connect'] = is_connect
    result['host_id'] = fap_vars.get('host_id', None)
    result['job_id'] = fap_vars.get('job_id', None)
    result['template_id'] = fap_vars.get('template_id', None)
    if exec_result  == 'T' and cmd_is_finished == True:
      result['prompt_result'] = True 
    else:
      result['prompt_result'] = False
    
    logger.info(f'')
    logger.info(f'* RESULT = {str(result)}')
    logger.info(f'### Module terminated.')
         
    
  except Exception as err:
    logger.exception(err)
    if err_finish_url is None : 
      # Config parser
      iniPath = '/fap/ansible/conf/fap.conf'

      config = configparser.ConfigParser()
      config.read(iniPath)
      api_url = config.get('API_SERVER', 'API_URL')
      api_token = config.get('API_SERVER', 'API_TOKEN')

      err_finish_url = api_url + '/api/fap_common/prompt/finish'

    sendPromptExecuteResult(err_finish_url, api_token, params, 'E')
    module.fail_json(msg="Module failed: {0}".format(str(err)), exception=str(err))
  finally:
    if client != None:
      client.close()
      client = None  
  # return 
  module.exit_json(**result)
  
if __name__ == "__main__":
  main()
