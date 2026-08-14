# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
import telnetlib                                                                                                                                                                                                                
                                                                                                                                                                                                                                
from ansible.module_utils import fap_common_prompt as FAP                                                                                                                                                                       
from ansible.module_utils.fap_client_base_prompt import FapBasePromptClient


class FapTelnetPromptClient(FapBasePromptClient):
    def connect(self):
        self.logger.info(f"- [TELNET] Attempt to connect. ip={self.ip}")
        try:
            self.client = telnetlib.Telnet(host=self.ip, port=self.port, timeout=3)
            if self.client is not None:
                self.status = FAP.SessionStatus.CONNECTED
                if not self._processLogin():
                    self.close()
                    return None
            else:
                self.close()
            return self.client is not None
        except Exception as err:
            self.logger.exception(err)
            self.close()
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))

    def send(self, command, isSecured=False):
        if command is None or self.client is None:
            return
        self.client.write(command.encode())
        self.logger.debug("[<<] ****" if isSecured else f"[<<] {command.replace(chr(10), '')}")

    def expect(self, patterns=None, timeout=3):
        try:
            encoded_patterns = [pattern.encode() for pattern in patterns] if patterns else []
            output = ""
            start_time = time.time()
            while True:
                _, _, recvData = self.client.expect(encoded_patterns, 0.2)
                if recvData:
                    recvData = FAP.decodeString(recvData)
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

    def _processLogin(self):
        try:
            _, _, output = self.client.expect(FAP.TN_PATTERN_FIRST_LOGIN, 3)
            output = FAP.decodeString(output)
            if not FAP.isBlank(output):
                if re.search(FAP.PATTERN_USERNAME, output):
                    self.client.write(self.user_id.encode() + b"\n")
                    _, _, output = self.client.expect(FAP.TN_PATTERN_PASSWORD, 3)
                    output = FAP.decodeString(output)
                    if not FAP.isBlank(output) and re.search(FAP.PATTERN_PASSWORD, output):
                        self.client.write(self.user_password.encode() + b"\n")
                elif re.search(FAP.PATTERN_PASSWORD, output):
                    self.client.write(self.user_password.encode() + b"\n")
                else:
                    return False
            return self._checkPrompt()
        except Exception as err:
            self.logger.exception(err)
            raise ValueError(str(err))
