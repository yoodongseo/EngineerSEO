# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import datetime
import re
import time

import ansible.module_utils.fap_common_prompt as FAP


class FapBasePromptClient:
    module = None
    logger = None
    params = None
    commands = None
    result_type = None

    ip = None
    port = None
    target_type = None
    user_id = None
    user_password = None
    become_method = None
    become_password = None
    ssh_port = None
    ssh_params = None
    job_id = None

    client = None
    device_prompt = None
    prompt_patterns = None
    prompt_stack = None
    last_debug_info = None

    status = FAP.SessionStatus.READY

    def _normalize_target_type(self, value):
        normalized = str(value or "server").strip().lower()
        if normalized not in ["server", "network"]:
            return "server"
        return normalized

    def __init__(self, module, logger, _params, _commands):
        self.module = module
        self.logger = logger
        self.params = _params
        self.commands = []

        if isinstance(_commands, str):
            self.commands.append({"command": _commands})
        elif isinstance(_commands, list):
            for item in _commands:
                if isinstance(item, str):
                    self.commands.append({"command": item})
                elif isinstance(item, dict):
                    self.commands.append(item)

        self.ip = FAP.getDicValue(self.params, "ip", None)
        self.ssh_port = FAP.getDicValue(self.params, "ssh_port", 22)
        self.port = FAP.getDicValue(self.params, "telnet_port", 23)
        self.ssh_params = FAP.getDicValue(self.params, "ssh_params", None)
        self.target_type = self._normalize_target_type(FAP.getDicValue(self.params, "target_type", "server"))
        self.user_id = FAP.getDicValue(self.params, "user_id", None)
        self.user_password = FAP.getDicValue(self.params, "user_password", None)
        self.become_user = FAP.getDicValue(self.params, "become_user", None)
        self.become_method = FAP.getDicValue(self.params, "become_method", None)
        self.become_password = FAP.getDicValue(self.params, "become_password", None)
        self.result_type = FAP.getDicValue(self.params, "result_type", None)
        self.job_id = FAP.getDicValue(self.params, "job_id", None)

        self.prompt_patterns = []
        # Future phases can use the stack for prompt transitions such as su/rman/sqlplus.
        self.prompt_stack = []
        self.last_debug_info = {}

    def connect(self):
        raise ValueError("Must define connect()")

    def send(self, command, isSecured=False):
        raise ValueError("Must define send()")

    def expect(self, patterns=None, timeout=5):
        raise ValueError("Must define expect()")

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.status = FAP.SessionStatus.DISCONNECTED
            self.logger.info(f"- STATUS = {self.status}")

    def _normalize_prompt(self, line):
        if line is None:
            return None
        prompt = FAP.decodeString(line).strip()
        if FAP.isBlank(prompt):
            return None
        return prompt

    def _learn_prompt(self, line):
        prompt = self._normalize_prompt(line)
        if not prompt:
            return
        self.device_prompt = prompt
        self.prompt_patterns = [re.escape(prompt)]
        self.logger.info(f"- CURRENT_PROMPT = [{self.device_prompt}]")

    def _is_prompt_candidate(self, line):
        if FAP.isBlank(line):
            return False
        for pattern in [FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT, FAP.PATTERN_APP_PROMPT]:
            try:
                if re.search(pattern, line):
                    return True
            except Exception:
                continue
        return False

    def _is_current_prompt(self, line):
        if FAP.isBlank(line) or FAP.isBlank(self.device_prompt):
            return False
        return FAP.comparePromptString(self.device_prompt, line)

    def _is_enable_prompt(self, line=None):
        prompt = self._normalize_prompt(line if line is not None else self.device_prompt)
        if FAP.isBlank(prompt):
            return False

        if prompt.endswith("#") or "(enable)" in prompt.lower():
            return True

        return False

    def _is_root_login(self):
        if FAP.isBlank(self.user_id):
            return False
        return str(self.user_id).strip().lower() == "root"

    def _should_skip_become(self):
        if FAP.isBlank(self.become_method):
            return True

        method = str(self.become_method).strip().lower() if not FAP.isBlank(self.become_method) else ""
        target_user = str(self.become_user).strip().lower() if not FAP.isBlank(self.become_user) else ""

        if method == "enable" and self._is_enable_prompt():
            self.logger.info(f"# already privileged prompt ===================== {self.device_prompt}")
            return True

        if method in ["su", "sudo"] and self._is_root_login() and (target_user in ["", "root"]):
            self.logger.info(f"# already root login ===================== user_id={self.user_id}")
            return True

        return False

    def _get_login_prompt_timeouts(self):
        configured_max = FAP.getDicValue(self.ssh_params, "login_prompt_timeout", None)
        if configured_max is None:
            configured_max = FAP.getDicValue(self.ssh_params, "prompt_timeout", 60)
        configured_max = FAP.str2num(configured_max, 60, 1, 60)

        stages = [10, 15, 30, 40, 60]
        timeout_steps = [step for step in stages if step <= configured_max]
        if not timeout_steps or timeout_steps[-1] != configured_max:
            timeout_steps.append(configured_max)
        return timeout_steps

    def _build_become_command(self):
        enable_cmd = None

        if self.become_method:
            method = str(self.become_method).strip().lower()
            if method == "su":
                if self.become_user:
                    enable_cmd = f"su - {self.become_user}"
                else:
                    enable_cmd = "su -"
            elif method == "sudo":
                if self.become_user:
                    enable_cmd = f"sudo -iu {self.become_user}"
                else:
                    enable_cmd = "sudo -i"
            elif method == "enable":
                enable_cmd = "enable"
            else:
                if self.become_user:
                    enable_cmd = f"{self.become_method} - {self.become_user}"
                else:
                    enable_cmd = f"{self.become_method} -"

        return enable_cmd

    def _apply_become(self):
        if self._should_skip_become():
            return True

        enable_cmd = self._build_become_command()
        if FAP.isBlank(enable_cmd):
            return True

        self.logger.info(f"# enableCmd ===================== {enable_cmd}")
        self.logger.info("# SEND-ENABLE-COMMAND")
        self.send(enable_cmd + "\n")

        patterns = [FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT, FAP.PATTERN_PASSWORD]
        output_lines = self.expect(patterns, 5)
        if not output_lines:
            return False

        last_non_empty = None
        for line in output_lines:
            if not FAP.isBlank(line):
                last_non_empty = line

        if last_non_empty is None:
            return False

        normalized = FAP.decodeString(last_non_empty).strip()
        if re.search(FAP.PATTERN_PASSWORD, normalized, re.IGNORECASE):
            if FAP.isBlank(self.become_password):
                raise ValueError(f"Become password required: {normalized}")

            self.logger.info("# SEND-ENABLE-PASSWORD")
            self.send(self.become_password + "\n", True)
            output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT, FAP.PATTERN_PASSWORD], 8)
            if not output_lines:
                return False

            last_non_empty = None
            for line in output_lines:
                if not FAP.isBlank(line):
                    last_non_empty = line

            if last_non_empty is None:
                return False
            normalized = FAP.decodeString(last_non_empty).strip()

            if re.search(FAP.PATTERN_PASSWORD, normalized, re.IGNORECASE):
                raise ValueError(f"Become authentication failed: {normalized}")

        if re.search(FAP.PATTERN_AUTH_FAIL, normalized, re.IGNORECASE):
            raise ValueError(normalized)

        if self._is_prompt_candidate(normalized):
            previous_prompt = self.device_prompt
            self.prompt_stack.append(previous_prompt)
            self._learn_prompt(normalized)
            return True

        return False

    def _confirm_prompt_change(self, candidate_prompt):
        if FAP.isBlank(candidate_prompt):
            return False

        probe_lines = []
        probe_error_lines = []
        try:
            self.send("\n")
        except Exception:
            return False

        patterns = [re.escape(candidate_prompt)]
        if self.device_prompt:
            patterns.append(re.escape(self.device_prompt))

        for _ in range(3):
            output_lines = self.expect(patterns, 0.1)
            if output_lines:
                probe_lines.extend(output_lines)
                for line in output_lines:
                    if FAP.isBlank(line):
                        continue
                    normalized = self._normalize_prompt(line)
                    decoded_line = FAP.decodeString(line).strip()
                    if re.search(FAP.PATTERN_AUTH_FAIL, decoded_line, re.IGNORECASE) or re.search(
                        r"(ORA-|RMAN-|SP2-|ERROR|FAILED|DENIED|UNKNOWN|INVALID|USAGE)",
                        decoded_line,
                        re.IGNORECASE,
                    ):
                        probe_error_lines.append(decoded_line)
                    if normalized and FAP.comparePromptString(candidate_prompt, normalized):
                        self.last_debug_info["prompt_probe_lines"] = [
                            FAP.decodeString(item).strip() for item in probe_lines if not FAP.isBlank(item)
                        ]
                        self.last_debug_info["prompt_probe_error_lines"] = probe_error_lines
                        self.last_debug_info["prompt_change_confirmed"] = True
                        self.last_debug_info["prompt_change_probe_result"] = "prompt_reappeared"
                        return True

        self.last_debug_info["prompt_probe_lines"] = [
            FAP.decodeString(item).strip() for item in probe_lines if not FAP.isBlank(item)
        ]
        self.last_debug_info["prompt_probe_error_lines"] = probe_error_lines
        self.last_debug_info["prompt_change_confirmed"] = False
        self.last_debug_info["prompt_change_probe_result"] = "error_without_prompt" if probe_error_lines else "no_prompt_reappeared"
        return False

    def _classify_last_line(self, line):
        if FAP.isBlank(line):
            return "blank"
        normalized = FAP.decodeString(line).strip()
        if self._is_current_prompt(normalized):
            return "current_prompt"
        if self._is_prompt_candidate(normalized):
            return "prompt_candidate"
        if re.search(FAP.PATTERN_PASSWORD, normalized, re.IGNORECASE):
            return "password_prompt"
        if re.search(FAP.PATTERN_AUTH_FAIL, normalized, re.IGNORECASE):
            return "auth_fail"
        if re.search(r"(not found|unknown|invalid|error|failed|denied|usage)", normalized, re.IGNORECASE):
            return "error_line"
        return "non_prompt"

    def _wait_for_prompt(self, max_timeout, command=None):
        collected = []
        command = command.strip() if isinstance(command, str) else None
        start_time = time.time()
        saw_command_echo = False
        saw_payload = False
        leading_prompt_hits = 0
        timed_out = False
        last_non_empty = None

        if self.device_prompt:
            patterns = [re.escape(self.device_prompt)]
        else:
            patterns = [FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT]

        while True:
            output_lines = self.expect(patterns, 0.2)
            if output_lines:
                collected.extend(output_lines)

                last_non_empty = None
                for line in output_lines:
                    if FAP.isBlank(line):
                        continue
                    last_non_empty = line
                    if command and line.strip() == command:
                        saw_command_echo = True
                        continue
                    if not self._is_prompt_candidate(line):
                        saw_payload = True

                if last_non_empty is not None:
                    self.last_debug_info["last_line"] = FAP.decodeString(last_non_empty).strip()
                    self.last_debug_info["last_line_type"] = self._classify_last_line(last_non_empty)
                    self.logger.info(f"- LAST_LINE = [{FAP.decodeString(last_non_empty).strip()}]")
                    if self.device_prompt:
                        prompt_match = self._is_current_prompt(last_non_empty)
                        self.last_debug_info["prompt_match"] = prompt_match
                        self.logger.info(f"- PROMPT_MATCH = {prompt_match}")
                        if prompt_match:
                            if saw_command_echo or saw_payload:
                                return collected, timed_out
                            leading_prompt_hits += 1
                            if leading_prompt_hits >= 2:
                                return collected, timed_out
                        elif self._is_prompt_candidate(last_non_empty):
                            previous_prompt = self.device_prompt
                            new_prompt = self._normalize_prompt(last_non_empty)
                            if previous_prompt and new_prompt and not FAP.comparePromptString(previous_prompt, new_prompt):
                                self.logger.info(f"- PROMPT_CHANGE_CANDIDATE = [{previous_prompt}] -> [{new_prompt}]")
                                self.last_debug_info["prompt_changed_from"] = previous_prompt
                                self.last_debug_info["prompt_changed_to"] = new_prompt
                                if self._confirm_prompt_change(new_prompt):
                                    self.last_debug_info["prompt_changed"] = True
                                    self.logger.info(f"- PROMPT_CHANGED = [{previous_prompt}] -> [{new_prompt}]")
                                    self.prompt_stack.append(previous_prompt)
                                    self._learn_prompt(new_prompt)
                                    if saw_command_echo or saw_payload:
                                        return collected, timed_out
                    elif self._is_prompt_candidate(last_non_empty):
                        self._learn_prompt(last_non_empty)
                        if saw_command_echo or saw_payload:
                            return collected, timed_out
                        leading_prompt_hits += 1
                        if leading_prompt_hits >= 2:
                            return collected, timed_out

            if time.time() - start_time >= max_timeout:
                self.logger.warning(f"max_timeout reached: {max_timeout} seconds")
                if last_non_empty is not None:
                    self.last_debug_info["timeout_last_line"] = FAP.decodeString(last_non_empty).strip()
                    self.last_debug_info["timeout_last_line_type"] = self._classify_last_line(last_non_empty)
                    self.logger.warning(f"- TIMEOUT_LAST_LINE = [{FAP.decodeString(last_non_empty).strip()}]")
                timed_out = True
                self.last_debug_info["timed_out"] = True
                try:
                    self.send("\x03")
                except Exception:
                    pass
                self._drain_recv_buffer(per_try_timeout=0.1, max_tries=5)
                break

        return collected, timed_out

    def _drain_recv_buffer(self, per_try_timeout=0.1, max_tries=5):
        for _ in range(max_tries):
            tail_lines = self.expect(None, per_try_timeout)
            if not tail_lines:
                break

    def execute(self):
        result_data = {} if self.result_type in ["dict", "cli_data"] else []
        if self.result_type == "cli_data":
            result_data["data_list"] = []

        risk_command = self.checkRiskCommands(self.commands)
        if risk_command:
            raise ValueError(f"[REJECT] Contains a risk command: {risk_command}")

        self.status = FAP.SessionStatus.EXECUTE_COMMANDS
        index = 0

        for cmd_item in self.commands:
            self._drain_recv_buffer()

            command = FAP.getDicValue(cmd_item, "command", None)
            if not command:
                continue

            timeout = FAP.str2num(FAP.getDicValue(cmd_item, "timeout", None), 5, 1, 120)

            is_save_output = FAP.getDicValue(cmd_item, "is_save", False) is True
            if command.startswith("*"):
                command = command[1:]
                is_save_output = True

            output = self.executeCommand(command, timeout)

            # Keep expect/global_expect out of the fast path. Future phases can expand this.
            if self._has_expect(cmd_item):
                output = self._handle_expect(cmd_item, output, expect_timeout=timeout)

            if not is_save_output:
                continue

            index += 1
            if self.result_type == "dict":
                result_data[command] = output
                continue

            output_item = {
                "index": index,
                "cmd": command,
                "output": output,
                "is_success": self._is_success_output(output),
                "debug_info": dict(self.last_debug_info or {}),
            }

            if self.result_type == "list":
                result_data.append(output_item)
                continue

            output_item["host_name"] = self.ip
            output_item["cmd_id"] = FAP.getDicValue(cmd_item, "cmd_id", FAP.getDicValue(cmd_item, "id", index))
            output_item["cmd_name"] = FAP.getDicValue(cmd_item, "cmd_name", FAP.getDicValue(cmd_item, "name", command))
            output_item["os"] = FAP.getDicValue(cmd_item, "os", None)
            output_item["insert_time"] = FAP.timestampMilliSec64()

            exclude_keys = ["index", "id", "cmd", "output", "is_success", "is_save", "timeout"]
            for key, value in cmd_item.items():
                if key not in exclude_keys and key not in output_item:
                    output_item[key] = value
            result_data["data_list"].append(output_item)

        return result_data

    def _checkPrompt(self):
        try:
            login_prompt_timeouts = self._get_login_prompt_timeouts()

            self.send("\n")
            output_lines = []
            previous_timeout = 0
            for login_prompt_timeout in login_prompt_timeouts:
                wait_timeout = max(login_prompt_timeout - previous_timeout, 0.1)
                self.logger.info(f"- LOGIN_PROMPT_WAIT = {login_prompt_timeout}s")
                output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2], wait_timeout)
                previous_timeout = login_prompt_timeout
                if output_lines:
                    break
            if not output_lines:
                return False

            last_non_empty = None
            for line in output_lines:
                if not FAP.isBlank(line):
                    last_non_empty = line

            if last_non_empty is None:
                return False

            if re.search(r"[Pp]assword:", last_non_empty):
                raise Exception(f"Login Failed: {last_non_empty}")

            if self._is_prompt_candidate(last_non_empty):
                self._learn_prompt(last_non_empty)
                self.status = FAP.SessionStatus.PROMPT
                if not self._apply_become():
                    return False
                return True

            return False
        except Exception as err:
            self.logger.exception(err)
            if isinstance(err, FAP.EnablePromptError):
                raise
            raise ValueError(str(err))

    def executeCommand(self, command, timeout=5):
        try:
            if FAP.isBlank(command):
                return None

            self.last_debug_info = {
                "command": command,
                "current_prompt": self.device_prompt,
                "last_line": None,
                "last_line_type": None,
                "prompt_match": None,
                "prompt_changed": False,
                "prompt_changed_from": None,
                "prompt_changed_to": None,
                "prompt_change_confirmed": False,
                "prompt_probe_lines": [],
                "prompt_probe_error_lines": [],
                "prompt_change_probe_result": None,
                "timed_out": False,
                "timeout_last_line": None,
                "timeout_last_line_type": None,
            }
            self.logger.info(f"- CMD_START = [{command}]")
            self.logger.info(f"- CMD_PROMPT = [{self.device_prompt}]")
            self.send(command + "\n")
            output = ""
            is_feedback_command = False
            output_lines, timed_out = self._wait_for_prompt(max_timeout=timeout, command=command)
            command_echo_lines = self._normalize_command_lines(command)

            for line in output_lines:
                normalized_line = FAP.decodeString(line).strip()
                if not is_feedback_command and normalized_line == command.strip():
                    is_feedback_command = True
                    continue
                if self._is_command_echo_line(normalized_line, command_echo_lines):
                    continue
                if self._is_current_prompt(line):
                    continue

                output += line if line.endswith("\n") else line + "\n"

            output = self._strip_trailing_current_prompt(output)

            if timed_out:
                self.logger.warning(f"command timeout detected: {command}")
            self.last_debug_info["timed_out"] = timed_out

            return output
        except Exception as err:
            self.logger.exception(err)
            raise ValueError(str(err))

    def checkRiskCommands(self, commands):
        if commands is None or not isinstance(commands, list):
            raise TypeError("Value should be a list")

        risk_patterns = [
            r"^\s*(reload|reboot)\s*$",
            r"^\s*(write erease|(erase|delete) startup-config|unconfigure switch all)\s*$",
            r"^\s*(debug \S+|debug all)\s*$",
        ]
        for cmd_item in commands:
            command = FAP.getDicValue(cmd_item, "command", None)
            if not command:
                continue
            for pattern in risk_patterns:
                match = re.search(pattern, command, re.IGNORECASE | re.MULTILINE)
                if match and match.group():
                    return match.group().strip()
        return None

    def _has_expect(self, cmd_item):
        expect_list = FAP.getDicValue(cmd_item, "expect", None)
        global_expect = FAP.getDicValue(cmd_item, "global_expect", None)
        return bool(expect_list or global_expect)

    def _handle_expect(self, cmd_item, full_output, expect_timeout=3):
        expect_list = FAP.getDicValue(cmd_item, "expect", None)
        global_expect = FAP.getDicValue(cmd_item, "global_expect", None)
        global_match_count = 0
        global_match_max_count = 3

        if expect_list and isinstance(expect_list, list):
            for expect_item in expect_list:
                prompt = FAP.getDicValue(expect_item, "prompt", None)
                answer = FAP.getDicValue(expect_item, "answer", None)
                item_timeout = FAP.getDicValue(expect_item, "timeout", expect_timeout)

                if prompt and answer is not None:
                    output_lines = full_output.split("\n")
                    combined_lines = "\n".join(output_lines[-3:] if len(output_lines) >= 3 else output_lines)

                    if global_expect and isinstance(global_expect, list):
                        full_output, combined_lines, global_match_count = self._handle_global_expect(
                            global_expect,
                            combined_lines,
                            full_output,
                            global_match_count,
                            global_match_max_count,
                            item_timeout,
                        )

                    if not self._check_prompt_match(prompt, combined_lines):
                        raise ValueError(f"Expected prompt pattern '{prompt}' not found in ({combined_lines})")

                    self.send(answer + "\n")
                    new_output = self.expect(timeout=item_timeout)
                    if new_output:
                        full_output += "\n" + "\n".join(new_output)

        return full_output

    def _handle_global_expect(self, global_expect, combined_lines, full_output, global_match_count, global_match_max_count, expect_timeout):
        for global_item in global_expect:
            global_prompt = FAP.getDicValue(global_item, "prompt", None)
            global_answer = FAP.getDicValue(global_item, "answer", None)
            global_timeout = FAP.getDicValue(global_item, "timeout", expect_timeout)

            if global_prompt and global_answer is not None:
                patterns = [global_prompt] if isinstance(global_prompt, str) else global_prompt
                for pattern in patterns:
                    if self._check_prompt_match(pattern, combined_lines):
                        if global_match_count >= global_match_max_count:
                            return full_output, combined_lines, global_match_count
                        self.send(global_answer + "\n")
                        new_output = self.expect(timeout=global_timeout)
                        if new_output:
                            full_output += "\n" + "\n".join(new_output)
                            combined_lines = "\n".join(new_output)
                        global_match_count += 1
                        return full_output, combined_lines, global_match_count

        return full_output, combined_lines, global_match_count

    def _check_prompt_match(self, prompt, combined_lines):
        if isinstance(prompt, str):
            try:
                return re.search(prompt, combined_lines, re.MULTILINE) is not None
            except re.error:
                return prompt in combined_lines
        if isinstance(prompt, list):
            for pattern in prompt:
                if self._check_prompt_match(pattern, combined_lines):
                    return True
        return False

    def _normalize_command_lines(self, command):
        lines = []
        for line in FAP.decodeString(command).splitlines():
            stripped = line.strip()
            if stripped:
                lines.append(stripped)
        return lines

    def _is_command_echo_line(self, normalized_line, command_echo_lines):
        if FAP.isBlank(normalized_line):
            return False
        if normalized_line in command_echo_lines:
            return True

        if normalized_line.startswith(">"):
            heredoc_line = normalized_line[1:].strip()
            if heredoc_line == "EOF" or heredoc_line in command_echo_lines:
                return True

        for command_line in command_echo_lines:
            if "<<" in command_line:
                prefix = command_line.split("<<", 1)[0].strip()
                if prefix and normalized_line.startswith(prefix):
                    return True
        return False

    def _strip_trailing_current_prompt(self, output):
        if FAP.isBlank(output):
            return output

        lines = output.splitlines()
        while lines:
            last_line = lines[-1].strip()
            if FAP.isBlank(last_line):
                lines.pop()
                continue
            if self._is_current_prompt(last_line):
                lines.pop()
                continue
            break

        if not lines:
            return ""
        return "\n".join(lines) + "\n"

    def _is_success_output(self, output):
        if not self.last_debug_info:
            return False
        if self.last_debug_info.get("timed_out"):
            return False
        if self.last_debug_info.get("last_line_type") in ["password_prompt", "auth_fail", "error_line"]:
            return False
        if self.last_debug_info.get("prompt_change_probe_result") == "error_without_prompt":
            return False
        if self.last_debug_info.get("last_line_type") == "non_prompt":
            if not self.last_debug_info.get("prompt_match") and not self.last_debug_info.get("prompt_changed"):
                return False
        if not FAP.isBlank(output):
            return True
        if self.last_debug_info.get("prompt_match"):
            return True
        if self.last_debug_info.get("prompt_changed"):
            return True
        return False
