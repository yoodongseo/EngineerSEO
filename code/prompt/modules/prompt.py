#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

__metaclass__ = type

ANSIBLE_METADATA = {
    "metadata_version": "0.10.1",
    "status": ["stableinterface"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: prompt
short_description: Execute commands with learned prompt detection.
description:
- Execute commands over SSH or telnet.
- Command completion is detected by learning the device prompt and waiting for that prompt to return.
"""

import logging

from ansible.module_utils.basic import AnsibleModule

import ansible_collections.fap.custom.plugins.module_utils.fap_common_prompt as FAP
from ansible_collections.fap.custom.plugins.module_utils.fap_client_ssh_prompt import FapSshPromptClient
from ansible_collections.fap.custom.plugins.module_utils.fap_client_telnet_prompt import FapTelnetPromptClient

logger = logging.getLogger(__name__)


def normalize_target_type(value):
    normalized = str(value or "mixed").strip().lower()
    if normalized not in ["mixed", "pwonly"]:
        return "mixed"
    return normalized


def main():
    module_args = dict(
        fap_vars=dict(type="dict", required=True),
        protocol=dict(type="str", choices=["ssh", "telnet", "auto"], required=False, default="ssh"),
        ip=dict(type="str", required=True),
        ssh_port=dict(type="int", required=False, default=22),
        telnet_port=dict(type="int", required=False, default=23),
        ssh_params=dict(type="dict", required=False, default=dict()),
        command=dict(type="raw", required=True),
        target_type=dict(type="str", required=False, default="mixed"),
        user_id=dict(type="str", required=False),
        user_password=dict(type="str", required=True, no_log=True),
        become_user=dict(type="str", required=False, default=None),
        become_method=dict(type="str", required=False, default=None),
        become_password=dict(type="str", required=False, default=None, no_log=True),
        result_type=dict(type="str", choices=["cli_data", "list", "dict"], required=False, default="cli_data"),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)
    result = dict(changed=False)
    client = None
    result_data = None
    connected = False
    ssh_error = None
    telnet_error = None

    fap_vars = module.params.get("fap_vars")
    ip = module.params.get("ip")
    protocol = module.params.get("protocol")
    ssh_port = module.params.get("ssh_port")
    telnet_port = module.params.get("telnet_port")
    ssh_params = module.params.get("ssh_params")
    command = module.params.get("command")
    target_type = normalize_target_type(module.params.get("target_type"))
    user_id = module.params.get("user_id")
    user_password = module.params.get("user_password")
    become_user = module.params.get("become_user")
    become_method = module.params.get("become_method")
    become_password = module.params.get("become_password")
    result_type = module.params.get("result_type")

    try:
        if not fap_vars:
            raise ValueError("fap_vars must be define")
        if not ip:
            raise ValueError("ip must be define")
        if not protocol:
            raise ValueError("protocol must be define")
        if not command:
            raise ValueError("command must be define")
        if not user_id:
            raise ValueError("user_id must be define")
        if not user_password:
            raise ValueError("user_password must be define")

        FAP.iniLogger(logger, module, "prompt", fap_vars)

        params = {
            "ip": ip,
            "ssh_port": ssh_port,
            "telnet_port": telnet_port,
            "site_code": fap_vars.get("site_code"),
            "target_type": target_type,
            "user_id": user_id,
            "user_password": user_password,
            "become_user": become_user,
            "become_method": become_method,
            "become_password": become_password,
            "result_type": result_type,
            "job_id": fap_vars.get("job_id"),
            "ssh_params": ssh_params,
        }

        if protocol == "ssh":
            client = FapSshPromptClient(module, logger, params, command)
            connected = bool(client.connect())
        elif protocol == "telnet":
            client = FapTelnetPromptClient(module, logger, params, command)
            connected = bool(client.connect())
        elif protocol == "auto":
            protocol = "ssh"
            try:
                client = FapSshPromptClient(module, logger, params, command)
                connected = bool(client.connect())
            except FAP.EnablePromptError:
                if client is not None:
                    client.close()
                raise
            except Exception as err:
                ssh_error = err
                logger.warning(f"SSH connect failed during auto mode: {err}")
                connected = False

            if not connected:
                if client is not None:
                    client.close()
                protocol = "telnet"
                try:
                    client = FapTelnetPromptClient(module, logger, params, command)
                    connected = bool(client.connect())
                except Exception as err:
                    telnet_error = err
                    logger.warning(f"Telnet connect failed during auto mode: {err}")
                    connected = False
        else:
            raise ValueError("Unknown protocol")

        if client is None or not connected:
            if ssh_error is not None or telnet_error is not None:
                raise ValueError(
                    "Failed to connect"
                    + (f" | ssh_error={ssh_error}" if ssh_error is not None else "")
                    + (f" | telnet_error={telnet_error}" if telnet_error is not None else "")
                )
            raise ValueError("Failed to connect")

        result_data = client.execute()
    except Exception as err:
        logger.exception(err)
        module.fail_json(msg="Module failed: {0}".format(str(err)), exception=str(err))
    finally:
        if client is not None:
            client.close()

    result["changed"] = True
    result["protocol"] = protocol
    result["connected"] = connected
    result["host_id"] = fap_vars.get("host_id")
    result["job_id"] = fap_vars.get("job_id")
    result["template_id"] = fap_vars.get("template_id")

    if result_data is not None:
        result["result"] = result_data
    else:
        module.fail_json(msg="Failed to execute command", **result)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
