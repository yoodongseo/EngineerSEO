# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
import time

import paramiko

import ansible.module_utils.fap_common_prompt as FAP
from ansible.module_utils.fap_client_base_prompt import FapBasePromptClient


class FapSshPromptClient(FapBasePromptClient):
    channel = None

    def _is_network_target(self):
        return str(self.target_type or "server").strip().lower() == "network"

    def _get_ssh_connect_timeout(self):
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "connect_timeout", 5), 5, 1, 60)

    def _get_ssh_banner_timeout(self):
        default_timeout = 60 if self._is_network_target() else 30
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "banner_timeout", default_timeout), default_timeout, 1, 60)

    def _get_ssh_auth_timeout(self):
        default_timeout = 60 if self._is_network_target() else 30
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "auth_timeout", default_timeout), default_timeout, 1, 60)

    def connect(self):
        try:
            self.logger.info(f"- [SSH] Attempt to connect. ip={self.ip}")
            self.client = self._new_client()
            connect_timeout = self._get_ssh_connect_timeout()
            banner_timeout = self._get_ssh_banner_timeout()
            auth_timeout = self._get_ssh_auth_timeout()

            if self._is_network_target():
                self.logger.info("- Try authentication using 'password-only'")
                self.client.connect(
                    self.ip,
                    port=self.ssh_port,
                    username=self.user_id,
                    look_for_keys=False,
                    allow_agent=False,
                    password=self.user_password,
                    timeout=connect_timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                )
            else:
                self.logger.info("- Try authentication using 'mixed-auth'")
                self.client.connect(
                    self.ip,
                    port=self.ssh_port,
                    username=self.user_id,
                    look_for_keys=True,
                    allow_agent=True,
                    password=self.user_password,
                    timeout=connect_timeout,
                    banner_timeout=banner_timeout,
                    auth_timeout=auth_timeout,
                )

            self.status = FAP.SessionStatus.CONNECTED
            self.status = FAP.SessionStatus.LOGINED

            term = FAP.get_valid_param(self.ssh_params, "term", "dumb", str)
            width = FAP.get_valid_param(self.ssh_params, "width", 1000, int)
            height = FAP.get_valid_param(self.ssh_params, "height", 1000, int)
            self.channel = self.client.invoke_shell(term=term, width=width, height=height)
            self._checkPrompt()
            return self.channel is not None
        except Exception as err:
            self.logger.exception(err)
            self.close()
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))

    def _new_client(self):
        client = paramiko.client.SSHClient()
        client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
        return client

    def send(self, command, isSecured=False):
        if command is None or self.channel is None:
            return
        self.channel.send(command.encode())
        self.logger.debug("[<<] ****" if isSecured else f"[<<] {command.replace(chr(10), '')}")

    def expect(self, patterns=None, timeout=3):
        try:
            output = ""
            start_time = time.time()
            while True:
                if self.channel.recv_ready():
                    recvData = FAP.decodeString(self.channel.recv(65535))
                    output += recvData
                    if re.search(FAP.PATTERN_MORE, recvData):
                        self.send(" ")
                    elif re.search(FAP.PATTERN_MORE2, recvData):
                        self.send(" ")

                    if patterns is not None:
                        matched = False
                        for pattern in patterns:
                            if re.search(pattern, output, re.MULTILINE):
                                matched = True
                                break
                        if matched:
                            break

                if time.time() - start_time > timeout:
                    break
                time.sleep(0.02)

            output = FAP.cleanOutput(output)
            return output.replace("\r\n", "\n").replace("\n\r", "\n").splitlines()
        except Exception as err:
            self.logger.exception(err)
            raise ValueError(str(err))
