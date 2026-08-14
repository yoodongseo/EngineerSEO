# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import os, sys, time, datetime, logging, json, re
import warnings

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP
from ansible_collections.fap.common.plugins.module_utils.fap_client_base import FapBaseClient

warnings.filterwarnings('ignore', category=DeprecationWarning)
import telnetlib

class FapTelnetClient(FapBaseClient):

  #==================================================
  # Init
  #==================================================
  def __init__(self, module, logger, _params, _commands):
    
    # Invoke parent class method
    super().__init__(module, logger, _params, _commands)

    
  #==================================================
  # Connect
  #==================================================
  def connect(self):
    try:
      # Create telnet
      self.logger.info(f"- [TELNET] Attempt to TELNET connect. ip={self.ip}, telnet_port={self.telnet_port}")
      self.client = telnetlib.Telnet(host=self.ip, port=self.telnet_port, timeout=3)
      if self.client != None:

        # Conntected
        self.status = FAP.SessionStatus.CONNECTED
        self.logger.info(f"- STATUS = {self.status}")

        # processLogin
        if not self._processLogin():
          self.close()
          self.logger.info(f"Failed to login")
          return None
      else:
        self.close()

      return (self.client != None)
              
    except Exception as err:
      #self.logger.error("[ERROR] " + str(err) )
      self.logger.exception(err)
      self.close()
      raise ValueError(str(err))
      return False

  #==================================================
  # Send
  #==================================================
  def send(self, command, isSecured=False):
    
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
  def expect(self, patterns=None, timeout=3):
    lines = []
    try:
      # Encode patterns
      encoded_patterns = []
      if patterns:
        for pattern in patterns:
          encoded_patterns.append(pattern.encode())
    
      output = ''
      start_time = time.time()
      while True:
        idx, match, recvData = self.client.expect(encoded_patterns, 1)
        
        if recvData is not None and len(recvData) > 0:
        
          recvData = FAP.decodeString(recvData)
        
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
        # Check password input string (NO USER INPUT)
        elif re.search(FAP.PATTERN_PASSWORD, output):
          # Send password
          self.client.write(self.user_password.encode() + b'\n')
          self.logger.info("# SEND-PASSWORD")
        # Check escape
        elif re.search(FAP.PATTERN_ESCAPE, output):
          self.client.write(b'\n')
          self.logger.info("# SEND-ESCAPE")
          idx, match, output = self.client.expect(FAP.TN_PATTERN_FIRST_LOGIN, 3)
          output = FAP.decodeString(output)
          if not FAP.isBlank(output):
            self.logger.info(f"[RAW>>][ESCAPE-USERNAME] {output}")
            if re.search(FAP.PATTERN_USERNAME, output):
              self.client.write(self.user_id.encode() + b'\n')
              self.logger.info(f'# SEND-ESCAPE-USERNAME')
              idx, match, output = self.client.expect(FAP.TN_PATTERN_PASSWORD, 3)
              output = FAP.decodeString(output)
              if not FAP.isBlank(output):
                self.logger.info(f"[RAW>>][ESCAPE-PASSWORD] {output}")
                if re.search(FAP.PATTERN_PASSWORD, output):
                  # Send password
                  self.client.write(self.user_password.encode() +b'\n')
                  self.logger.info("# SEND-ESCAPE-PASSWORD")
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
  
