# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule

import sys, os, json, time, logging, json, re
import threading

import ansible_collections.fap.common.plugins.module_utils.fap_common_custom as FAP
import datetime

# Set default encoding
FAP.setDefaultEncoding()


# ==================================================
# FapBaseClient
# ==================================================
class FapBaseClient:
    module = None  # AnsibleModule
    logger = None
    params = None
    commands = None
    result_type = None

    ip = None
    port = None
    network_os = None
    user_id = None
    user_password = None
    become_method = None
    become_password = None
    ssh_port = None
    ssh_key_file = None

    client = None
    device_prompt = None

    # Session status
    status = FAP.SessionStatus.READY

    def __init__(self, module, logger, _params, _commands):

        self.module = module
        self.logger = logger
        self.params = _params

        self.logger.debug(
            f"- RAW_COMMAND_DATA_TYPE = {FAP.checkDataType(_commands)[0]}"
        )
        self.logger.debug(f"- RAW_COMMAND = {_commands}")

        self.commands = []

        # Single command
        if isinstance(_commands, str):
            cmd_item = {}
            cmd_item["command"] = _commands
            self.commands.append(cmd_item)
        # Multiple command
        elif isinstance(_commands, list):
            for _cmd in _commands:
                if isinstance(_cmd, str):
                    cmd_item = {}
                    cmd_item["command"] = _cmd
                    self.commands.append(cmd_item)
                elif isinstance(_cmd, dict):
                    self.commands.append(_cmd)

        self.logger.info(f"- EXEC_COMMAND = {self.commands}")

        self.ip = FAP.getDicValue(self.params, "ip", None)
        self.ssh_port = FAP.getDicValue(self.params, "ssh_port", None)
        self.ssh_key_file = FAP.getDicValue(self.params, "ssh_key_file", None)
        self.network_os = FAP.getDicValue(self.params, "network_os", None)
        self.user_id = FAP.getDicValue(self.params, "user_id", None)
        self.user_password = FAP.getDicValue(self.params, "user_password", None)
        self.become_user = FAP.getDicValue(self.params, "become_user", None)
        self.become_method = FAP.getDicValue(self.params, "become_method", None)
        self.become_password = FAP.getDicValue(self.params, "become_password", None)
        self.result_type = FAP.getDicValue(self.params, "result_type", None)
        self.job_id = FAP.getDicValue(self.params, "job_id", None)
        self.ssh_params = FAP.getDicValue(self.params, "ssh_params", None)

        self.logger.info(f"- VERBOSITY LEVEL = {self.module._verbosity}")

    # ==================================================
    # * Connect (Must be define)
    # ==================================================
    def connect(self):
        raise ValueError(f"[ERROR] Must define the connect() function")
        return False

    def isConnected(self):
        if (
            self.status != FAP.SessionStatus.READY
            and self.status != FAP.SessionStatus.DISCONNECTED
        ):
            return True
        else:
            return False

    # ==================================================
    # * Send (Must be define)
    # ==================================================
    def send(self, command, isSecured=False):
        raise ValueError(f"[ERROR] Must define the send() function")
        return False

    # ==================================================
    # * Expect (Must be define)
    # ==================================================
    def expect(self, patterns=None, timeout=5):
        raise ValueError(f"[ERROR] Must define the expect() function")
        return None

    # ==================================================
    # Close
    # ==================================================
    def close(self):
        if self.client != None:
            self.client.close()
            self.client = None

            # stuats = DISCONNECTED
            self.status = FAP.SessionStatus.DISCONNECTED
            self.logger.info(f"- STATUS = {self.status}")

    # ==================================================
    # Execute
    # ==================================================
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
            if self.result_type in ["dict"]:  # dic
                result_data = {}
            elif self.result_type == "cli_data":  # cli_data
                result_data = {}
                result_data["data_list"] = []
            else:  # list (default)
                result_data = []

            index = 0
            for cmd_item in commands:

                # Sleep time = 0.1 ~ 300 seconds
                _sleep = FAP.getDicValue(cmd_item, "sleep", None)
                if _sleep:
                    _sleep = FAP.str2num(_sleep, None, 0.1, 300)
                    if _sleep and _sleep > 0:
                        self.logger.info(f"- SLEEP: {_sleep} seconds")
                        time.sleep(_sleep)

                # Clear recv buffer
                # self.expect(None, 2)
                self.expect(None, 0.2)

                # Get command string
                command = FAP.getDicValue(cmd_item, "command", None)
                if not command:
                    continue

                # Execute timeout = 5 ~ 120 seconds
                # timeout = 5
                # _timeout = FAP.getDicValue(cmd_item, "timeout", None)
                # if _timeout:
                #     _timeout = FAP.str2num(_timeout, None, 0, 120)
                #     if _timeout and _timeout > 5:
                #         timeout = _timeout
                _timeout = FAP.getDicValue(cmd_item, "timeout", None)
                timeout = FAP.str2num(_timeout, 5, 0.1, 1000)  # ← 기본 값 5, 최소 0.1초부터 1000초까지 허용
                
                self.logger.info(
                    f"- SEND COMMAND: {command} (timeout={timeout} seconds)"
                )

                # Check save flag
                isSaveOuput = False
                if FAP.getDicValue(cmd_item, "is_save", False) == True:
                    isSaveOuput = True
                if command[0] == "*":
                    command = command[1:]
                    isSaveOuput = True

                # Execute command
                output = self.executeCommand(command, timeout)
                output = self._handle_expect(cmd_item, output, expect_timeout=3)
                            
                self.logger.info(f"- PROCESS END: {command}")

                time.sleep(0.1)

                # Check save flag
                if not isSaveOuput:
                    continue

                # Make output item
                index = index + 1

                # Make result
                if self.result_type == "dict":
                    # dictinary
                    result_data[command] = output
                else:
                    # list, cli_data
                    output_item = {}
                    output_item["index"] = index
                    output_item["cmd"] = command
                    output_item["output"] = output

                    if not FAP.isBlank(output):
                        output_item["is_success"] = True
                    else:
                        output_item["is_success"] = False

                    # list
                    if self.result_type == "list":
                        result_data.append(output_item)

                    # ansible_cli_data
                    elif self.result_type == "cli_data":
                        # host_name
                        output_item["host_name"] = self.ip
                        # cmd_id
                        _cmd_id = FAP.getDicValue(
                            cmd_item, "cmd_id", FAP.getDicValue(cmd_item, "id", None)
                        )
                        if _cmd_id is None:
                            _cmd_id = index
                        output_item["cmd_id"] = _cmd_id
                        # cmd_name
                        _cmd_name = FAP.getDicValue(
                            cmd_item,
                            "cmd_name",
                            FAP.getDicValue(cmd_item, "name", None),
                        )
                        if _cmd_name is None:
                            _cmd_name = command
                        output_item["cmd_name"] = _cmd_name
                        # os
                        _os = FAP.getDicValue(cmd_item, "os", None)
                        if _os is None:
                            _os = self.network_os
                        output_item["os"] = _os
                        # insert_time
                        output_item["insert_time"] = FAP.timestampMilliSec64()

                        # Copy cmd_item values
                        exclude_keys = [
                            "index",
                            "id",
                            "cmd",
                            "output",
                            "is_success",
                            "is_save",
                            "timeout",
                        ]
                        for key, value in cmd_item.items():
                            if key not in exclude_keys and key not in output_item:
                                output_item[key] = value

                        result_data["data_list"].append(output_item)

                # Sleep 1 seconds
                time.sleep(0.1)

            return result_data

        except Exception as err:
            self.logger.exception(err)
            # 커스텀 에러는 그대로 다시 raise
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))
            return None

    # ==================================================
    # Check prompt
    # ==================================================
    def _checkPrompt(self):
        try:

            time.sleep(1)
            if self.network_os == "v2024g":
                self.logger.debug(f"v2024g is more sleep 5 seconds")
                time.sleep(5)

            self.logger.info(f"- START CHECK_PROMPT FUNCTION")

            if self.network_os == "freebsd":
                self.logger.info(
                    f"- !!! FreeBSD OS !!! PASS MENU WINDOW: 'tools' -> 'shell' "
                )
                self.send("t\n")
                time.sleep(1)
                self.send("s\n")

            if self.network_os == "aos":
                self.logger.info(f"- !!! AOS OS !!! RE-ENTER USERNAME & PASSWORD")
                self.send(f"{self.user_password}\n")
                time.sleep(1)
                self.send(f"start-shell\n")

            if self.network_os == "genian":
                self.logger.info(f"Try {self.network_os}'s LOGIN")
                self.send(f"{self.user_password}\r")
                self.send("enable\r")
                self.send(f"{self.user_password}\r")
                self.send("@shell\r")

            self.send("\n\n")

            # Recv data
            output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2], 2)
            if output_lines is None or len(output_lines) == 0:
                self.logger.info(f"- PROMPT STRING IS NONE")
                return False

            output = output_lines[-1]
            if FAP.isBlank(output):
                self.logger.info(f"- PROMPT STRING IS NONE")
                return False

            self.logger.debug(f"[RAW>>] {output}")

            if re.search(r"[Pp]assword:", output):
                raise Exception(f"Login Failed: {output}")

            # Check prompt
            if re.search(FAP.PATTERN_PROMPT, output) or re.search(
                FAP.PATTERN_PROMPT2, output
            ):

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

            # Find enable
            enableCmd = None

            # set enableCmd
            if self.become_method:
                # In the 'su' command, the hyphen '-' means to start a login shell.
                # This loads the target user's environment variables, profile scripts, and sets up the shell as if the user had logged in directly.
                # Without '-', the environment is only partially changed.
                if self.become_user: enableCmd = f"{self.become_method} - {self.become_user}"
                else: enableCmd = f"{self.become_method} -"

            enableCmdModels = ["V2024G", "E6300", "V8605", "V8607", "E4020", "E5010"]
            if self.network_os:
                if (
                    self.network_os.upper().startswith("CISCO")
                    or self.network_os.upper() in enableCmdModels
                ):
                    enableCmd = "enable"
                elif self.network_os.upper().startswith("HP"):
                    enableCmd = "super"
                elif self.network_os.upper().startswith("ARISTA"):
                    enableCmd = "enable"
                elif self.network_os.upper().startswith("MX"):
                    enableCmd = "cli"

            self.logger.info(f"# enableCmd ===================== {enableCmd}")

            if self.become_password == "":
                self.become_password = "nopassword"
                self.logger.info(
                    f"$ become_password is '' so update ---> {self.become_password}"
                )

            # Enter enable mode
            if not FAP.isBlank(enableCmd) and not FAP.isBlank(self.become_password):

                self.logger.info("# SEND-ENABLE-COMMAND")
                self.send(enableCmd + "\n")

                # Check password input
                output_lines = self.expect([FAP.PATTERN_PASSWORD])
                self.logger.info(f"[DEBUG LYH] {output_lines}")
                if output_lines is None or len(output_lines) == 0:
                    return False

                output = output_lines[-1]
                self.logger.debug(f"[ - DEVICE PROMPT]: //{self.device_prompt}//")
                if self.device_prompt == "% ":
                    self.logger.debug(f"# juniper exception case")
                    self.device_prompt = output  # juniper exception case
                    self.logger.debug(
                        f"# juniper exception case self.device_prompt update {self.device_prompt}"
                    )

                if FAP.isBlank(output):
                    return False

                self.logger.debug("[RAW>>] " + output)

                if re.search(FAP.PATTERN_PASSWORD, output):

                    # Send enable password
                    self.logger.info("# SEND-ENABLE-PASSWORD")

                    self.send(self.become_password + "\r\n", True)

                    # Check enable mode prompt
                    output_lines = self.expect([FAP.PATTERN_EN_PROMPT, FAP.PATTERN_PASSWORD], 1)
                    self.logger.info(f"enable mode prompt ---> {output_lines}")

                    if output_lines is None or len(output_lines) == 0:
                        return False
                    
                    
                    output = output_lines[-1]
                    if FAP.isBlank(output):
                        return False

                    self.logger.info(f"[_checkPrompt][RAW>>] {output}")
                    output_tmp = '\n'.join(output_lines)

                    if re.search(FAP.PATTERN_EN_PROMPT, output):
                        self.device_prompt = output
                        self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")

                        # stuats = EN_PROMPT
                        self.status = FAP.SessionStatus.EN_PROMPT
                        self.logger.info(f"- STATUS = {self.status}")
                        self.logger.info(f"- ENABLE-PROMPT-OK")
                        return True
                    # 인증 실패 패턴을 찾는 경우 해당 구문은 실행되지 않는다.
                    elif ((re.search(FAP.PATTERN_PROMPT, output) 
                          or re.search(FAP.PATTERN_PROMPT2, output))
                          and not re.search(FAP.PATTERN_AUTH_FAIL, output_tmp, re.IGNORECASE)):
                        self.device_prompt = output
                        self.logger.info(f"- PROMPT_STRING = {self.device_prompt}")
                        return True
                    else:
                        self.logger.info(f"- ENABLE-PROMPT-FAILED")
                        curr_date = datetime.datetime.now().strftime('%Y%m%d')
                        raise FAP.EnablePromptError(f"Failed to enter enable prompt mode. debug /fap/logs/ansible/{curr_date}/job_{self.job_id}_{self.ip}.log")                        
                else:
                    return False

            return True
        except Exception as err:
            self.logger.exception(err)
            # 커스텀 에러는 그대로 다시 raise
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))
            return False

    # ==================================================
    # Execute command
    # ==================================================
    def executeCommand(self, command, timeout=0.1):
        try:
            if FAP.isBlank(command):
                return None

            # Send data
            self.send(command + "\n")

            # Recv output
            output = ""
            isFeedbackCommand = False

            isRunning = True
            start_time = time.time()
            tmp_start_time = time.time()

            while isRunning:
                output_lines = self.expect(
                    [FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT], 1
                )

                if output_lines is not None and len(output_lines) > 0:
                    if time.time() - tmp_start_time > timeout:
                        self.logger.debug(
                            f"output line is incoming. but timeout is occured!!! send ctrl+c data"
                        )
                        self.send("\x03")
                        isRunning = False
                    start_time = time.time()
                    self.logger.debug(f"--> TIME UPDATED: time={int(start_time)}")
                elif time.time() - start_time > timeout:
                    self.logger.debug(
                        f"--> TIME-OUT. curr={int(time.time())}, elapsed={int(time.time()-start_time)}"
                    )
                    self.logger.debug(f"--> DEVICE_PROMPT: {self.device_prompt}")
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

                        if line.endswith("\n"):
                            output += line
                        else:
                            output += line + "\n"

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

    # ==================================================
    # Check risk commands
    # ==================================================
    def checkRiskCommands(self, commands):

        if commands is None or not isinstance(commands, list):
            raise TypeError("Value should be a list")

        riskPatterns = []
        riskPatterns.append(r"^\s*(reload|reboot)\s*$")
        riskPatterns.append(
            r"^\s*(write erease|(erase|delete) startup-config|unconfigure switch all)\s*$"
        )
        riskPatterns.append(r"^\s*(debug \S+|debug all)\s*$")

        self.logger.debug(f"[RISK_CHECK] riskPatterns = {riskPatterns}")

        # Commands
        for cmd_item in commands:
            command = FAP.getDicValue(cmd_item, "command", None)
            if not command:
                continue

            self.logger.debug(f"[RISK_CHECK] command = {command}")

            # check risk patterns
            for pattern in riskPatterns:

                match = re.search(pattern, command, re.IGNORECASE | re.MULTILINE)
                if match and match.group():
                    risk_cmd = match.group()
                    return risk_cmd.strip()

        return None

    def _handle_expect(self, cmd_item, full_output, expect_timeout=3):
        """Handle expect functionality for a command item
        
        Args:
            cmd_item (dict): Command item containing expect settings
            full_output (str): Current command output
            expect_timeout (int): Default timeout for expect operations (seconds)
            
        Returns:
            str: Updated full output after handling expect operations
            
        Process:
            1. Get expect and global_expect settings from cmd_item
            2. For each expect item:
               - Get prompt, answer, and timeout settings
               - Check last 3 lines of output for pattern matching
               - Handle global expect patterns if present
               - Handle local prompt patterns
               - Send answer and wait for response
        """
        self.logger.info("=== Starting expect handling ===")
        
        # Get expect settings
        expect_list = FAP.getDicValue(cmd_item, "expect", None)
        global_expect = FAP.getDicValue(cmd_item, "global_expect", None)
        self.logger.info(f"- Found expect_list: {expect_list is not None}")
        self.logger.info(f"- Found global_expect: {global_expect is not None}")
        
        # Initialize counters
        global_match_count = 0
        global_match_max_count = 3
        self.logger.info(f"- Global match limit: {global_match_max_count}")
        
        if expect_list and isinstance(expect_list, list):
            self.logger.info(f"- Processing {len(expect_list)} expect items")
            
            for idx, expect_item in enumerate(expect_list, 1):
                self.logger.info(f"\n=== Processing expect item {idx}/{len(expect_list)} ===")
                
                # Get expect settings
                prompt = FAP.getDicValue(expect_item, "prompt", None)
                answer = FAP.getDicValue(expect_item, "answer", None)
                item_timeout = FAP.getDicValue(expect_item, "timeout", expect_timeout)
                optional_prompt = FAP.getDicValue(expect_item, "optional_prompt", None)
                optional_answer = FAP.getDicValue(expect_item, "optional_answer", None)
                
                self.logger.info(f"- Prompt: {prompt}")
                self.logger.info(f"- Answer: {answer}")
                self.logger.info(f"- Timeout: {item_timeout} seconds")
                self.logger.info(f"- Optional prompt: {optional_prompt}")
                self.logger.info(f"- Optional answer: {optional_answer}")
                
                if prompt and answer is not None:
                    # Get last 3 lines of current output
                    output_lines = full_output.split('\n')
                    last_lines = output_lines[-3:] if len(output_lines) >= 3 else output_lines
                    combined_lines = '\n'.join(last_lines)
                    
                    self.logger.info(f"- Last output lines: {last_lines}")
                    self.logger.info(f"- Combined lines for matching: {combined_lines}")
                    
                    # Handle global expect patterns first
                    if global_expect and isinstance(global_expect, list):
                        self.logger.info("- Checking global expect patterns")
                        full_output, combined_lines = self._handle_global_expect(
                            global_expect, combined_lines, full_output, 
                            global_match_count, global_match_max_count, 
                            item_timeout
                        )
                    
                    # Handle local prompt patterns first
                    if optional_prompt and optional_answer is not None:
                        self.logger.info("- Checking optional prompt patterns")
                        matched = self._check_prompt_match(optional_prompt, combined_lines)
                        self.logger.info(f"- Optional pattern match result: {matched}")
                        if matched:
                            self.send(optional_answer + "\n")
                            new_output = self.expect(patterns= prompt if isinstance(prompt,list) else [prompt], timeout=item_timeout)
                            if new_output:
                                self.logger.info("- Received new output")
                                full_output += "\n" + "\n".join(new_output)
                                output_lines = full_output.split('\n')
                                last_lines = output_lines[-3:] if len(output_lines) >= 3 else output_lines
                                combined_lines = '\n'.join(last_lines)
                                self.logger.info(f"- Updated combined lines: {combined_lines}")
                                                        

                    # Handle local prompt patterns
                    self.logger.info("- Checking local prompt patterns")
                    matched = self._check_prompt_match(prompt, combined_lines)
                    
                    self.logger.info(f"- Pattern match result: {matched}")
                    if not matched:
                        error_msg = (f"Expected prompt pattern '{prompt}' not found" 
                                   if isinstance(prompt, str) 
                                   else f"None of the expected prompt patterns {prompt} found")
                        self.logger.error(f"- Error: {error_msg}")
                        raise ValueError(f"{error_msg} in ({combined_lines})")
                    
                    # Send answer and wait for response
                    self.logger.info("- Sending answer and waiting for response")
                    self.send(answer + "\n")
                    new_output = self.expect(patterns=[FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2], timeout=item_timeout)
                    
                    
                    if new_output:
                        self.logger.info("- Received new output")
                        full_output += "\n" + "\n".join(new_output)
                    else:
                        self.logger.info("- No new output received")
                else:
                    self.logger.warning("- Skipping expect item: missing prompt or answer")
        
        self.logger.info("=== Expect handling completed ===")
        return full_output

    def _handle_global_expect(self, global_expect, combined_lines, full_output, 
                            global_match_count, global_match_max_count, expect_timeout):
        """Handle global expect patterns
        
        Args:
            global_expect (list): List of global expect patterns
            combined_lines (str): Combined output lines to check against
            full_output (str): Current full output
            global_match_count (int): Current count of global matches
            global_match_max_count (int): Maximum allowed global matches
            expect_timeout (int): Default timeout for expect operations (seconds)
            
        Returns:
            tuple: (updated_full_output, matched_status)
        """
        self.logger.info("=== Processing global expect patterns ===")
        global_matched = False
        
        for idx, global_item in enumerate(global_expect, 1):
            self.logger.info(f"\n- Checking global pattern {idx}/{len(global_expect)}")
            
            global_prompt = FAP.getDicValue(global_item, "prompt", None)
            global_answer = FAP.getDicValue(global_item, "answer", None)
            global_timeout = FAP.getDicValue(global_item, "timeout", 5)
            
            self.logger.info(f"- Global timeout: {global_timeout} seconds")
            
            if global_prompt and global_answer is not None:
                if isinstance(global_prompt, str):
                    self.logger.info(f"- Checking global single pattern: {global_prompt}")
                    if global_prompt in combined_lines:
                        if global_match_count >= global_match_max_count:
                            self.logger.warning(f"- Global match limit reached: {global_match_count}")
                            break
                        self.logger.info(f"- Pattern matched: {global_prompt}")
                        self.send(global_answer + "\n")
                        new_output = self.expect(timeout=global_timeout)
                        if new_output:
                            full_output += "\n" + "\n".join(new_output)
                            combined_lines = '\n'.join(new_output)
                        global_matched = True
                        global_match_count += 1
                        break
                elif isinstance(global_prompt, list):
                    self.logger.info(f"- Checking multiple patterns: {global_prompt}")
                    for pattern in global_prompt:
                        if pattern in combined_lines:
                            if global_match_count >= global_match_max_count:
                                self.logger.warning(f"- Global match limit reached: {global_match_count}")
                                break
                            self.logger.info(f"- Pattern matched: {pattern}")
                            self.send(global_answer + "\n")
                            new_output = self.expect(timeout=global_timeout)
                            if new_output:
                                full_output += "\n" + "\n".join(new_output)
                                combined_lines = '\n'.join(new_output)
                            global_matched = True
                            global_match_count += 1
                            break
                    if global_matched:
                        break
            else:
                self.logger.warning("- Skipping global pattern: missing prompt or answer")
        
        self.logger.info(f"- Global pattern processing completed. Matched: {global_matched}")
        return full_output, combined_lines

    def _check_prompt_match(self, prompt, combined_lines):
        """Check if prompt pattern matches combined lines
        
        Args:
            prompt (str or list): Prompt pattern(s) to check
            combined_lines (str): Combined output lines to check against
            
        Returns:
            bool: True if any prompt pattern matches
        """
        self.logger.info("=== Checking prompt match ===")
        
        if isinstance(prompt, str):
            self.logger.info(f"- Checking single pattern: {prompt}")
            result = prompt in combined_lines
            self.logger.info(f"- Match result: {result}")
            return result
        elif isinstance(prompt, list):
            self.logger.info(f"- Checking multiple patterns: {prompt}")
            for pattern in prompt:
                if pattern in combined_lines:
                    self.logger.info(f"- Pattern matched: {pattern}")
                    return True
            self.logger.info("- No patterns matched")
            return False
        else:
            self.logger.warning(f"- Invalid prompt type: {type(prompt)}")
            return False
