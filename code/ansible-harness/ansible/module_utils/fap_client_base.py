# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import sys, os, json, time, logging, json, re
import threading

import ansible_collections.fap.custom.plugins.module_utils.fap_common as FAP

# Set default encoding
FAP.setDefaultEncoding()

#==================================================
# FapBaseClient
#==================================================
class FapBaseClient:
  module = None        # AnsibleModule
  logger = None
  params = None
  commands = None
  result_type = None

  ip = None
  ssh_port = 22
  telnet_port = 23
  network_os = None
  user_id = None
  user_password = None
  become_method = None
  become_password = None

  client = None
  device_prompt = None
  
  # Session status
  status = FAP.SessionStatus.READY

  def __init__(self, module, logger, _params, _commands):
  
    self.module = module
    self.logger = logger
    self.params = _params
    
    self.logger.debug(f"- RAW_COMMAND_DATA_TYPE = {FAP.checkDataType(_commands)[0]}")
    self.logger.debug(f"- RAW_COMMAND = {_commands}")
    
    self.commands = []
    
    # Single command
    if isinstance(_commands, str):
      cmd_item = {}
      cmd_item['command'] = _commands
      self.commands.append( cmd_item )
    # Multiple command
    elif isinstance(_commands, list):
      for _cmd in _commands:
        if isinstance(_cmd, str):
          cmd_item = {}
          cmd_item['command'] = _cmd
          self.commands.append( cmd_item )
        elif isinstance(_cmd, dict):
          self.commands.append( _cmd )
    
    self.logger.info(f"- EXEC_COMMAND = {self.commands}")

    self.ip = FAP.getDicValue(self.params, 'ip', None)
    self.ssh_port = FAP.getDicValue(self.params, 'ssh_port', 22)
    self.telnet_port = FAP.getDicValue(self.params, 'telnet_port', 23)
    self.network_os = FAP.getDicValue(self.params, 'network_os', None)
    self.user_id = FAP.getDicValue(self.params, 'user_id', None)
    self.user_password = FAP.getDicValue(self.params, 'user_password', None)
    self.become_method = FAP.getDicValue(self.params, 'become_method', None)
    self.become_password = FAP.getDicValue(self.params, 'become_password', None)
    self.result_type = FAP.getDicValue(self.params, 'result_type', None)
    
    self.logger.info(f"- VERBOSITY LEVEL = {self.module._verbosity}")
    
  #==================================================
  # * Connect (Must be define)
  #==================================================
  def connect(self):
    raise ValueError(f"[ERROR] Must define the connect() function")
    return False

  def isConnected(self):
    if self.status != FAP.SessionStatus.READY and self.status != FAP.SessionStatus.DISCONNECTED:
      return True
    else:
      return False

  #==================================================
  # * Send (Must be define)
  #==================================================
  def send(self, command, isSecured=False):
    raise ValueError(f"[ERROR] Must define the send() function")
    return False

  #==================================================
  # * Expect (Must be define)
  #==================================================
  def expect(self, patterns=None, timeout=5):
    raise ValueError(f"[ERROR] Must define the expect() function")
    return None


  #==================================================
  # Close
  #==================================================
  def close(self):
    if self.client != None:
      self.client.close()
      self.client = None
    
      # stuats = DISCONNECTED
      self.status = FAP.SessionStatus.DISCONNECTED
      self.logger.info(f"- STATUS = {self.status}")
  
  #==================================================
  # Execute
  #==================================================
  def execute(self):
    
    # Outputs
    result_data = None
    
    try:
      # Check risk commands
      riskCommand = self.checkRiskCommands(self.commands)
      if riskCommand and len(riskCommand) > 0:
        self.logger.info(f"[REJECT] Contains a risk command: {riskCommand}")
        raise ValueError(f"[REJECT] Contains a risk command: {riskCommand}")
    
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
  
      index = 0
      for cmd_item in commands:
      
        # Sleep time = 0.1 ~ 300 seconds
        _sleep = FAP.getDicValue(cmd_item, 'sleep', None)
        if _sleep:
          _sleep = FAP.str2num(_sleep, None, 0.1, 300)
          if _sleep and _sleep > 0:
            self.logger.info(f"- SLEEP: {_sleep} seconds")
            time.sleep(_sleep)
        
        # Clear recv buffer
        self.expect(None, 2)
        
        # Get command string
        command = FAP.getDicValue(cmd_item, 'command', None)
        if not command:
          continue
        
        # Execute timeout = 5 ~ 120 seconds
        timeout = 5
        _timeout = FAP.getDicValue(cmd_item, 'timeout', None)
        if _timeout:
          _timeout = FAP.str2num(_timeout, None, 5, 120)
          if _timeout and _timeout > 5:
            timeout = _timeout
        
        self.logger.info(f"- SEND COMMAND: {command} (timeout={timeout} seconds)")
        
        # Check save flag
        isSaveOuput = False
        if FAP.getDicValue(cmd_item, 'is_save', False) == True:
          isSaveOuput = True
        if command[0] == '*':
          command = command[1:]
          isSaveOuput = True

        # Execute command
        output = self.executeCommand(command, timeout)
        
        self.logger.info(f"- PROCESS END: {command}")

        time.sleep(1)
        
        # Check save flag  
        if not isSaveOuput: continue
        
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
          
          if not FAP.isBlank(output):
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
  # Check prompt
  #==================================================
  def _checkPrompt(self):
    try:
    
      time.sleep(2)
      
      self.logger.info(f"- START CHECK_PROMPT FUNCTION")
      
      self.send('\n')
      
      # Recv data
      output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2], 10)
      if output_lines is None or len(output_lines) == 0:
        self.logger.info(f"- PROMPT STRING IS NONE") 
        return False
      
      output = output_lines[-1]
      if FAP.isBlank(output):
        self.logger.info(f"- PROMPT STRING IS NONE")
        return False

      self.logger.debug(f"[RAW>>] {output}")

      # Check prompt
      if re.search(FAP.PATTERN_PROMPT, output) or re.search(FAP.PATTERN_PROMPT2, output):

        output = FAP.decodeString(output)
        
        if not FAP.isBlank(output):
          self.device_prompt = output
          self.logger.debug(f"[RAW>>] {output}")
          self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")
          
          # stuats = PROMPT
          self.status = FAP.SessionStatus.PROMPT
          self.logger.info(f"- STATUS = {self.status}")
        else:
          self.logger.debug(f"[RAW>>] {output}")
          self.logger.info("- PROMPT-CHECK-FAILED")
          
          return False
      else:
        return False
      
      # Find enable command
      enableCmd = None
      if self.network_os:
        if self.network_os.upper().startswith("CISCO"):
          enableCmd = "enable"
        elif self.network_os.upper().startswith("HP"):
          enableCmd = "super"
        elif self.network_os.upper().startswith("ARISTA"):
          enableCmd = "enable"

      # Enter enable mode
      if not FAP.isBlank(enableCmd) and not FAP.isBlank(self.become_password):
          
        self.logger.info("# SEND-ENABLE-COMMAND")
        self.send(enableCmd+'\n')

        # Check password input
        output_lines = self.expect([FAP.PATTERN_PASSWORD])
        if output_lines is None or len(output_lines) == 0: return False
        
        output = output_lines[-1]
        if FAP.isBlank(output): return False
        
        self.logger.debug("[RAW>>] "+output)

        if re.search(FAP.PATTERN_PASSWORD, output):
            
          # Send enable password
          self.logger.info("# SEND-ENABLE-PASSWORD")
          self.send(self.become_password+'\n', True)
          
          # Check enable mode prompt
          output_lines = self.expect([FAP.PATTERN_EN_PROMPT])
          if output_lines is None or len(output_lines) == 0: return False
          
          output = output_lines[-1]
          if FAP.isBlank(output): return False

          self.logger.debug(f"[RAW>>] {output}")

          if re.search(FAP.PATTERN_EN_PROMPT, output):
            self.device_prompt = output
            self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")
            
            # stuats = EN_PROMPT
            self.status = FAP.SessionStatus.EN_PROMPT
            self.logger.info(f"- STATUS = {self.status}")
            self.logger.info(f"- ENABLE-PROMPT-OK")
            return True
          elif re.search(FAP.PATTERN_PROMPT, output) or re.search(FAP.PATTERN_PROMPT2, output):
            self.device_prompt = output
            self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")
          else:
            self.logger.info(f"- ENABLE-PROMPT-FAILED")
            return False
        elif re.search(FAP.PATTERN_EN_PROMPT, output) or re.search(FAP.PATTERN_PROMPT, output) or re.search(FAP.PATTERN_PROMPT2, output):
          self.device_prompt = output
          self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")
          
          # stuats = EN_PROMPT
          self.status = FAP.SessionStatus.EN_PROMPT
          self.logger.info(f"- STATUS = {self.status}")
          self.logger.info(f"- ENABLE-PROMPT-OK")
          return True
        else:
          self.logger.info(f"- ENABLE-PROMPT-FAILED")
          return False
    
      return True
    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))
      return False
  
  #==================================================
  # Execute command
  #==================================================
  def executeCommand(self, command, timeout=5):
    try:
      if FAP.isBlank(command): return None
      
      # Send data
      self.send(command+'\n')

      # Recv output
      output = ''
      isFeedbackCommand = False
      
      isRunning = True
      start_time = time.time()
      while isRunning:
        output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 1)
        
        if output_lines is not None and len(output_lines) > 0:
          start_time = time.time()
          self.logger.debug(f"--> TIME UPDATED: time={int(start_time)}")
        elif time.time() - start_time > timeout:
          self.logger.debug(f"--> TIME-OUT. curr={int(time.time())}, elapsed={int(time.time()-start_time)}")
          isRunning = False
          break        
        
        for line in output_lines:
          # Check more string
          if not isFeedbackCommand and line == command:
            self.logger.debug(f"--> SKIPED. FEEDBACK COMMAND: {line}")
            isFeedbackCommand = True
          # Check prompt string
          elif FAP.comparePromptString(self.device_prompt, line):
            self.logger.debug(f"--> SKIPED. PROMPT MATCHING: {line}")
            isRunning = False
            break
          else:
            self.logger.info(f"[>>] {line}")
            
            if line.endswith('\n'):
              output += line
            else:
              output += line+'\n'

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
  # Check risk commands
  #==================================================
  def checkRiskCommands(self, commands):

    if commands is None or not isinstance(commands, list):
      raise TypeError('Value should be a list')
    
    riskPatterns = []
    riskPatterns.append(r'^\s*(reload|reboot)\s*$')
    riskPatterns.append(r'^\s*(write erease|(erase|delete) startup-config|unconfigure switch all)\s*$')
    riskPatterns.append(r'^\s*(debug \S+|debug all)\s*$')
    
    self.logger.debug(f'[RISK_CHECK] riskPatterns = {riskPatterns}')
    
    # Commands
    for cmd_item in commands:
      command = FAP.getDicValue(cmd_item, 'command', None)
      if not command: continue
      
      self.logger.debug(f'[RISK_CHECK] command = {command}')
      
      # check risk patterns
      for pattern in riskPatterns:
      
        match = re.search(pattern, command, re.IGNORECASE|re.MULTILINE)
        if match and match.group():
          risk_cmd = match.group()
          return risk_cmd.strip()
    
    return None
    
    
