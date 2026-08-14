#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original version : 29 Jan 2024
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
module: get_credential
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for get credential information
description:
- This module is for get credential information.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  credential_name:
    description:
    - Input credential name.
    required: true
  host_ip:
    description:
    - Input host IPAddress.
    required: false
  host_name:
    description:
    - Input host name.
    required: false
"""

EXAMPLES = """
- fap.common.get_credential:
    credential_name: "cr_name_01"
    host_ip: "{{ fap.host_ip | default(omit) }}"
    host_name: "{{ fap.host_name | default(omit) }}"
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
        credential_name=dict(type='str', required=True),
        host_ip=dict(type='str', required=False),
        host_name=dict(type='str', required=False),
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
    credential_name = module.params['credential_name']
    host_ip = module.params['host_ip']
    host_name = module.params['host_name']

    # Check input parameters
    if not credential_name: module.fail_json(msg='credential_name must be define')
    
    # Check the config file exists.
    if os.path.isfile(iniPath) == False:
        module.fail_json(msg='Not found config file. (' + iniPath + ')')

    # Config parser
    config = configparser.ConfigParser()
    config.read(iniPath)

    # Make data structure
    sendData = {}
    sendData['credential_name'] = credential_name
    sendData['host_ip'] = host_ip
    sendData['host_name'] = host_name

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/get_credential'

    try :
        # Http
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        
        # Make header
        headers = {'Cache-Control':'no-cache', 'x-auth-token':'Bearer '+api_token}

        # Send request
        resp, content = http.request(uri=url, method='POST', headers=headers, body=json.dumps(sendData))

        # OK=200, CREATED=201, ACCEPTED=202
        if resp.status == 200 or resp.status == 201 or resp.status == 202:

            # json to dictionary
            result = json.loads(content)

            # check result data
            if result is not None and result['data'] is not None:
                module.exit_json(changed=False, data=result['data'])
            else:
                module.fail_json(msg='Not found credential information.')
        else:
            module.fail_json(msg='Failed to get credential information. (status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to get credential information. (url=' + url + ')')

if __name__ == "__main__":
    main()
