# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import re
import time

import paramiko

import ansible_collections.fap.custom.plugins.module_utils.fap_common_prompt as FAP
from ansible_collections.fap.custom.plugins.module_utils.fap_client_base_prompt import FapBasePromptClient


class FapSshPromptClient(FapBasePromptClient):
    channel = None

    def _is_password_only_auth(self):
        return str(self.target_type or "mixed").strip().lower() == "pwonly"

    def _get_session_timeout(self):
        default_timeout = 60
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "session_timeout", default_timeout), default_timeout, 1, 120)

    def _get_ssh_connect_timeout(self):
        if "session_timeout" in self.ssh_params:
            return self._get_session_timeout()
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "connect_timeout", 60), 60, 1, 120)

    def _get_ssh_banner_timeout(self):
        if "session_timeout" in self.ssh_params:
            return self._get_session_timeout()
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "banner_timeout", 60), 60, 1, 120)

    def _get_ssh_auth_timeout(self):
        if "session_timeout" in self.ssh_params:
            return self._get_session_timeout()
        return FAP.str2num(FAP.getDicValue(self.ssh_params, "auth_timeout", 60), 60, 1, 120)

    def _has_session_timeout(self):
        return "session_timeout" in self.ssh_params or not any(
            key in self.ssh_params for key in ["connect_timeout", "banner_timeout", "auth_timeout", "login_prompt_timeout", "prompt_timeout"]
        )

    def _remaining_session_timeout(self, deadline):
        remaining = deadline - time.time()
        if remaining <= 0:
            raise TimeoutError("session_timeout exceeded")
        return remaining

    def connect(self):
        session_start = time.time()
        stage = "ssh_connect"
        try:
            self.logger.info(f"- [SSH] Attempt to connect. ip={self.ip}")
            self.client = self._new_client()
            use_session_deadline = self._has_session_timeout()
            session_timeout = self._get_session_timeout()
            session_deadline = session_start + session_timeout if use_session_deadline else None
            connect_timeout = self._get_ssh_connect_timeout()
            banner_timeout = self._get_ssh_banner_timeout()
            auth_timeout = self._get_ssh_auth_timeout()
            if use_session_deadline:
                remaining_timeout = self._remaining_session_timeout(session_deadline)
                connect_timeout = remaining_timeout
                banner_timeout = remaining_timeout
                auth_timeout = remaining_timeout
            self.logger.info(f"- SESSION_START total_timeout={session_timeout}s")

            connect_start = time.time()
            try:
                if self._is_password_only_auth():
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
            except Exception as err:
                connect_elapsed = time.time() - connect_start
                self.logger.error(f"- SSH_CONNECT_FAILED elapsed={connect_elapsed:.2f}s reason={err}")
                raise

            connect_elapsed = time.time() - connect_start
            self.logger.info(f"- SSH_CONNECT_DONE elapsed={connect_elapsed:.2f}s")

            self.status = FAP.SessionStatus.CONNECTED
            self.status = FAP.SessionStatus.LOGINED

            stage = "invoke_shell"
            term = FAP.get_valid_param(self.ssh_params, "term", "dumb", str)
            width = FAP.get_valid_param(self.ssh_params, "width", 1000, int)
            height = FAP.get_valid_param(self.ssh_params, "height", 1000, int)
            shell_start = time.time()
            try:
                if use_session_deadline:
                    remaining_timeout = self._remaining_session_timeout(session_deadline)
                    transport = self.client.get_transport()
                    if transport is None:
                        raise ValueError("SSH transport is not available")
                    self.channel = transport.open_session(timeout=remaining_timeout)
                    self.channel.settimeout(remaining_timeout)
                    self.channel.get_pty(term=term, width=width, height=height)
                    self.channel.invoke_shell()
                    self._remaining_session_timeout(session_deadline)
                else:
                    self.channel = self.client.invoke_shell(term=term, width=width, height=height)
            except Exception as err:
                shell_elapsed = time.time() - shell_start
                self.logger.error(f"- INVOKE_SHELL_FAILED elapsed={shell_elapsed:.2f}s reason={err}")
                raise
            shell_elapsed = time.time() - shell_start
            self.logger.info(f"- INVOKE_SHELL_DONE elapsed={shell_elapsed:.2f}s")

            stage = "login_prompt"
            login_prompt_timeout = self._remaining_session_timeout(session_deadline) if use_session_deadline else None
            if not self._checkPrompt(login_prompt_timeout):
                session_elapsed = time.time() - session_start
                self.logger.error(f"- SESSION_FAILED stage={stage} total_elapsed={session_elapsed:.2f}s reason=prompt_not_found")
                return False

            session_elapsed = time.time() - session_start
            self.logger.info(f"- SESSION_READY total_elapsed={session_elapsed:.2f}s")
            return self.channel is not None
        except Exception as err:
            session_elapsed = time.time() - session_start
            self.logger.error(f"- SESSION_FAILED stage={stage} total_elapsed={session_elapsed:.2f}s reason={err}")
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
