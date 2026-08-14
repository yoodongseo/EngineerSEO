# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import sys, os, json, time, logging
import json, re
import threading, paramiko
import datetime
import warnings
import os.path
import string
import random
import configparser

import ansible.module_utils.fap_common as FAP
from ansible.module_utils.fap_client_base import FapBaseClient
from ansible.module_utils.fap_client_ssh import FapSshClient
from ansible.module_utils.fap_client_telnet import FapTelnetClient

warnings.filterwarnings('ignore', category=DeprecationWarning)

from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

import telnetlib

HAS_HTTPLIB2 = True
try:
    import httplib2
except:
    HAS_HTTPLIB2 = False


class FapPromptClient(FapBaseClient):

  channel = None

  last_input_updated = time.time()
  last_output_updated = time.time()

  # keepalive  
  keepalive_enable = True
  keepalive_maxtime = 60 * 60 * 6   # 6 hour
  keepalive_updated = time.time()
  keepalive_time = 120

  #==================================================
  # Init
  #==================================================
  def __init__(self, module, logger, _params, _commands):
  
    # Invoke parent class method
    super().__init__(module, logger, _params, _commands)
    
  #==================================================
  # connect
  #==================================================
  def connect(self):
    try:
      connected = False
      client_timeout = 10 * 6 * 10
      
      # 1. ssh
      try:
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        
        # Connect
        self.logger.info(f"- [PROMPT] Attempt to SSH connect. ip={self.ip}, ssh_port={self.ssh_port}")
        self.client.connect(self.ip, port=self.ssh_port, username=self.user_id, password=self.user_password, look_for_keys=False, timeout=client_timeout)
        
        # stuats = CONNECTED
        self.status = FAP.SessionStatus.CONNECTED
        self.logger.info(f"- STATUS = {self.status}")

        # stuats = LOGINED
        self.status = FAP.SessionStatus.LOGINED
        self.logger.info(f"- STATUS = {self.status}")

        # Create session
        self.channel = self.client.invoke_shell(width=256, height=1000)
        self.channel.settimeout(0)

        self._checkPrompt()

        self.logger.debug(f'- (CONNECT-SSH) client = {self.client}')
        self.logger.debug(f'- (CONNECT-SSH) channel = {self.channel}')
        
        self.logger.info(f'- TIMEOUT(B) = {self.channel.timeout}')

        if self.channel!= None : connected = True
      except Exception as err:
        self.logger.exception(err)
        None
      
      # 2. telnet
      if connected == False:
        if self.client is not None: self.client.close()
        
        # protocol = 'telnet'
        self.logger.info(f"- [PROMPT] Attempt to TELNET connect. ip={self.ip}, telnet_port={self.telnet_port}")
        self.client = telnetlib.Telnet(host=self.ip, port=self.telnet_port, timeout=10)
        if self.client != None:

          # Conntected
          self.status = FAP.SessionStatus.CONNECTED
          self.logger.info(f"- STATUS = {self.status}")

          # processLogin
          if not self._processLogin():
            self.close()
            self.logger.info(f"Failed to login")
            connected = False
            self.client = None
            return False
        else:
          self.close()

        if self.client != None: 
          connected = True
          self.channel = self.client

          return (self.client != None)
      
      return (self.channel != None)
  
    except Exception as err:
      self.logger.exception(err)
      self.close()
      raise ValueError(str(err))
      return False

  #==================================================
  # Send
  #==================================================
  def send(self, command, isSecured=False):
    if command is None: return
    
    time.sleep(0.5)
    
    client_type = self.checkClientType()
    
    _tmpRecv = None
    
    # SSH
    if client_type == 'ssh':
      if self.channel is None:
        self.logger.error(f"- Send failed (Channel is null)") 
        return

      self.channel.send(command.encode())
    
    # Telnet
    elif client_type == 'telnet':
      if command is None: return
    
      if self.client is None:
        self.logger.error(f"- Send failed (client is null)") 
        return

      self.client.write(command.encode())

    if isSecured: 
      self.logger.debug(f"[<<] ****")
    else:
      sendCmd = command.replace('\n','')
      self.logger.debug(f"[<<] {sendCmd}")

  #==================================================
  #  Expect
  #==================================================
  def expect(self, patterns=None, timeout=10):
    lines = []
    try:
      client_type =  self.checkClientType()

      # Encode patterns
      encoded_patterns = []
      if patterns:
        for pattern in patterns:
          encoded_patterns.append(pattern.encode())

      output = ''
      start_time = time.time()
      line_start_time = time.time()
      
      while True:
        recvData = None
        
        # Check session is closed
        if self.isConnected() == False: break
        
        if client_type == 'ssh' : 
          if self.channel.recv_ready():
            recvData = FAP.decodeString(self.channel.recv(1024))
        elif client_type == 'telnet':
          # idx, match, tempRecvData = self.client.expect(encoded_patterns, 1)
          tempRecvData = self.client.read_eager()
          if tempRecvData is not None and len(tempRecvData) > 0:
            recvData = FAP.decodeString(tempRecvData)
            
        if recvData is not None:
          output += recvData
          
          start_time = time.time()
          self.last_output_updated = time.time()
          self.keepalive_updated = time.time()
          
          # Check more string
          if re.search(FAP.PATTERN_MORE, recvData):
            self.logger.debug(f"[RAW>>] {recvData}")
            self.logger.debug(f"--> MORE PATTERN-1 MATCHING")
            self.send(' ')
          elif re.search(FAP.PATTERN_MORE2, recvData):
            self.logger.debug(f"[RAW>>] {recvData}")
            self.logger.debug(f"--> MORE PATTERN-2 MATCHING")
            self.send(' ')
          else:
            self.logger.debug(f"[RAW>>] {recvData}")
            
          # Check expect pattern
          isPatternMatched = False
          if patterns != None:
            for pattern in patterns:
              if re.search(pattern, output):
                isPatternMatched = True
                break

          # Check line timeout
          if '\r' in recvData or '\n' in recvData:
            line_start_time = time.time()
          else:
            if time.time() - line_start_time > 5:
              # Timeout occurs for 1 line output: 5 seconds
              break
          
          if isPatternMatched:
            break
        
        # Check timeout
        if time.time() - start_time > timeout:
          break
        
        time.sleep(0.2)

      # Clean output
      output = FAP.cleanOutput(output)

      return output.replace('\r\n','\n').replace('\n\r','\n').splitlines()

    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))

    return None

  #==================================================
  #  Execute 
  #==================================================
  def execute(self):

    #output 
    result_data = None 

    try:
      # stuats = EXECUTE_COMMANDS
      self.status = FAP.SessionStatus.EXECUTE_COMMANDS
      self.logger.info(f"- STATUS = {self.status}")
  
      # Commands
      commands = self.commands
      
      # Result type
      if self.result_type in ['dict']:     # dic
        result_data = {}    
      elif self.result_type == 'cli_data': # cli_data
        result_data = {}
        result_data['data_list'] = []
      else:                                # list (default)
        result_data = []

      # API URL, Config Setting
      iniPath = '/fap/ansible/conf/fap.conf'

      config = configparser.ConfigParser()
      config.read(iniPath)

      api_url = config.get('API_SERVER', 'API_URL')
      api_token = config.get('API_SERVER', 'API_TOKEN')

      bCheckInput = False # FAP.getDicValue(self.params, 'is_input', None)
      # Get Prompt Request Param 
      req_id = FAP.getDicValue(self.params, 'req_id', None) 
      job_id = FAP.getDicValue(self.params, 'job_id', None) 
      host_ip = FAP.getDicValue(self.params, 'ip', None) 

      index = 0
      for cmd_item in commands:
      
        # Clear recv buffer
        self.expect(None, 2)
        
        # Get command string
        command = FAP.getDicValue(cmd_item, 'command', None)
        if not command:
          continue

        cmd_started = False 
        cmd_status = None 
        input_data = None 

        # Get Input Data Wait Flag   
        if cmd_item['cmd_idx'] != 1 :

          # global is_input < command is_input 우선순위 높음
          bCheckInput = FAP.getDicValue(cmd_item, 'is_input', None)
          if bCheckInput is None or bCheckInput == False:
            bCheckInput = FAP.getDicValue(self.params, 'is_input', None)
          
          if bCheckInput is None: bCheckInput = True  # Default: True
          
          self.logger.debug(f'** Check Input Flag(prompt) : {bCheckInput}')
          
          if bCheckInput == True:
            cmd_started, cmd_status, input_data = self.checkInputData(config, req_id, job_id, host_ip, cmd_item['cmd_idx'], cmd_item['cmd_id'])
            
            if not cmd_started :
              if cmd_status == 'P':
                self.logger.info(f'* Check Input Request Cancel.')
              else:  
                self.logger.info(f'* Check Input Request Time out.')
              break

          # self.logger.debug (f'### cmd_start : {bCmdStarted} , cms_status : {cmd_status}, input_data : {input_data}')
          
          # cmd_status case process
          cmd_result = False 
          if cmd_status is not None:
            if cmd_status == 'P': # skip
              self.logger.info(f'--> COMMAND PROCESS SKIPED. ')
              cmd_result = True 
              self.sendCommandFinish(host_ip, cmd_item['cmd_idx'], cmd_item['cmd_id'], cmd_result, cmd_status )
              continue 
            elif cmd_status == 'T': # stop
              self.logger.info(f'--> COMMAND PROCESS STOPED.')
              cmd_result = True 
              self.sendCommandFinish(host_ip, cmd_item['cmd_idx'], cmd_item['cmd_id'], cmd_result, cmd_status )
              break
        
        self.logger.info(f"- SEND COMMAND(PROMPT): {command}")
        
        # Execute command timeout (min: 1 sec ~ max: 1800 seconds)
        timeout = 60
        _timeout = FAP.getDicValue(cmd_item, 'timeout', None)
        if _timeout:
          _timeout = FAP.str2num(_timeout, None, 1, 1800)
          if _timeout and _timeout > 1:
            timeout = _timeout

        output = self.executeCommand(command, cmd_item['cmd_idx'], cmd_item['cmd_id'], timeout)
        
        # Change status
        cmd_result = True
        cmd_status = 'S'
        if output is None: output = ''
        
        self.logger.info(f"- PROCESS END(PROMPT): command={command}, cmd_status={cmd_status}")
        
        self.sendCommandFinish(host_ip, cmd_item['cmd_idx'], cmd_item['cmd_id'], cmd_result, cmd_status )

        time.sleep(1)
        
        # Make output item
        index = index + 1

        # Make result
        if self.result_type == 'dict':
          # dictinary
          result_data[command] = output
        else:
          # list, cli_data
          output_item = {}
          output_item['index'] = index
          output_item['cmd'] = command
          output_item['output'] = output
          
          #if not FAP.isBlank(output):
          if output != None:
            output_item['is_success'] = True
          else:
            output_item['is_success'] = False
          
          # list
          if self.result_type == 'list':
            result_data.append(output_item)
            
          # ansible_cli_data
          elif self.result_type == 'cli_data':
            # host_name
            output_item['host_name'] = self.ip
            # cmd_id
            _cmd_id = FAP.getDicValue(cmd_item, 'cmd_id', FAP.getDicValue(cmd_item, 'id', None))
            if _cmd_id is None: _cmd_id = index
            output_item['cmd_id'] = _cmd_id
            # cmd_name
            _cmd_name = FAP.getDicValue(cmd_item, 'cmd_name', FAP.getDicValue(cmd_item, 'name', None))
            if _cmd_name is None: _cmd_name = command
            output_item['cmd_name'] = _cmd_name
            # os
            _os = FAP.getDicValue(cmd_item, 'os', None)
            if _os is None: _os = self.network_os
            output_item['os'] = _os
            # insert_time
            output_item['insert_time'] = FAP.timestampMilliSec64()
            
            # Copy cmd_item values
            exclude_keys = ['index', 'id', 'cmd', 'output', 'is_success', 'is_save', 'timeout']
            for key, value in cmd_item.items():
              if key not in exclude_keys and key not in output_item:
                output_item[key] = value
            
            result_data['data_list'].append(output_item)
 
        # Sleep 1 seconds          
        time.sleep(1)
      
      return result_data 
    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))
      return None
  

  #==================================================
  #  Check Input Data
  #==================================================
  def checkInputData(self, config, req_id, job_id, host_ip, cmd_idx, cmd_id) :

    self.logger.debug(f'----> checkInputData(Prompt) Start ')

    time_diff = 0
    start_time = datetime.datetime.now()
    timeout_min = start_time + datetime.timedelta(minutes=10)

    cmd_started = False
    input_data = None
    cmd_status = None 

    check_request = False

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    while cmd_started == False:
      
      # Check session is closed
      if self.isConnected() == False: break

      sendData = {}
      sendData['check_type'] = 'CMD_START'
      sendData['req_id'] = req_id
      sendData['job_id'] = job_id
      sendData['host_ip'] = host_ip
      sendData['cmd_idx'] = cmd_idx 
              
      url = api_url + '/api/fap_common/prompt/check/input'
       # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
            
      # Make header
      headers = {'Cache-Control':'no-cache','Connection':'close','x-auth-token':'Bearer '+api_token}

      # Send request
      time.sleep(0.1)
      get_content = None
      try:
        resp, get_content = http.request(uri=url, method='GET', headers=headers, body=json.dumps(sendData))
      except Exception as err:
        self.logger.exception(err)
        get_content = None

      #logger.info(f'*** checkInputData(Prompt) CHeck Result : {get_content}')
              
      if get_content is not None:
        check_result = json.loads(get_content)
        
        #self.logger.info(f'** Check Input Data Result : {check_result}')
        
        if FAP.getDicValue(check_result, 'isSuccess', False) == False:
          time.sleep(5)
          self.logger.info(f'** Check Input Data Result : {check_result}')
          continue
        
        if check_result['data']['cmd_start'] == 1:
          self.logger.info(f'** Check Input Data Result : {check_result}')         

          cmd_status = check_result['data']['status']
          if cmd_status == 'P' or cmd_status == 'T':
            ## SKIP, STOP
            cmd_started = True 
            check_request = True 
          elif cmd_status == 'W' or cmd_status =='R':
            if 'input_data' in check_result['data']:
              input_data = check_result['data']['input_data']
            cmd_started = True
            check_request = True
        else:
          cmd_status = check_result['data']['status']
          if cmd_status == 'P' or cmd_status == 'T':
            ## SKIP, STOP
            self.logger.info(f'** Check Input Data Result : {check_result}')
            cmd_started = True 
            check_request = True 
          else:
            now_time = datetime.datetime.now()
            
            # Keepalive
            if self.keepalive_enable and self.keepalive_time > 0:
              # Total delayed
              _total_delayed = time.time() - max(self.last_input_updated, self.last_output_updated)
              # KeepAlive delayed
              _keepalive_delayed = time.time() - self.keepalive_updated
              
              # Check total delayed time
              if self.keepalive_maxtime > 0 and _total_delayed > self.keepalive_maxtime:
                self.logger.info(f"[KeepAlive] delayed={_keepalive_delayed:.0f} sec, total_delayed={_total_delayed/60.0:.0f} min.")
                self.logger.info(f"[KeepAlive] Timeout. (Maximum keepalive time reached. {(self.keepalive_maxtime/3600.0):.1f} hour)")
                cmd_started = True
                check_request = False 
                break
              # Check keepAlive
              elif _keepalive_delayed >= self.keepalive_time:
                self.logger.info(f"[KeepAlive] delayed={_keepalive_delayed:.0f} sec, total_delayed={_total_delayed/60.0:.0f} min.")
                
                # Send heartbeat (1 character)
                self.logger.info(f"[KeepAlive] Send heartbeat")
                self.send('\b')  # Backspace
                self.keepalive_updated = time.time()
                
                # Recv heartbeat (1 character)
                time.sleep(0.5)
                client_type = self.checkClientType()
                _tmpRecv = None
                if client_type == 'ssh' and self.channel.recv_ready():
                  _tmpRecv = self.channel.recv(1)
                  _tmpRecv = FAP.decodeString(_tmpRecv)
                elif client_type == 'telnet':
                  idx, match, _tmpRecv = self.client.expect([b'.'], 1)
                  _tmpRecv = FAP.decodeString(_tmpRecv)
                
                if _tmpRecv is not None and len(_tmpRecv) > 0:
                  self.logger.debug(f'[KeepAlive] Receive heartbeat={_tmpRecv}, length={len(_tmpRecv)}')
                
            # Check timeout  
            elif now_time > timeout_min :
              cmd_started = True
              check_request = False 
              break
      
      if cmd_started == False:
        time.sleep(5)
      
    self.logger.debug(f'----> checkInputData(Prompt) End ')
    
    if cmd_started and check_request == False : 
      cmd_started = False

    return cmd_started, cmd_status, input_data
    
  #==================================================
  # Execute command
  #==================================================
  def executeCommand(self, command, cmd_idx, cmd_id, timeout=60):
    try:
      if FAP.isBlank(command): return None
      
      self.last_input_updated = time.time()
      self.keepalive_updated = time.time()

      # Send data
      self.send(command+'\n')
      self.sendCommandExecuted(cmd_idx, cmd_id)

      # Recv output
      output = ''
      isFeedbackCommand = False

      isRunning = True
      start_time = time.time()

      prmopt_index = 1
      
      client_type = FAP.getDicValue(self.params, 'client_type', None)
      
      last_line = None

      while isRunning:
        output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 1)
        
        # Check session is closed
        if self.isConnected() == False: break
        
        if output_lines is not None and len(output_lines) > 0:
          start_time = time.time()
          self.logger.debug(f"--> TIME UPDATED: time={int(start_time)}")
        elif time.time() - start_time > timeout:
          self.logger.debug(f"--> TIME-OUT. curr={int(time.time())}, elapsed={int(time.time()-start_time)}")
          isRunning = False
          break   
        # Check question message (when 5 seconds after)
        elif last_line and len(last_line) > 0 and time.time() - start_time > 5:
          if re.search(FAP.PATTERN_QUESTION, last_line, re.IGNORECASE):
            isRunning = False
            break
          elif re.search(r'.*[:\?>\]$#]', last_line.strip()):
            # Excluded: "Slot 1:"
            if re.search(r'[sS]lot\s+\d+\s*:\s*|MD5\sdigest:$', last_line.strip()):
              pass
            else:
              isRunning = False
              break
            
        
        for line in output_lines:
          
          last_line = line
          
          # Check more string
          if not isFeedbackCommand and line == command:
            self.logger.debug(f"--> SKIPED. FEEDBACK COMMAND: {line}")
            isFeedbackCommand = True
            continue
          # Check prompt string
          elif FAP.comparePromptString(self.device_prompt, line):
            self.logger.debug(f"--> SKIPED. PROMPT MATCHING: {line}")
            isRunning = False
            
          # Merget output
          self.logger.info(f"[>>] {line}")
          
          if line.endswith('\n'):
            output += line
          else:
            output += line+'\n'

          # Send output
          sendOutput = line
          self.sendCommandOutput(sendOutput, cmd_idx, cmd_id, prmopt_index)
          self.logger.info(f"[PRPT>>>] {sendOutput}")
          prmopt_index += 1

      # Clear recv buffer
      while isRunning:
        output_lines = self.expect(None, 1)
        if output_lines is None or len(output_lines) == 0:
          break
        else:
          time.sleep(0.1)

      return output 
      

    except Exception as err:
      self.logger.exception(err)
      self.logger.error(f"[ERROR] {str(err)}")
      raise ValueError(str(err))
      return None

  #==================================================
  # Send command excuted
  #==================================================
  def sendCommandExecuted(self, cmd_idx, cmd_id):
    # Config parser
    iniPath = '/fap/ansible/conf/fap.conf'

    config = configparser.ConfigParser()
    config.read(iniPath)

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/prompt/command_executed'
    
    sendData = {}
    sendData['req_id'] = FAP.getDicValue(self.params, 'req_id', None)
    sendData['job_id'] = FAP.getDicValue(self.params, 'job_id', None)
    sendData['host_ip'] = FAP.getDicValue(self.params, 'ip', None)
    sendData['cmd_idx'] = cmd_idx 

    try:

      # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
            
      # Make header
      headers = {'Cache-Control':'no-cache','Connection':'close', 'x-auth-token':'Bearer '+api_token}

      # Send request
      time.sleep(0.1)
      resp, content = http.request(uri=url, method='POST', headers=headers, body=json.dumps(sendData))

      sendResult = False
      if resp.status == 200 or resp.status == 201 or resp.status == 202 :
        if content is not None:
          sendResult = True
        else:
          sendResult = False
      else:
        sendResult = False 

      if sendResult == True:
        self.logger.info(f'# Send command_executed {cmd_id}')
      else:
        self.logger.info(f'# Send command_executed {cmd_id}')
        
    except Exception as err:
      self.logger.exception(err)
      self.logger.error(f"[ERROR] {str(err)}")
      raise ValueError(str(err))
      return None

  #==================================================
  # Send Output
  #==================================================
  def sendCommandOutput(self, line, cmd_idx, cmd_id, prompt_idx):
    # Config parser
    iniPath = '/fap/ansible/conf/fap.conf'

    config = configparser.ConfigParser()
    config.read(iniPath)

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/prompt/saveOutput'

    sendData = {}
    sendData['req_id'] = FAP.getDicValue(self.params, 'req_id', None)
    sendData['job_id'] = FAP.getDicValue(self.params, 'job_id', None)
    sendData['template_id'] = FAP.getDicValue(self.params, 'template_id', None)
    sendData['host_ip'] = FAP.getDicValue(self.params, 'ip', None)
    sendData['cmd_idx'] = cmd_idx 
    sendData['cmd_id'] = cmd_id 
    sendData['prompt_idx'] = prompt_idx 
    sendData['output'] = line 

    try:

      # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
            
      # Make header
      headers = {'Cache-Control':'no-cache','Connection':'close', 'x-auth-token':'Bearer '+api_token}

      # Send request
      time.sleep(0.1)
      resp, content = http.request(uri=url, method='POST', headers=headers, body=json.dumps(sendData))

      sendResult = False
      if resp.status == 200 or resp.status == 201 or resp.status == 202 :
        if content is not None:
          sendResult = True
        else:
          sendResult = False
      else:
        sendResult = False 

      if sendResult == True:
        self.logger.info(f'# sendOutput Save Success {cmd_id}')
      else:
        self.logger.info(f'# sendOutput Save Failed {cmd_id}')
        
    except Exception as err:
      self.logger.exception(err)
      self.logger.error(f"[ERROR] {str(err)}")
      raise ValueError(str(err))
      return None

  #==================================================
  # Send Finish
  #==================================================
  def sendCommandFinish(self, host_ip, cmd_idx, cmd_id, cmd_result, cmd_status):
    # Config parser
    iniPath = '/fap/ansible/conf/fap.conf'

    config = configparser.ConfigParser()
    config.read(iniPath)

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/prompt/finish/command'

    sendData = {}
    sendData['req_id'] = FAP.getDicValue(self.params, 'req_id', None)
    sendData['job_id'] = FAP.getDicValue(self.params, 'job_id', None)
    sendData['template_id'] = FAP.getDicValue(self.params, 'template_id', None)
    sendData['host_ip'] = host_ip
    sendData['cmd_idx'] = cmd_idx 
    sendData['cmd_id'] = cmd_id 
    sendData['cmd_result'] = cmd_result 
    sendData['cmd_status'] = cmd_status
    
    try:

      self.logger.info(f'# sendData : {sendData}')

      # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
            
      # Make header
      headers = {'Cache-Control':'no-cache','Connection':'close', 'x-auth-token':'Bearer '+api_token}

      # Send request
      time.sleep(0.1)
      resp, content = http.request(uri=url, method='POST', headers=headers, body=json.dumps(sendData))

      sendResult = False
      if resp.status == 200 or resp.status == 201 or resp.status == 202 :
        if content is not None:
          sendResult = True
        else:
          sendResult = False
      else:
        sendResult = False 

      if sendResult == True:
        self.logger.info(f'# sendCommandFinish Success {cmd_id}')
      else:
        self.logger.info(f'# sendCommandFinish Failed {cmd_id}')
        
    except Exception as err:
      self.logger.exception(err)
      self.logger.error(f"[ERROR] {str(err)}")
      raise ValueError(str(err))
      return None

  #==================================================
  #  Set Params 
  #==================================================
  def setParams(self, params):
    if params is not None:
     # self.logger.info(f"* Set Params Try(before) : {params}")
      self.params = params
     # self.logger.info(f"* Set Params Try(after) : {self.params}")

  #==================================================
  # Process login (Telnet)
  #==================================================
  def _processLogin(self):
    try:
      # First check
      idx, match, output = self.client.expect(FAP.TN_PATTERN_FIRST_LOGIN, 3)
      output = FAP.decodeString(output)

      self.logger.debug(f"[RAW>>] {output}")
      if not FAP.isBlank(output):
        
        # Check user input string
        if re.search(FAP.PATTERN_USERNAME, output):
          # Send user
          self.client.write(self.user_id.encode() + b'\n')
          self.logger.debug(f'[SEND-USER]')

          # Check password input string
          idx, match, output = self.client.expect(FAP.TN_PATTERN_PASSWORD, 3)
          output = FAP.decodeString(output)
          if not FAP.isBlank(output):
            self.logger.debug(f"[RAW>>] {output}")
            if re.search(FAP.PATTERN_PASSWORD, output):
              # Send password
              self.client.write(self.user_password.encode() + b'\n')
              self.logger.info("# SEND-PASSWORD")
              self.logger.debug("# (DEBUG) SEND-PASSWORD")
        # Check password input string (NO USER INPUT)
        elif re.search(FAP.PATTERN_PASSWORD, output):
          # Send password
          self.client.write(self.user_password.encode() + b'\n')
          self.logger.info("# SEND-PASSWORD")
          self.logger.debug("# (DEBUG_2)SEND-PASSWORD")
        # Unknown output
        else:
          self.logger.info(f"[ERROR] Unknown output")
          self.logger.debug(f"[RAW>>] {output}")
          return False
          
      return self._checkPrompt()

    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))
      return False
  
  #==================================================
  #  Check Client Type
  #==================================================
  def checkClientType(self): 
    client_type = None

    if type(self.client) == telnetlib.Telnet:
      client_type = 'telnet'
    else:
      client_type = 'ssh' 
    
    return client_type
