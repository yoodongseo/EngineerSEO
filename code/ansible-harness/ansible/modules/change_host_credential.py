#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original version : 20 Dec 2023
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
module: change_host_credential
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for send email
description:
- This module is for changing host credential info.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  host_ip:
    description:
    - Input host ip.
    required: true
  password:
    description:
    - Input credential password data.
    required: false
  en_password:
    description:
    - (TELNET, NETWORK_DEVICE) Input credential en_password.
    required: false
  become_user:
    description:
    - (SSH) Input credential become user.
    required: false
  become_password:
    description:
    - (SSH) Input credential become password.
    required: false
"""

EXAMPLES = """
- fap.common.change_host_credential:
    host_ip: "{{ inventory_hostname }}"
    password: "NEW_PASSWORD"
  delegate_to: localhost

- fap.common.change_host_credential:
    host_ip: "{{ inventory_hostname }}"
    password: "NEW_PASSWORD"
    become_user: "NEW_BECOME_USER"
    become_password: "NEW_BECOME_PASSWORD"
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

from cryptography.fernet import Fernet

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_native
from ansible.module_utils._text import to_text
#from ansible.module_utils.urls import fetch_url

HAS_HTTPLIB2 = True
try:
    import httplib2
except:
    HAS_HTTPLIB2 = False

def main():

    iniPath = '/fap/ansible/conf/fap.conf'

    # Module arguments
    module_args = dict(
        host_ip=dict(type='str', required=True),
        password=dict(type='str', required=False, no_log=True),
        en_password=dict(type='str', required=False, no_log=True),
        become_user=dict(type='str', required=False),
        become_password=dict(type='str', required=False, no_log=True),
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
    host_ip = module.params['host_ip']
    password = module.params['password']
    en_password = module.params['en_password']
    become_user = module.params['become_user']
    become_password = module.params['become_password']

    # Check input parameters
    if not host_ip: module.fail_json(msg='host_ip must be define')
    
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
    resultData['host_ip'] = host_ip
    resultData['password'] = password
    resultData['en_password'] = en_password
    resultData['become_user'] = become_user
    resultData['become_password'] = become_password

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/change_host_credential'

    try :
        # Http
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        
        # Make header
        headers = {'Cache-Control':'no-cache', 'x-auth-token':'Bearer '+api_token}

        # Send request
        resp, content = http.request(uri=url, method='POST', headers=headers, body=json.dumps(resultData))

        # OK=200, CREATED=201, ACCEPTED=202
        if resp.status == 200 or resp.status == 201 or resp.status == 202:
            module.exit_json(**result)
        else:
            module.fail_json(msg='Failed to change host credential. (status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to change host credential (url=' + url + ')')

if __name__ == "__main__":
    main()
