# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import datetime
import re
import time

import ansible_collections.fap.custom.plugins.module_utils.fap_common_prompt as FAP


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
        normalized = str(value or "mixed").strip().lower()
        if normalized not in ["mixed", "pwonly"]:
            return "mixed"
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
        self.ssh_params = FAP.getDicValue(self.params, "ssh_params", {}) or {}
        self._validate_ssh_timeout_params()
        self.target_type = self._normalize_target_type(FAP.getDicValue(self.params, "target_type", "mixed"))
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

    def _validate_ssh_timeout_params(self):
        if not isinstance(self.ssh_params, dict):
            self.ssh_params = {}
            return

        if "session_timeout" not in self.ssh_params:
            return

        legacy_keys = ["connect_timeout", "banner_timeout", "auth_timeout", "login_prompt_timeout", "prompt_timeout"]
        mixed_keys = [key for key in legacy_keys if key in self.ssh_params]
        if mixed_keys:
            raise ValueError(
                "ssh_params.session_timeout cannot be used with legacy timeout keys: "
                + ", ".join(mixed_keys)
            )

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

    def _is_initial_prompt(self, line):
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

    def _get_login_prompt_timeout(self):
        if "session_timeout" in self.ssh_params:
            configured_max = FAP.getDicValue(self.ssh_params, "session_timeout", 60)
        else:
            configured_max = FAP.getDicValue(self.ssh_params, "login_prompt_timeout", None)
            if configured_max is None:
                configured_max = FAP.getDicValue(self.ssh_params, "prompt_timeout", 60)
        return FAP.str2num(configured_max, 60, 1, 120)

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

    def _record_prompt_check(self, check_lines, check_error_lines, confirmed, result):
        self.last_debug_info["prompt_check_lines"] = [
            FAP.decodeString(item).strip() for item in check_lines if not FAP.isBlank(item)
        ]
        self.last_debug_info["prompt_check_error_lines"] = check_error_lines
        self.last_debug_info["prompt_confirmed"] = confirmed
        self.last_debug_info["prompt_check_result"] = result

    def _find_last_prompt_candidate(self, lines):
        candidate = None
        for line in lines or []:
            if FAP.isBlank(line):
                continue
            if self._is_prompt_candidate(line):
                candidate = self._normalize_prompt(line)
        return candidate

    def _has_non_prompt_output(self, lines):
        for line in lines or []:
            if FAP.isBlank(line):
                continue
            if not self._is_prompt_candidate(line):
                return True
        return False

    def _confirm_prompt_change(self, candidate_prompt, max_probe_time, quiet_timeout=0.3):
        result = {
            "confirmed": False,
            "prompt": None,
            "changed": False,
            "lines": [],
            "error_lines": [],
        }
        if FAP.isBlank(candidate_prompt) or max_probe_time <= 0:
            self._record_prompt_check([], [], False, "no_time_remaining")
            return result

        check_lines = []
        check_error_lines = []
        current_candidate = candidate_prompt
        deadline = time.time() + max_probe_time

        while time.time() < deadline:
            quiet_deadline = min(deadline, time.time() + quiet_timeout)
            quiet_lines = []
            while time.time() < quiet_deadline:
                wait_time = min(0.05, max(0.01, quiet_deadline - time.time()))
                output_lines = self.expect(None, wait_time)
                if output_lines:
                    quiet_lines.extend(output_lines)
                    break

            if quiet_lines:
                check_lines.extend(quiet_lines)
                last_candidate = self._find_last_prompt_candidate(quiet_lines)
                if last_candidate:
                    current_candidate = last_candidate
                continue

            try:
                self.send("\n")
            except Exception:
                self._record_prompt_check(check_lines, check_error_lines, False, "send_failed")
                result["lines"] = check_lines
                result["error_lines"] = check_error_lines
                return result

            remaining = deadline - time.time()
            if remaining <= 0:
                break

            patterns = [re.escape(current_candidate)]
            if self.device_prompt:
                patterns.append(re.escape(self.device_prompt))
            output_lines = self.expect(patterns, min(0.5, max(0.01, remaining)))
            if not output_lines:
                continue

            check_lines.extend(output_lines)
            for line in output_lines:
                if FAP.isBlank(line):
                    continue
                decoded_line = FAP.decodeString(line).strip()
                if re.search(FAP.PATTERN_AUTH_FAIL, decoded_line, re.IGNORECASE) or re.search(
                    r"(ORA-|RMAN-|SP2-|ERROR|FAILED|DENIED|UNKNOWN|INVALID|USAGE)",
                    decoded_line,
                    re.IGNORECASE,
                ):
                    check_error_lines.append(decoded_line)

            last_candidate = self._find_last_prompt_candidate(output_lines)
            if last_candidate:
                current_candidate = last_candidate

            if self._has_non_prompt_output(output_lines):
                continue

            confirmed_prompt = None
            for line in output_lines:
                normalized = self._normalize_prompt(line)
                if not normalized:
                    continue
                if FAP.comparePromptString(current_candidate, normalized):
                    confirmed_prompt = normalized
                elif self.device_prompt and FAP.comparePromptString(self.device_prompt, normalized):
                    confirmed_prompt = normalized

            if confirmed_prompt:
                changed = bool(self.device_prompt and not FAP.comparePromptString(self.device_prompt, confirmed_prompt))
                result.update({
                    "confirmed": True,
                    "prompt": confirmed_prompt,
                    "changed": changed,
                    "lines": check_lines,
                    "error_lines": check_error_lines,
                })
                self._record_prompt_check(check_lines, check_error_lines, True, "prompt_reappeared")
                return result

        result["lines"] = check_lines
        result["error_lines"] = check_error_lines
        check_result = "error_without_prompt" if check_error_lines else "no_prompt_reappeared"
        self._record_prompt_check(check_lines, check_error_lines, False, check_result)
        return result

    def _classify_last_observed_line(self, line):
        if FAP.isBlank(line):
            return "blank"
        normalized = FAP.decodeString(line).strip()
        if self._is_initial_prompt(normalized):
            return "initial_prompt"
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
        timed_out = False
        last_non_empty = None

        if self.device_prompt:
            patterns = [re.escape(self.device_prompt)]
        else:
            patterns = [FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2, FAP.PATTERN_EN_PROMPT]

        while True:
            remaining_timeout = max_timeout - (time.time() - start_time)
            if remaining_timeout <= 0:
                self.logger.warning(f"max_timeout reached: {max_timeout} seconds")
                if last_non_empty is not None:
                    self.last_debug_info["timeout_last_observed_line"] = FAP.decodeString(last_non_empty).strip()
                    self.last_debug_info["timeout_last_observed_line_type"] = self._classify_last_observed_line(last_non_empty)
                    self.logger.warning(f"- TIMEOUT_LAST_LINE = [{FAP.decodeString(last_non_empty).strip()}]")
                timed_out = True
                self.last_debug_info["timed_out"] = True
                try:
                    self.send("\x03")
                except Exception:
                    pass
                self._drain_recv_buffer(per_try_timeout=0.1, max_tries=5)
                break

            output_lines = self.expect(patterns, min(0.2, max(0.01, remaining_timeout)))
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
                    self.last_debug_info["last_observed_line"] = FAP.decodeString(last_non_empty).strip()
                    self.last_debug_info["last_observed_line_type"] = self._classify_last_observed_line(last_non_empty)
                    self.logger.info(f"- LAST_LINE = [{FAP.decodeString(last_non_empty).strip()}]")

                    if self._is_prompt_candidate(last_non_empty):
                        previous_prompt = self.device_prompt
                        candidate_prompt = self._normalize_prompt(last_non_empty)
                        prompt_candidate_is_initial_prompt = self._is_initial_prompt(last_non_empty) if self.device_prompt else False
                        self.last_debug_info["prompt_candidate_is_initial_prompt"] = prompt_candidate_is_initial_prompt
                        self.logger.info(f"- PROMPT_MATCH = {prompt_candidate_is_initial_prompt}")

                        if previous_prompt and candidate_prompt and not FAP.comparePromptString(previous_prompt, candidate_prompt):
                            self.logger.info(f"- PROMPT_CHANGE_CANDIDATE = [{previous_prompt}] -> [{candidate_prompt}]")
                            self.last_debug_info["previous_prompt"] = previous_prompt
                            self.last_debug_info["prompt_candidate"] = candidate_prompt

                        remaining_timeout = max_timeout - (time.time() - start_time)
                        check_result = self._confirm_prompt_change(candidate_prompt, remaining_timeout)
                        check_lines = check_result.get("lines", [])
                        if check_lines:
                            collected.extend(check_lines)
                            for check_line in check_lines:
                                if FAP.isBlank(check_line):
                                    continue
                                last_non_empty = check_line
                                if not self._is_prompt_candidate(check_line):
                                    saw_payload = True

                        if check_result.get("confirmed"):
                            self.last_debug_info["confirmed_prompt"] = check_result.get("prompt")
                            if self.last_debug_info.get("prompt_status") != "changed":
                                self.last_debug_info["prompt_status"] = "unchanged"
                            confirmed_prompt = check_result.get("prompt")
                            if confirmed_prompt:
                                if self.device_prompt and not FAP.comparePromptString(self.device_prompt, confirmed_prompt):
                                    self.last_debug_info["prompt_status"] = "changed"
                                    self.last_debug_info["previous_prompt"] = self.device_prompt
                                    self.last_debug_info["prompt_candidate"] = confirmed_prompt
                                    self.logger.info(f"- PROMPT_CHANGED = [{self.device_prompt}] -> [{confirmed_prompt}]")
                                    self.prompt_stack.append(self.device_prompt)
                                    self._learn_prompt(confirmed_prompt)
                                elif not self.device_prompt:
                                    self._learn_prompt(confirmed_prompt)
                            if saw_command_echo or saw_payload or confirmed_prompt:
                                return collected, timed_out

        return collected, timed_out

    def _drain_recv_buffer(self, per_try_timeout=0.1, max_tries=5):
        drained = []
        for _ in range(max_tries):
            tail_lines = self.expect(None, per_try_timeout)
            if not tail_lines:
                break
            drained.extend(tail_lines)
        return drained
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
                "debug_info": self._get_public_debug_info(),
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

    def _checkPrompt(self, login_prompt_timeout=None):
        try:
            if login_prompt_timeout is None:
                login_prompt_timeout = self._get_login_prompt_timeout()

            self.send("\n")
            prompt_wait_start = time.time()
            output_lines = self.expect([FAP.PATTERN_PROMPT, FAP.PATTERN_PROMPT2], login_prompt_timeout)
            prompt_elapsed = time.time() - prompt_wait_start
            if not output_lines:
                self.logger.warning(f"- LOGIN_PROMPT_TIMEOUT elapsed={prompt_elapsed:.2f}s timeout={login_prompt_timeout}s")
                return False
            self.logger.info(f"- LOGIN_PROMPT_FOUND elapsed={prompt_elapsed:.2f}s")

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

    def _get_public_debug_info(self):
        debug_info = self.last_debug_info or {}
        return {
            "command": debug_info.get("command"),
            "initial_prompt": debug_info.get("initial_prompt"),
            "confirmed_prompt": debug_info.get("confirmed_prompt"),
            "prompt_status": debug_info.get("prompt_status"),
            "prompt_check_result": debug_info.get("prompt_check_result"),
            "prompt_check_lines": debug_info.get("prompt_check_lines", []),
            "timed_out": debug_info.get("timed_out", False),
            "timeout_last_line": debug_info.get("timeout_last_observed_line"),
        }


    def executeCommand(self, command, timeout=5):
        try:
            if FAP.isBlank(command):
                return None

            self.last_debug_info = {
                "command": command,
                "initial_prompt": self.device_prompt,
                "last_observed_line": None,
                "last_observed_line_type": None,
                "prompt_candidate_is_initial_prompt": None,
                "prompt_status": "unknown",
                "confirmed_prompt": None,
                "previous_prompt": None,
                "prompt_candidate": None,
                "prompt_confirmed": False,
                "prompt_check_lines": [],
                "prompt_check_error_lines": [],
                "prompt_check_result": None,
                "timed_out": False,
                "timeout_last_observed_line": None,
                "timeout_last_observed_line_type": None,
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
                if self._is_initial_prompt(line):
                    continue

                output += line if line.endswith("\n") else line + "\n"

            output = self._strip_trailing_initial_prompt(output)

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

                    if not self._check_prompt_candidate_is_initial_prompt(prompt, combined_lines):
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
                    if self._check_prompt_candidate_is_initial_prompt(pattern, combined_lines):
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

    def _check_prompt_candidate_is_initial_prompt(self, prompt, combined_lines):
        if isinstance(prompt, str):
            try:
                return re.search(prompt, combined_lines, re.MULTILINE) is not None
            except re.error:
                return prompt in combined_lines
        if isinstance(prompt, list):
            for pattern in prompt:
                if self._check_prompt_candidate_is_initial_prompt(pattern, combined_lines):
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

    def _strip_trailing_initial_prompt(self, output):
        if FAP.isBlank(output):
            return output

        lines = output.splitlines()
        while lines:
            last_observed_line = lines[-1].strip()
            if FAP.isBlank(last_observed_line):
                lines.pop()
                continue
            if self._is_initial_prompt(last_observed_line):
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
        if self.last_debug_info.get("last_observed_line_type") in ["password_prompt", "auth_fail", "error_line"]:
            return False
        if self.last_debug_info.get("prompt_check_result") == "error_without_prompt":
            return False
        if self.last_debug_info.get("last_observed_line_type") == "non_prompt":
            if not self.last_debug_info.get("prompt_candidate_is_initial_prompt") and self.last_debug_info.get("prompt_status") != "changed":
                return False
        if not FAP.isBlank(output):
            return True
        if self.last_debug_info.get("prompt_candidate_is_initial_prompt"):
            return True
        if self.last_debug_info.get("prompt_status") == "changed":
            return True
        return False
