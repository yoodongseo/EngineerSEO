# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import sys, os, json, time, logging
import json, re
import threading, paramiko
from paramiko import RSAKey

import ansible_collections.fap.common.plugins.module_utils.fap_common_custom as FAP
from ansible_collections.fap.common.plugins.module_utils.fap_client_base_custom import (
    FapBaseClient,
)


class FapSshClient(FapBaseClient):

    channel = None

    # ==================================================
    # Init
    # ==================================================
    def __init__(self, module, logger, _params, _commands):

        # Invoke parent class method
        super().__init__(module, logger, _params, _commands)

    # ==================================================
    # connect
    # ==================================================
    def connect(self):
        try:
            self.logger.info(f"- STATUS = Attempting to connect. ip={self.ip}")

            self.client = paramiko.client.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())

            # Connect            
            try:
                pkey = None
                if os.path.exists(self.ssh_key_file):
                    self.logger.info(f"- SET rsa_key = {self.ssh_key_file}")
                    try:
                        pkey = RSAKey.from_private_key_file(self.ssh_key_file, password=self.user_password)
                        self.logger.info(f"- SUCCESS SET rsa_key = {self.ssh_key_file} ")
                    except Exception as e:
                        self.logger.info(f"- FAILED SET 'rsa_key'")
                        pkey = None              
                self.logger.info(f"- Try authentication using 'rsa_key|password'")
                self.client.connect(
                    self.ip,
                    port=self.ssh_port,
                    username=self.user_id,
                    look_for_keys=False,
                    pkey=pkey,
                    password=self.user_password,
                    timeout=5,
                )
            except paramiko.ssh_exception.AuthenticationException as ae:
                self.logger.info(f"- FAILED = Try authentication using 'rsa_key|password'")
                try:
                    self.logger.info(f"- STATUS = Try authentication using 'none'")
                    self.client.get_transport().auth_none(self.user_id)
                except Exception as e:
                    self.logger.info(f"- FAILED = Try authentication using 'none'")
                    raise ae

            # stuats = CONNECTED
            self.status = FAP.SessionStatus.CONNECTED
            self.logger.info(f"- STATUS = {self.status}")

            # stuats = LOGINED
            self.status = FAP.SessionStatus.LOGINED
            self.logger.info(f"- STATUS = {self.status}")
            
            # Create session
            # term = FAP.get_valid_param(self.ssh_params, 'term', 'dumb', str)
            term = FAP.get_valid_param(self.ssh_params, 'term', 'vt100', str)
            width = FAP.get_valid_param(self.ssh_params, 'width', 1000, int)
            height = FAP.get_valid_param(self.ssh_params, 'height', 1000, int)
            self.channel = self.client.invoke_shell(term=term, width=width, height=height)

            self._checkPrompt()

            return self.channel != None
        except Exception as err:
            self.logger.exception(err)
            self.close()
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))
            return False

    # ==================================================
    # Send
    # ==================================================
    def send(self, command, isSecured=False):
        if command is None:
            return

        if self.channel is None:
            self.logger.error(f"- Send failed (Channel is null)")
            return

        self.channel.send(command.encode())
        if isSecured:
            self.logger.debug(f"[<<] ****")
        else:
            sendCmd = command.replace("\n", "")
            self.logger.debug(f"[<<] {sendCmd}")

    # ==================================================
    #  Expect
    # ==================================================
    def expect(self, patterns=None, timeout=3):
        lines = []
        try:
            output = ""
            start_time = time.time()
            while True:
                if self.channel.recv_ready():
                    recvData = FAP.decodeString(self.channel.recv(65535))
                    output += recvData
                    # start_time = time.time()

                    # Check more string
                    if re.search(FAP.PATTERN_MORE, recvData):
                        self.logger.debug(f"[RAW>>] {recvData}")
                        self.logger.debug(f"--> MORE PATTERN-1 MATCHING")
                        self.send(" ")
                    elif re.search(FAP.PATTERN_MORE2, recvData):
                        self.logger.debug(f"[RAW>>] {recvData}")
                        self.logger.debug(f"--> MORE PATTERN-2 MATCHING")
                        self.send(" ")
                    else:
                        self.logger.debug(f"[RAW>>] {recvData}")

                    # Check expect pattern
                    isPatternMatched = False
                    if patterns != None:
                        self.logger.debug(f"--> [PATTERNS] {patterns}")
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

            return output.replace("\r\n", "\n").replace("\n\r", "\n").splitlines()

        except Exception as err:
            self.logger.exception(err)
            raise ValueError(str(err))

        return None
