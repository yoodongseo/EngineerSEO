# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import datetime
import json
import logging
import os
import re

TN_PATTERN_FIRST_LOGIN = [b"([Uu]ser\\s?[Nn]ame|[Ll]ogin\\s?(as|[Nn]ame)?|[Pp]assword)\\s*:\\s*"]
TN_PATTERN_PASSWORD = [b"([Pp]assword|PASSCODE):\\s*|.*\xec\x95\x94\xed\x98\xb8:|[Pp]assword.*:\\s*"]
TN_PATTERN_PROMPT = [
    b"^[\\[<]?[\\w()@.~\\]_\\-\\s]*[\\$#?>]\\s?$",
    b"^[\\w()@._\\-\\s\\*]*\\.\\d{1,}\\s*#\\s*$",
]
TN_PATTERN_EN_PROMPT = [b"^[\\w()@._\\-\\s]*[\\$#?>]\\s?(\\(enable\\))?\\s*$"]
TN_PATTERN_MORE = [b"\\s*--(-)*\\s*[Mm][Oo][Rr][Ee]\\s*--", b"\\s*Press <SPACE> to continue\\s*"]

PATTERN_USERNAME = r"([Uu]ser\s?[Nn]ame|[Ll]ogin\s?(as|[Nn]ame)?)\s*:\s*$"
PATTERN_PASSWORD = r"([Pp]assword|PASSCODE):\s*|.*암호.*:\s*|[Pp]assword.*:\s*"
PATTERN_PROMPT = r"^[\[<]?[\w()@.~\]_\-\s]*[\$#?>]\s?$|%|^[^\n\r]*[\$#>] ?$|[\w\-\:\~\@\.\(\)/\\\[\] ]+[#\$>\]]\s?$"
PATTERN_PROMPT2 = r"([a-zA-Z0-9\-\_\.\@\(\)\<\>]+)([>#\]])\s*$"
PATTERN_EN_PROMPT = r"^[\w()@._\-\s]*[\$#?>]\s?(\(enable\))?\s*$"
PATTERN_APP_PROMPT = r"^[A-Za-z][A-Za-z0-9_\-().:/]*>\s*$"
PATTERN_MORE = r"\s*--(-)*\s*[Mm][Oo][Rr][Ee]\s*--"
PATTERN_MORE2 = r"\s*Press <SPACE> to continue\s*"
PATTERN_AUTH_FAIL = (
    r"Authentication failure|"
    r"unknown user|"
    r"denied|"
    r"PAM authentication error|"
    r"실패|"
    r"없음|"
    r"거부"
)


class EnablePromptError(Exception):
    pass


from enum import Enum


class SessionStatus(Enum):
    READY = 0
    CONNECTED = 1
    LOGINED = 2
    PROMPT = 3
    EN_PROMPT = 4
    EXECUTE_COMMANDS = 5
    DISCONNECTED = 9


def iniLogger(logger, module, moduleName, fap_vars):
    if isBlank(moduleName):
        moduleName = "UNKNOWN"

    currDate = datetime.datetime.now().strftime("%Y%m%d")
    host_ip = getDicValue(fap_vars, "host_ip", None)
    job_id = getDicValue(fap_vars, "job_id", None)
    log_file = None

    if host_ip and job_id:
        log_dir = f"/fap/logs/ansible/{currDate}"
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
        except Exception:
            pass
        log_file = f"{log_dir}/job_{job_id}_{host_ip}.log"

    logging.basicConfig(
        filename=log_file,
        datefmt="%Y-%m-%d %H:%M:%S",
        format=f"%(asctime)s %(levelname).5s [{moduleName}] %(message)s",
    )
    logger.setLevel(logging.DEBUG if module._verbosity > 0 else logging.INFO)


def get_valid_param(params, param_name, default, valid_type=None):
    if not params or param_name not in params:
        return default
    value = params.get(param_name)
    if valid_type:
        try:
            value = valid_type(value)
        except Exception:
            return default
    return default if value is None else value


def comparePromptString(device_prompt, line):
    if isBlank(device_prompt) or isBlank(line):
        return False
    device_prompt = decodeString(device_prompt).strip() if not isinstance(device_prompt, str) else device_prompt.strip()
    line = decodeString(line).strip() if not isinstance(line, str) else line.strip()
    if device_prompt == line:
        return True
    if len(line) >= 3 and (re.search(PATTERN_PROMPT, line) or re.search(PATTERN_PROMPT2, line)):
        cleaned_device_prompt = re.sub(r"[^A-Za-z0-9\s]", "", device_prompt)
        cleaned_line = re.sub(r"[^A-Za-z0-9\s]", "", line)
        return cleaned_device_prompt == cleaned_line
    return False


def cleanOutput(output):
    clean_text = []
    for char in output:
        if char == "\x08":
            if clean_text:
                clean_text.pop()
        else:
            clean_text.append(char)
    output = "".join(clean_text)
    ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", output)


def decodeString(data):
    for encoding in ("utf-8", "ascii", "unicode_escape"):
        try:
            if encoding == "utf-8":
                return data.decode(encoding, errors="ignore")
            return data.decode(encoding)
        except Exception:
            pass
    return str(data).replace("\r", "")


def checkDataType(data):
    if isinstance(data, str):
        try:
            return "json", json.loads(data)
        except Exception:
            pass
        try:
            return "dict", eval(data)
        except Exception:
            pass
    return type(data).__name__, data


def getDicValue(data, key, default=None):
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


def str2num(value, default=None, min_value=None, max_value=None):
    try:
        result = float(value)
        if min_value is not None and result < min_value:
            result = min_value
        if max_value is not None and result > max_value:
            result = max_value
        return int(result) if result.is_integer() else result
    except Exception:
        return default


def isBlank(value):
    return value is None or str(value).strip() == ""


def timestampMilliSec64():
    epoch = datetime.datetime(1970, 1, 1)
    return int((datetime.datetime.utcnow() - epoch).total_seconds() * 1000)
