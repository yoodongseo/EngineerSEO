#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: RTNET-Solution
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

DOCUMENTATION = """
---
module: exec_sop 
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
- Soyeon Jeong (sy.jeong@rtnet.co.kr)
short_description: A module to receive input from the user for values required to execute commands during playbook execution. 
description:
- This module is a module that receives input values from the user to use in executing commands during Playbook execution.
  You must declare the 'delegate_to = localhost' and 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
options:
  fap_vars:
    description:
    - Input FAP variables. {{ fap }}
    required: True
  ip:
    description:
    - Input target ip.
    required: True
  ssh_port:
    description:
    - Define the ssh port (default=22)
    required: false
    default: 22
  telnet_port:
    description:
    - Define the telnet port (default=23)
    required: false
    default: 23
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
  req_id:
    description:
    - Input SOP request ID
    required: True
"""

EXAMPLES = """
- fap.common.exec_sop:
    fap_vars: "{{ fap }}"
    ip: "{{ fap.host_ip | default('') }}"
    ssh_port: 22
    telnet_port: 23
    user_id: "{{ ansible_user | default('') }}"
    user_password: "{{ ansible_password | default('') }}"
    become_method: "{{ ansible_become_method | default('') }}"
    become_password: "{{ ansible_become_password | default('') }}"
    req_id: "{{ req_id }}"
  delegate_to: localhost
"""

RETURN = """
result:
  description: Result data
  type: dict
  returned: always
"""


from ansible.module_utils.basic import AnsibleModule

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP 
from ansible_collections.fap.common.plugins.module_utils.fap_client_sop import FapSopClient

import sys, os, datetime, json, logging, time, string, random
import datetime, os.path, configparser

from io import StringIO

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text

HAS_HTTPLIB2 = True
try:
  import httplib2
except:
  HAS_HTTPLIB2 = False

logger = logging.getLogger(__name__)

#==================================================
# MAIN
#==================================================
def main():
  
  # Module arguments
  module_args = dict(
    fap_vars=dict(type='dict', required=True),
    protocol=dict(type='str', choices=['ssh', 'telnet', 'auto'], required=False, default='ssh'),    # not use
    ssh_port=dict(type='int', required=False, default=22),
    telnet_port=dict(type='int', required=False, default=23),
    ip=dict(type='str', required=True),
    user_id=dict(type='str', required=False),
    user_password=dict(type='str', required=True, no_log=True),
    become_method=dict(type='str', required=False, default=None),
    become_password=dict(type='str', required=False, default=None, no_log=True),
    req_id=dict(type='str', required=True),
  )

  # AnsibleModule
  module = AnsibleModule(
    argument_spec= module_args,
    supports_check_mode=False,
  )

  # Initialize result data
  result = dict(changed=False)

  # FapSopClient
  client = None
  
  # Parameters
  fap_vars = module.params.get('fap_vars', None)
  ssh_port = module.params.get('ssh_port', None)
  telnet_port = module.params.get('telnet_port', None)
  ip = module.params.get('ip', None)
  user_id = module.params.get('user_id', None)
  user_password = module.params.get('user_password', None)
  become_method = module.params.get('become_method', None)
  become_password = module.params.get('become_password', None)
  req_id = module.params.get('req_id', None)
  
  try:
    # Check mandatory parameters
    if not fap_vars:
      raise ValueError("fap_vars must be define")
    if not ip:
      raise ValueError("ip must be define")
    if not user_password:
      raise ValueError("user_password must be define")
    
    # Initialze logger (/fap/logs/ansible/{yyyyMMdd}/~.log)
    #module._verbosity = 1 # Debug Level 
    FAP.iniLogger(logger, module, 'exec_sop', fap_vars)
    
    job_id = fap_vars.get('job_id', None)
    template_id = fap_vars.get('template_id',None)
    network_os = fap_vars.get('network_os', None)

    # Result default setting
    result['template_id'] = template_id
    result['job_id'] = job_id
    result['host_ip'] = ip
    result['req_id'] = req_id

    logger.info(f'-----------------------------------------------')
    logger.info(f'### Module started.')
    logger.info(f'- PARAMETERS.ip = {ip}')
    logger.info(f'- PARAMETERS.ssh_port = {ssh_port}')
    logger.info(f'- PARAMETERS.telnet_port = {telnet_port}')
    logger.info(f'- PARAMETERS.template_id = {template_id}')
    logger.info(f'- PARAMETERS.job_id = {job_id}')
    logger.info(f'- PARAMETERS.user_id = {user_id}')
    logger.info(f'- PARAMETERS.req_id = {req_id}')

    # Load config data
    iniPath = '/fap/ansible/conf/fap.conf'
    config = configparser.ConfigParser()
    config.read(iniPath)
    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    # Make Parameters
    params = {}
    params['client_type']='prompt'
    params['ip'] = ip
    params['ssh_port'] = ssh_port
    params['telnet_port'] = telnet_port
    params['job_id'] = job_id 
    params['site_code'] = fap_vars.get('site_code', None)
    params['template_id'] = template_id
    params['user_id'] = user_id
    params['network_os'] = network_os
    params['user_password'] = user_password
    params['become_method'] = become_method
    params['become_password'] = become_password
    # API data
    params['apiData'] = {}
    params['apiData']['url'] = api_url
    params['apiData']['token'] = api_token
    params['apiData']['failed'] = 0
    # Base Data
    params['baseData'] = {}
    params['baseData']['template_id'] = template_id
    params['baseData']['job_id'] = job_id
    params['baseData']['req_id'] = req_id
    params['baseData']['host_ip'] = ip

    time.sleep(3)
    
    # Execute SOP
    client = FapSopClient(module, logger, params)

    # Update Host (W=Wait)
    client.execApiUpdateHost('W', None)

    # Execute SOP
    client.executeSop()
    
    # Create result data
    result['changed'] = (client.cmd_exec_count > 0)
    result['cmd_exec_count'] = client.cmd_exec_count
    result['is_connected'] = client.isConnected()
    result['status'] = 'T'

  except Exception as err:
    logger.exception(err)
    # Update Host (F=Failed)
    client.execApiUpdateHost('F', f'Error Occured. msg=({str(err)})')
    # Return module fail
    module.fail_json(msg="Module failed: {0}".format(str(err)), exception=str(err))
  finally:
    if client is not None:
      # Update Host (T=Terminate)
      client.execApiUpdateHost('T', None)
      client.close()
      client = None

  # Module terminate
  logger.info(f'')
  logger.info(f'* RESULT = {str(result)}')
  logger.info(f'### Module terminated.')

  # Exit module
  module.exit_json(**result)

#==================================================
if __name__ == "__main__":
  main()

