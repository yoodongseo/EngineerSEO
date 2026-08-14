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

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP
from ansible_collections.fap.common.plugins.module_utils.fap_client_base import FapBaseClient

warnings.filterwarnings('ignore', category=DeprecationWarning)
import telnetlib

from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

HAS_HTTPLIB2 = True
try:
  import httplib2
except:
  HAS_HTTPLIB2 = False

class FapSopClient(FapBaseClient):

  channel = None
  
  last_input_updated = time.time()      # Last input
  last_output_updated = time.time()     # Last output (exclude hearbeat)
  last_keepalive_updated = time.time()  # Last send (include hearbeat)
  
  # keepalive  
  keepalive_enable = True
  #keepalive_maxtime = 60 * 60 * 6    # 6 hours
  #keepalive_time = 120
  keepalive_maxtime = 60 * 60         # 60 minutes (TEST)
  #keepalive_maxtime = 60 * 30         # 30 minutes (TEST)
  keepalive_time = 60

  # Command execute count
  cmd_exec_count = 0

  #==================================================
  # Init
  #==================================================
  def __init__(self, module, logger, _params):
    # Invoke parent method
    super().__init__(module, logger, _params, None)

  #==================================================
  # connect
  #==================================================
  def connect(self):
    try:
      _connected = False
      _connTimeoutSec = 30    # 30 seconds
      
      # 1. ssh
      try:
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        
        # Connect
        self.logger.info(f"- [SOP] Attempt to SSH connect. ip={self.ip}, ssh_port={self.ssh_port}")
        self.client.connect(self.ip, port=self.ssh_port, username=self.user_id, password=self.user_password, look_for_keys=False, timeout=_connTimeoutSec)
        
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

        if self.channel!= None : _connected = True
      except Exception as err:
        self.logger.exception(err)
        None
      
      # 2. telnet
      if _connected == False:
        if self.client is not None: self.client.close()
        
        # protocol = 'telnet'
        self.logger.info(f"- [SOP] Attempt to TELNET connect. ip={self.ip}, telnet_port={self.telnet_port}")
        self.client = telnetlib.Telnet(host=self.ip, port=self.telnet_port, timeout=_connTimeoutSec)
        if self.client != None:

          # Conntected
          self.status = FAP.SessionStatus.CONNECTED
          self.logger.info(f"- STATUS = {self.status}")

          # processLogin
          if not self._processLogin():
            self.close()
            self.logger.info(f"Failed to login")
            _connected = False
            self.client = None
            return False
        else:
          self.close()

        if self.client != None: 
          _connected = True
          self.channel = self.client

          return (self.client != None)
      
      return (self.channel != None)
  
    except Exception as err:
      self.logger.exception(err)
      self.close()
      raise ValueError(str(err))
      return False

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
  # Send
  #==================================================
  def send(self, command, isSecured=False):
    if command is None: return
    
    time.sleep(0.5)
    
    client_type = self.checkClientType()
    
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
  def expect(self, patterns=None, timeout=10, cmdData=None):
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
            recvData = FAP.decodeString(self.channel.recv(8192))
        elif client_type == 'telnet':
          # idx, match, tempRecvData = self.client.expect(encoded_patterns, 1)
          tempRecvData = self.client.read_eager()
          if tempRecvData is not None and len(tempRecvData) > 0:
            recvData = FAP.decodeString(tempRecvData)
        
        # Data recieved
        if recvData is not None:
          # Send data immediately
          if cmdData is not None:
            self.execApiSendOuput(cmdData, recvData)

          output += recvData
          
          start_time = time.time()
          self.last_output_updated = time.time()
          self.last_keepalive_updated = time.time()
          
          # Check more string
          self.logger.debug(f"[RAW>>] {recvData}")

          # Check expect pattern
          isPatternMatched = False
          if patterns != None:
            tmpOutput = output[-256:]
            for pattern in patterns:
              #if re.search(pattern, output):
              if re.search(pattern, tmpOutput):
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
        
        time.sleep(0.02)

      # Clean output
      output = FAP.cleanOutput(output)

      return output.replace('\r\n','\n').replace('\n\r','\n').splitlines()

    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))

    return None

  #==================================================
  #  Check Client Type
  #==================================================
  def checkClientType(self): 
    if type(self.client) == telnetlib.Telnet:
      return 'telnet'
    else:
      return 'ssh'

  #==================================================
  # Execute SOP
  #==================================================
  def executeSop(self):
    
    is_running = True
    is_first_running = True
    
    # Command data
    cmd_seq_idx = 0

    # Clear previous prompt line
    self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 5)

    # Main Loop
    while is_running:
      
      time.sleep(1)
      
      # Execute KeepAlive
      isTimeout = self._executeKeepAlive()
      if isTimeout:
        break
      
      # [API] getCommand
      nextData = self.execApiGetCommand(cmd_seq_idx)
      if nextData is None:
        continue
      elif 'status' not in nextData or 'commands' not in nextData:
        continue
      
      # is first running
      if is_first_running:
        self.logger.info(f"[SOP] First running ...")
        is_first_running = False

      # nextData - status
      statusData = nextData['status']
      if statusData is not None:
        # Check job status  (C=Completed, F=Failed, S=Stopped)
        _job_status = statusData['job_status'] 
        if _job_status in ['C', 'F', 'S', 'U']:
          self.logger.info(f"[SOP] Host={self.ip} - Job is terminated (job_status={_job_status})")
          break
        # Check prompt status (T=Terminated, F=Failed, S=Stopped)
        _prompt_status = statusData['prompt_status']
        if _prompt_status in ['T', 'F', 'S']:
          self.logger.info(f"[SOP] Host={self.ip} - Prompt is terminated (prompt_status={_prompt_status})")
          break
        # Check host status (T=Terminated, F=Failed, S=Stopped)
        _host_status = statusData['host_status']
        if _host_status in ['T', 'F', 'S']:
          self.logger.info(f"[SOP] Host={self.ip} - Host is terminated (host_status={_host_status})")
          break
      
      # nextData - commands
      listCommands = nextData['commands']
      if len(listCommands) == 0:
        continue
      
      # Check connection
      if self.client is None:
        try :
          # Connect to device
          if self.connect():
            # Update Host (C=Connected)
            self.execApiUpdateHost('C', None)
            self._sendNoPagingCommand()
          else:
            is_running = False
            self.client.close()
            self.client = None
            # Update Host (F=ConnectionFailed)
            self.execApiUpdateHost('F', 'Connection Failed')
            # Return fail
            self.module.fail_json(msg="Connection Failed", exception="Connection Failed")
        except Exception as err:
          self.logger.exception(err)
          is_running = False
          # Update Host (F=ConnectionFailed)
          self.execApiUpdateHost('F', 'Connection Failed')
          self.module.fail_json(msg="Connection Failed", exception="Connection Failed")
          break
      
      # Update Host (R=Running)
      self.execApiUpdateHost('R', None)

      # Command List
      for cmdData in listCommands:
        
        self.logger.info(f"[SOP] Host={self.ip}, cmdData={cmdData}")
        
        cmd_seq_idx = int(cmdData['cmd_seq_idx'])

        # Update command (R=Running)
        self.execApiUpdateCommand(cmdData, 'R', None)
        
        # Execute command
        #multiLineCmd = cmdData['cmd'].splitlines()
        #cmd_output = ""
        #if len(multiLineCmd) > 1:
          #for cmdLine in multiLineCmd:
            #cmd_output += self._executeSopCommand(cmdData, timeout=60, cmdLine=cmdLine)
        #else :
          #cmd_output = self._executeSopCommand(cmdData, timeout=60, cmdLine=None)
        cmd_output = self._executeSopCommand(cmdData, timeout=60, cmdLine=None)
        
        # Update command (T=Terminated)
        self.execApiUpdateCommand(cmdData, 'T', cmd_output)

        # Command execution counting
        self.cmd_exec_count = self.cmd_exec_count+1

  #==================================================
  # Execute command
  #==================================================
  def _executeSopCommand(self, cmdData, timeout=60, cmdLine=None):
    try:
      #self.logger.debug(f"executeSopCommand: cmdData={cmdData}")

      # Clear previous prompt line
      self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 2)

      # Command
      # multiLine
      if cmdLine is None:
        command = cmdData['cmd']
      else:
        command = cmdLine
      if FAP.isBlank(command): return None
      
      self.last_input_updated = time.time()
      self.last_keepalive_updated = time.time()

      # Send command
      self.send(command+'\n')
      
      # Recv output
      output = ''
      _isFeedbackCommand = False

      isRunning = True
      start_time = time.time()

      last_line = None

      while isRunning:
        output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 1, cmdData)
        
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
        elif last_line and len(last_line) > 0 :
          if re.search(FAP.PATTERN_CONF_PROMPT, last_line) and output_lines is not None and len(output_lines) < 1:
            self.logger.info(f"--> Configure Terminal Mode")
            break
          if time.time() - start_time > 5:
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
        else:
            None
        
        send_line_max = 100
        line_cnt = 1
        send_line = ""
        for line in output_lines:
          last_line = line
          send_line = send_line + line
          # Check more string
          if not _isFeedbackCommand and line == command:
            self.logger.debug(f"--> SKIPED. FEEDBACK COMMAND: {line}")
            _isFeedbackCommand = True
            continue
          # Check prompt string
          elif FAP.comparePromptString(self.device_prompt, line):
            self.logger.debug(f"--> SKIPED. PROMPT MATCHING: {line}")
            isRunning = False

          # Merge output
          self.logger.info(f"[>>] {line}")
          if line.endswith('\n'):
            output += line
          else:
            output += line+'\n'
            send_line += '\n'

          # Send output to server
          sendOutput = line
          if line_cnt % send_line_max == 0:
            #self.execApiSendOuput(cmdData, send_line)
            self.logger.info(f"[PRPT>>>] {send_line}")
            send_line = ""
          line_cnt = line_cnt + 1

        if send_line != "":
          #self.execApiSendOuput(cmdData, send_line)
          self.logger.info(f"[PRPT>>>] {send_line}")

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
  # Execute keepalive
  #==================================================
  def _executeKeepAlive(self):
    isTimeout = False
    if not self.keepalive_enable or self.keepalive_time <= 0: return isTimeout

    # Input/output elapsed (exclude heartbeat)
    _io_elapsed = time.time() - max(self.last_input_updated, self.last_output_updated)

    # Keepalive elapsed (include heartbeat)
    _keepalive_elapsed = time.time() - self.last_keepalive_updated
    
    # Check Input/output elapsed
    if self.keepalive_maxtime > 0 and _io_elapsed > self.keepalive_maxtime:
      self.logger.info(f"[KeepAlive] Keepalive={self._toElapsedTime(_keepalive_elapsed)}, TotalElapsed={self._toElapsedTime(_io_elapsed)}")
      self.logger.info(f"[KeepAlive] Timeout. (Maximum keepalive time reached. {self._toElapsedTime(self.keepalive_maxtime)} hour)")
      isTimeout = True
    # Check keepAlive elapsed and Send heartbeat
    elif _keepalive_elapsed >= self.keepalive_time:
      self.logger.info(f"[KeepAlive] Keepalive={self._toElapsedTime(_keepalive_elapsed)}, TotalElapsed={self._toElapsedTime(_io_elapsed)}")
      self.last_keepalive_updated = time.time()
      # if connected
      if self.isConnected() and self.channel is not None:

        # Send heartbeat (1 character)
        self.logger.info(f"[KeepAlive] Send heartbeat")
        self.send('\b')  # Backspace
        time.sleep(0.5)
        
        # Receive heartbeat (1 character)
        _clientType = self.checkClientType()
        _tmpRecv = None
        if _clientType == 'ssh' and self.channel.recv_ready():
          _tmpRecv = self.channel.recv(1)
          _tmpRecv = FAP.decodeString(_tmpRecv)
        elif _clientType == 'telnet':
          idx, match, _tmpRecv = self.client.expect([b'.'], 1)
          _tmpRecv = FAP.decodeString(_tmpRecv)
        
        # Check heartbeat feedback
        if _tmpRecv is not None and len(_tmpRecv) > 0:
          self.logger.debug(f'[KeepAlive] Heartbeat received. length={len(_tmpRecv)}')
    
    return isTimeout

  #==================================================
  # Execute API 
  #==================================================
  def _executeAPI(self, subURL, strMethod, sendData):
    try:
      _apiData = self.params['apiData']
      
      url = _apiData['url']+subURL
      #self.logger.debug(f'[API] URL={url}, sendData={sendData}')
      
      # Http
      http = httplib2.Http(disable_ssl_certificate_validation=True)
      
      # Make header
      headers = {'Cache-Control':'no-cache', 'Connection':'close', 'x-auth-token':'Bearer '+_apiData['token']}
      
      # Send request
      resp, content = http.request(uri=url, method=strMethod, headers=headers, body=json.dumps(sendData))
      #self.logger.debug(f'[API] status={resp.status}, content={content}')
      
      # OK=200, CREATED=201, ACCEPTED=202
      if resp.status == 200 or resp.status == 201 or resp.status == 202:
        # Reset failed count
        _apiData['failed'] = 0
        jsonContent = json.loads(content)
        return jsonContent
      else:
        return None
    except Exception as err:  
      self.logger.exception(err)
      # Increase failed count
      _apiData['failed'] = _apiData['failed'] + 1
      return None
    finally:
      time.sleep(0.05)
      # Check the maximum number of failed API executions has been reached
      if _apiData['failed'] > 10:
        self.module.fail_json(msg="Module failed: The maximum number of failed API executions has been reached. (MaxCount = 10)", exception="FAILED_TO_EXECUTE_API")

  #==================================================
  # [API] updateHost
  #==================================================
  def execApiUpdateHost(self, status, message=None):

    # Make sendData
    sendData = self.params['baseData'].copy()  # Copy data
    sendData['status'] = status
    sendData['message'] = message

    # Execute API
    _url = '/api/fap_common/sop/updateHost'
    content = self._executeAPI(_url, 'POST', sendData)

    # Check API result
    if content is not None:
      return True
    else:
      return False
      
  #==================================================
  # [API] getCommand
  #==================================================
  def execApiGetCommand(self, prev_seq_idx):
    
    # Make sendData
    sendData = self.params['baseData'].copy()  # Copy base data
    if prev_seq_idx > 0:
      sendData['prev_seq_idx'] = prev_seq_idx
    
    # Execute API
    _url = '/api/fap_common/sop/getCommand'
    content = self._executeAPI(_url, 'POST', sendData)
    
    # Check API result
    if content is not None and content['data'] is not None:
      return content['data']
    else:
      return None

  #==================================================
  # [API] sendOutput
  #==================================================
  def execApiSendOuput(self, cmdData, output):
    cmd_seq_idx = cmdData['cmd_seq_idx']
    cmd_id = cmdData['cmd_id']
    cmd = cmdData['cmd']
    
    # Make sendData
    sendData = self.params['baseData'].copy()  # Copy data
    sendData['cmd_seq_idx'] = cmd_seq_idx
    sendData['cmd_id'] = cmd_id
    sendData['output'] = output
    sendData['cmd'] = cmd

    # Execute API
    _url = '/api/fap_common/sop/sendOutput'  
    content = self._executeAPI(_url, 'POST', sendData)
    
    # Check API result
    if content is not None:
      return True
    else:
      return False

  #==================================================
  # [API] updateCommand
  #==================================================
  def execApiUpdateCommand(self, cmdData, cmd_status, cmd_output):
    cmd_seq_idx = FAP.getDicValue(cmdData, 'cmd_seq_idx', None)
    cmd_id = FAP.getDicValue(cmdData, 'cmd_id', None)
    rep_idx = FAP.getDicValue(cmdData,'rep_idx', None)
    repeat_group_id = FAP.getDicValue(cmdData,'repeat_group_id', None)
    repeat_count = FAP.getDicValue(cmdData,'repeat_count', None)
    execute_count = FAP.getDicValue(cmdData,'execute_count', None)
    recovery_cmd_id = FAP.getDicValue(cmdData,'recovery_cmd_id', None)
    cmd = FAP.getDicValue(cmdData,'cmd', None)

    # Make sendData
    sendData = self.params['baseData'].copy()    # Copy data
    sendData['cmd_seq_idx'] = cmd_seq_idx
    sendData['cmd_id'] = cmd_id
    sendData['cmd_status'] = cmd_status
    sendData['rep_idx'] = rep_idx   # ansible_prompt_sop_repeat_cmd - rep_idx 
    sendData['repeat_group_id'] = repeat_group_id   # ansible_prompt_sop_repeat_cmd - repeat_group_id 
    sendData['repeat_count'] = repeat_count
    sendData['execute_count'] = execute_count
    sendData['recovery_cmd_id'] = recovery_cmd_id
    sendData['cmd'] = cmd
    
    if cmd_output is not None:
      sendData['cmd_output'] = cmd_output
    
    # Execute API
    _url = '/api/fap_common/sop/updateCommand'
    content = self._executeAPI(_url, 'POST', sendData)
    
    # Check API result
    if content is not None:
      return True
    else:
      return False

  # Calculate hours, minutes, and seconds
  def _toElapsedTime(self, total_seconds):
    total_seconds = int(total_seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    parts = []
    if hours > 0: parts.append(f"{hours}H,")
    if hours > 0 or minutes > 0: parts.append(f"{minutes}M,")
    parts.append(f"{seconds}S")
    return "".join(parts)
  
  # send no paging command
  def _sendNoPagingCommand(self):
    if self.network_os is None:
      self.logger.info(f"network_os is None not sending no paging command")
      return
    cisco_ios_command = "terminal length 0"
    cisco_nxos_command = "terminal length 0"
    arista_command = "terminal length 0"
    hp_command = "screen-length disable"
    extreme_command = "terminal length 0"
    if self.network_os in 'cisco_ios':
      self.logger.info(f"cisco_ios send no paging command({cisco_ios_command})")
      self.send(cisco_ios_command+'\n')
    elif self.network_os in 'cisco_nxos':
      self.logger.info(f"cisco_nxos send no paging command({cisco_nxos_command})")
      self.send(cisco_nxos_command+'\n')
    elif "hp" in self.network_os:
      self.logger.info(f"hp send no paging command({hp_command})")
      self.send(hp_command+'\n')
    elif "extreme" in self.network_os:
      self.logger.info(f"extreme send no paging command({extreme_command})")
      self.send(extreme_command+'\n')
    elif "arista" in self.network_os:
      self.logger.info(f"arista send no paging command({arista_command})")
      self.send(arista_command+'\n')
    else:
      self.logger.info(f"NOT FOUND PAGING COMMAND (OS:{self.network_os})")
