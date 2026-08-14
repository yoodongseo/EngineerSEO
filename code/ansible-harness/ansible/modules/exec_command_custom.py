#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2024 www.rtnet.co.kr
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "0.10.1",
    "status": ["stableinterface"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: exec_command
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for execute commands in ssh and telnet access environments. 
description:
- This module is intended to execute commands in ssh and telnet access environments.
  You must declare the 'delegate_to = localhost' and 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
options:
  fap_vars:
    description:
    - Input FAP variables. {{ fap }}
    required: True
  protocol:
    description:
    - Define the connection protocol
    choices: ['ssh', 'telnet', 'auto']
    required: false
    default: 'ssh'
  ip:
    description:
    - Input target ip.
    required: True
  command:
    description:
    - Input command list.
    required: True
  user_id:
    description:
    - Input user id
    required: False
  user_password:
    description:
    - Input user password
    required: True
  become_method:
    description:
    - Input become method (su, enable, super, ...)
    required: False
  become_password:
    description:
    - Input become password
    required: False
  network_os:
    description:
    - Input network os type (cisco_ios, cisco_nxos, extreme_exos, arista_eos, ...)
    required: False
  result_type:
    description:
    - Define the result type
    choices: ['cli_data', 'list', 'dict']
    required: false
    default: 'cli_data'
"""

EXAMPLES = """
- fap.common.exec_command:
    fap_vars: "{{ fap }}"
    protocol: ssh
    ip: "{{ ansible_hostname }}"
    command: ["terminal length 0", "*show version"]
    result_type: cli_data
    user_id: "{{ ansible_user | default('') }}"
    user_password: "{{ ansible_password | default('') }}"
    become_method: "{{ ansible_become_method | default('') }}"
    become_password: "{{ ansible_become_password | default('') }}"
    network_os: "cisco_ios"
  delegate_to: localhost
"""

RETURN = """
result:
  description: Result data
  type: dict
  returned: always
"""


from ansible.module_utils.basic import AnsibleModule

import ansible_collections.fap.common.plugins.module_utils.fap_common_custom as FAP
from ansible_collections.fap.common.plugins.module_utils.fap_client_ssh_custom import (
    FapSshClient,
)
from ansible_collections.fap.common.plugins.module_utils.fap_client_telnet_custom import (
    FapTelnetClient,
)


import sys, os, datetime, json, logging

from io import StringIO

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text

logger = logging.getLogger(__name__)


def main():

    # Module arguments
    module_args = dict(
        fap_vars=dict(type="dict", required=True),
        protocol=dict(
            type="str", choices=["ssh", "telnet", "auto"], required=False, default="ssh"
        ),
        ip=dict(type="str", required=True),
        ssh_port=dict(type="int", required=False, default=22),
        ssh_key_file=dict(type="str", required=False, default="/home/fap/.ssh/id_rsa"),
        ssh_params=dict(type="dict", required=False, default=dict(
            width=1000, height=1000, term="dumb")
        ),
        command=dict(type="raw", required=True),
        user_id=dict(type="str", required=False),
        user_password=dict(type="str", required=True, no_log=True),
        become_user=dict(type="str", required=False, default=None),
        become_method=dict(type="str", required=False, default=None),
        become_password=dict(type="str", required=False, default=None, no_log=True),
        network_os=dict(type="str", required=False, default=None),
        result_type=dict(
            type="str",
            choices=["cli_data", "list", "dict"],
            required=False,
            default="cli_data",
        ),
    )

    # AnsibleModule
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False,
    )

    # Init result data
    result = dict(changed=False)

    client = None  # FapSshClient, FapTelnetClient
    output = None
    result_data = None

    # Parameters
    fap_vars = module.params.get("fap_vars", None)
    ip = module.params.get("ip", None)
    protocol = module.params.get("protocol", None)
    ssh_port = module.params.get("ssh_port", 22)
    ssh_key_file = module.params.get("ssh_key_file", "/home/fap/.ssh/id_rsa")
    command = module.params.get("command", None)
    user_id = module.params.get("user_id", None)
    user_password = module.params.get("user_password", None)
    become_user = module.params.get("become_user", None)
    become_method = module.params.get("become_method", None)
    become_password = module.params.get("become_password", None)
    network_os = module.params.get("network_os", None)
    result_type = module.params.get("result_type", None)
    ssh_params = module.params.get("ssh_params", None)

    try:

        # Check mandatory parameters
        if not fap_vars:
            raise ValueError("fap_vars must be define")
        if not ip:
            raise ValueError("ip must be define")
        if not protocol:
            raise ValueError("protocol must be define")
        if not command:
            raise ValueError("command must be define")
        if not user_password:
            raise ValueError("user_password must be define")

        # Initialze logger (/fap/logs/ansible/{yyyyMMdd}/~.log)
        FAP.iniLogger(logger, module, "exec_command", fap_vars)

        # network_os
        if network_os is None:
            network_os = fap_vars.get("network_os", None)

        # Make execution parameters
        params = {}
        params["ip"] = ip
        params["ssh_port"] = ssh_port
        params["ssh_key_file"] = ssh_key_file
        params["site_code"] = fap_vars.get("site_code", None)
        params["user_id"] = user_id
        params["user_password"] = user_password
        params["become_user"] = become_user
        params["become_method"] = become_method
        params["become_password"] = become_password
        params["result_type"] = result_type
        params["network_os"] = network_os
        params["job_id"] = fap_vars.get("job_id", None)
        params["ssh_params"] = ssh_params

        logger.info(f"-----------------------------------------------")
        logger.info(f"### Module started.")
        logger.info(f"- PARAMTERS.ip = {ip}")
        logger.info(f"- PARAMTERS.ssh_port = {ssh_port}")
        logger.info(f"- PARAMTERS.ssh_key_file = {ssh_key_file}")
        logger.info(f"- PARAMTERS.protocol = {protocol}")
        logger.info(f"- PARAMTERS.result_type = {result_type}")
        logger.info(f"- PARAMTERS.network_os = {network_os}")
        logger.info(f"- PARAMTERS.become_method = {become_method}")
        logger.info(f"- PARAMTERS.become_user = {become_user}")
        logger.info(f"- PARAMTERS.ssh_params = {ssh_params}")
        logger.info(f"")

        connected = False

        # 1. SSH
        if protocol == "ssh":
            client = FapSshClient(module, logger, params, command)
            if client.connect():
                connected = True
            else:
                client.close()
                client = None
        # 2. Telnet
        elif protocol == "telnet":
            client = FapTelnetClient(module, logger, params, command)
            if client.connect():
                connected = True
            else:
                client.close()
                client = None
        # 3. Auto (ssh, telnet)
        elif protocol == "auto":
            # 1. ssh
            protocol = "ssh"
            try:
                client = FapSshClient(module, logger, params, command)
                if client.connect():
                    connected = True
            except FAP.EnablePromptError as err:
                if client is not None:
                    client.close()
                raise err
            except Exception as err:
                None

            # 2. telnet
            if connected == False:
                if client is not None:
                    client.close()

                protocol = "telnet"
                client = FapTelnetClient(module, logger, params, command)
                if client.connect():
                    connected = True
                else:
                    client.close()
                    client = None

        else:
            raise ValueError("Unknown protocol")

        if client is None:
            raise ValueError("Failed to connect")

        # Execute commands
        result_data = client.execute()

    except Exception as err:
        logger.exception(err)
        module.fail_json(msg="Module failed: {0}".format(str(err)), exception=str(err))
    finally:
        if client != None:
            client.close()
            client = None

    # Create result data
    result["changed"] = True
    result["protocol"] = protocol

    if not FAP.isBlank(network_os):
        result["network_os"] = network_os

    result["connected"] = connected
    result["host_id"] = fap_vars.get("host_id", None)
    result["job_id"] = fap_vars.get("job_id", None)
    result["template_id"] = fap_vars.get("template_id", None)

    # result data
    if result_data is not None:
        result["result"] = result_data
    else:
        module.fail_json(msg="Failed to execute command", **result)

    logger.info(f"")
    logger.info(f"* RESULT = {str(result)}")
    logger.info(f"### Module terminated.")

    # return
    module.exit_json(**result)


if __name__ == "__main__":
    main()
