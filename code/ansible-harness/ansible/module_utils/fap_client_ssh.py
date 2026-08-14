# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import sys, os, json, time, logging
import json, re
import threading, paramiko

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP
from ansible_collections.fap.common.plugins.module_utils.fap_client_base import FapBaseClient

class FapSshClient(FapBaseClient):

  channel = None

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
      self.client = paramiko.client.SSHClient()
      self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
      
      # Connect
      self.logger.info(f"- [SSH] Attempt to SSH connect. ip={self.ip}, ssh_port={self.ssh_port}")
      self.client.connect(self.ip, port=self.ssh_port, username=self.user_id, password=self.user_password, look_for_keys=False, timeout=5)
      
      # stuats = CONNECTED
      self.status = FAP.SessionStatus.CONNECTED
      self.logger.info(f"- STATUS = {self.status}")

      # stuats = LOGINED
      self.status = FAP.SessionStatus.LOGINED
      self.logger.info(f"- STATUS = {self.status}")

      # Create session
      self.channel = self.client.invoke_shell(width=256, height=1000)

      self._checkPrompt()

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
    
    if self.channel is None:
      self.logger.error(f"- Send failed (Channel is null)") 
      return

    self.channel.send(command.encode())

    if isSecured: 
      self.logger.debug(f"[<<] ****")
    else:
      sendCmd = command.replace('\n','')
      self.logger.debug(f"[<<] {sendCmd}")

  #==================================================
  #  Expect
  #==================================================
  def expect(self, patterns=None, timeout=3):
    lines = []
    try:
      output = ''
      start_time = time.time()
      while True:
        if self.channel.recv_ready():
          recvData = FAP.decodeString(self.channel.recv(1024))
          output += recvData
          
          start_time = time.time()
          
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
          
          if isPatternMatched:
            break
        
        # Check timeout
        if time.time() - start_time > timeout:
          break
        
        time.sleep(0.1)

      # Clean output
      output = FAP.cleanOutput(output)

      return output.replace('\r\n','\n').replace('\n\r','\n').splitlines()

    except Exception as err:
      self.logger.exception(err)
      raise ValueError(str(err))

    return None
