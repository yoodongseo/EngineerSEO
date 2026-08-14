#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original version : 23 Oct 2022
# Copyright 2019 www.rtnet.co.kr
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

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

ANSIBLE_METADATA = {
    "metadata_version": "0.9.1",
    "status": ["stableinterface"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: add_host
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for add host into FAP system
description:
- This module is for add host into the FAP system.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  host_name:
    description:
    - Input host name.
    required: True
  host_ip:
    description:
    - Input host IP.
    required: True
  host_vars:
    description:
    - Input host_vars (JSON).
    required: false
  credential_type:
    description:
    - Define the credential type
    choices: ['TELNET', 'SSH', 'NETWORK_DEVICE', 'WINRM']
    required: false
  username:
    description:
    - Input credential username data.
    required: false
  password:
    description:
    - Input credential password data.
    required: false
  en_password:
    description:
    - (TELNET, NETWORK_DEVICE) Input credential en_password.
    required: false
  network_os:
    description:
    - (NETWORK_DEVICE) Input network_os data.
    required: false
  become:
    description:
    - (SSH) Input become enable.
    type: bool
    default: false
    required: false
  become_method:
    description:
    - (SSH) Input become method command. (ex. enable, su, ...)
    required: false
  become_user:
    description:
    - (SSH) Input credential become user.
    required: false
  become_password:
    description:
    - (SSH) Input credential become password.
    required: false
  cert_validation:
    description:
    - (WINRM) Input cert_validation.
    choices: ['ignore', 'validate']
    default: 'ignore'
    required: false
"""

EXAMPLES = """
- fap.common.add_host:
    host_name: "{{ host_name }}"
    host_ip: "{{ host_ip }}"
  delegate_to: localhost
  
- fap.common.add_host:
    host_name: "{{ host_name }}"
    host_ip: "{{ host_ip }}"
    credential_type: "TELNET"
    username: "{{ username }}"
    password: "{{ password }}"
  delegate_to: localhost

- fap.common.add_host:
    host_name: "{{ host_name }}"
    host_ip: "{{ host_ip }}"
    host_vars: "{ ansible_ssh_port: 3838 }"
    credential_type: "SSH"
    username: "{{ username }}"
    password: "{{ password }}"
    become: true
    become_method: "{{ become_method }}"
    become_user: "{{ become_user }}"
    become_password: "{{ become_password }}"
  delegate_to: localhost

- fap.common.add_host:
    host_name: "{{ host_name }}"
    host_ip: "{{ host_ip }}"
    credential_type: "NETWORK_DEVICE"
    network_os: "{{ network_os }}"
    username: "{{ username }}"
    password: "{{ password }}"
    en_password: "{{ en_password }}"
  delegate_to: localhost

- fap.common.add_host:
    host_name: "{{ host_name }}"
    host_ip: "{{ host_ip }}"
    credential_type: "WINRM"
    username: "{{ username }}"
    password: "{{ password }}"
  delegate_to: localhost
"""

RETURN = """
result:
  description: Result message.
  returned: success
  type: dict
"""

import datetime
import os.path
import json
import base64
import configparser

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text
#from ansible.module_utils.urls import fetch_url

HAS_HTTPLIB2 = True
try:
    import httplib2
except:
    HAS_HTTPLIB2 = False

#def timestampMillisec64():
#    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

def main():

    iniPath = '/fap/ansible/conf/fap.conf'

    # Module arguments
    module_args = dict(
        host_name=dict(type='str', required=True),
        host_ip=dict(type='str', required=True),
        host_vars=dict(type='dict', required=False),
        credential_type=dict(type='str', choices=['TELNET', 'SSH', 'NETWORK_DEVICE', 'WINRM'], required=False),
        username=dict(type='str', required=False),
        password=dict(type='str', required=False, no_log=True),
        en_password=dict(type='str', required=False, no_log=True),
        network_os=dict(type='str', required=False),
        become=dict(type='bool', required=False, default=False),
        become_method=dict(type='str', required=False),
        become_user=dict(type='str', required=False),
        become_password=dict(type='str', required=False, no_log=True),
        cert_validation=dict(type='str', choices=['ignore', 'validate'], required=False, default='ignore'),
    )

    # AnsibleModule
    module = AnsibleModule(
        argument_spec= module_args,
        supports_check_mode=False,
        #required_one_of=[['content', 'offline_file']],
        #mutually_exclusive=(['content', 'offline_file']),
    )

    # Check library
    if not HAS_HTTPLIB2:
        module.fail_json(msg='This module requires httplib2.')

    # Parameters
    host_name = module.params['host_name']
    host_ip = module.params['host_ip']
    host_vars = module.params['host_vars']
    credential_type = module.params['credential_type']
    username = module.params['username']
    password = module.params['password']
    en_password = module.params['en_password']
    network_os = module.params['network_os']
    become = module.params['become']
    become_method = module.params['become_method']
    become_user = module.params['become_user']
    become_password = module.params['become_password']
    cert_validation = module.params['cert_validation']


    # Check input parameters
    if not host_name:
        module.fail_json(msg='host_name must be define')
    if not host_ip:
        module.fail_json(msg='host_ip must be define')
    
    if credential_type:
        if not username:
            module.fail_json(msg='username must be defined when entering crenential data.')
        if not password:
            module.fail_json(msg='password must be defined when entering crenential data.')
        
        if credential_type == 'NETWORK_DEVICE':
            if not network_os:
                module.fail_json(msg='network_os must be defined when entering NETWORK_DEVICE crenential data.')
    
    # Check the config file exists.
    if os.path.isfile(iniPath) == False:
        module.fail_json(msg='Not found config file. (' + iniPath + ')')

    # Config parser
    config = configparser.ConfigParser()
    config.read(iniPath)

    # Make result data
    result = dict(
        changed=False,
        msg=''
    )

    # Check mode
    if module.check_mode:
        module.exit_json(**result)

    # Make data structure
    resultData = {}
    resultData['host_name'] = host_name
    resultData['host_ip'] = host_ip
    resultData['credential_type'] = credential_type
    resultData['username'] = username
    resultData['password'] = password
    resultData['en_password'] = en_password
    resultData['network_os'] = network_os
    resultData['become'] = become
    resultData['become_method'] = become_method
    resultData['become_user'] = become_user
    resultData['become_password'] = become_password
    resultData['cert_validation'] = cert_validation

    if host_vars:
      resultData['host_vars'] = json.dumps(host_vars)

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/add_host'

    try :
        # Http
        http = httplib2.Http(disable_ssl_certificate_validation=True)

        # Make header
        headers = {'Cache-Control':'no-cache', 'x-auth-token':'Bearer '+api_token}

        # Send request
        resp, content = http.request(uri=url, method='PUT', headers=headers, body=json.dumps(resultData))

        # OK=200, CREATED=201, ACCEPTED=202
        if resp.status == 200 or resp.status == 201 or resp.status == 202:
            module.exit_json(**result)
        else:
            module.fail_json(msg='Failed to add host. (protocol=http, status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to add host. (protocol=http, url=' + url + ')')

if __name__ == "__main__":
    main()
