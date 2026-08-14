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
module: send_data
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for send data to external system
description:
- This module is intended to transfer data from the FAP system to the external system.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  service_uri:
    description:
    - External service URI to receive data
    required: True
  method:
    description:
    - Http method
    choices: ['POST', 'PUT']
    required: True
  auth_header:
    description:
    - Authorization header field (ex. Authorization, x-auth-token, ...)
    required: False
  auth_value:
    description:
    - Authorization header value (ex. JWT-token, ...)
    required: False
  host_name:
    description:
    - Input host name.
    required: True
  content:
    description:
    - Input data of ditionary type.
    required: True
  template_id:
    description:
    - Enter the Template ID defined in the FAP variable. {{ fap.template_id | default(omit) }}
    required: False
  job_id:
    description:
    - Enter the Job ID defined in the FAP variable. {{ fap.job_id | default(omit) }}
    required: False
"""

EXAMPLES = """
- fap.common.send_data:
    service_uri: http://1.1.1.1/recv_data
    method: POST
    host_name: "{{ inventory_hostname }}"
    content: "{{ input_data }}"
  delegate_to: localhost
  
- fap.common.send_data:
    service_uri: http://10.10.10.10/recv_data
    method: POST
    auth_header: x-auth-token
    auth_value: Bearer {access-token}
    host_name: "{{ inventory_hostname }}"
    content: "{{ input_data }}"
    template_id: "{{ fap.template_id | default(omit) }}"
    job_id: "{{ fap.job_id | default(omit) }}"
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

    # Module arguments
    module_args = dict(
        service_uri=dict(type='str', required=True),
        method=dict(type='str', choices=['POST', 'PUT'], required=True),
        auth_header=dict(type='str', required=False),
        auth_value=dict(type='str', required=False),
        host_name=dict(type='str', required=True),
        content=dict(type='dict', required=True),
        template_id=dict(type='int', required=False),
        job_id=dict(type='int', required=False),
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
    service_uri = module.params['service_uri']
    method = module.params['method']
    auth_header = module.params['auth_header']
    auth_value = module.params['auth_value']
    host_name = module.params['host_name']
    content = module.params['content']
    template_id = module.params['template_id']
    job_id = module.params['job_id']

    # Check input parameters
    if not service_uri:
        module.fail_json(msg='service_uri must be define')
    if not method:
        module.fail_json(msg='method must be define')
    if not host_name:
        module.fail_json(msg='host_name must be define')
    
    if auth_header:
        if not auth_value:
            module.fail_json(msg='auth_value must be defined when auth_header is defined.')
    
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
    resultData['content'] = content
    
    if template_id:
        resultData['template_id'] = template_id

    if job_id:
        resultData['job_id'] = job_id

    try :
        # Http
        http = httplib2.Http(disable_ssl_certificate_validation=True)
        
        if auth_header and auth_value:
            # Make header
            headers = {auth_header : auth_value}
            # Send request with auth header
            resp, content = http.request(uri=service_uri, method=method, headers=headers, body=json.dumps(resultData))
        else:
            # Send request
            resp, content = http.request(uri=service_uri, method=method, body=json.dumps(resultData))

        # OK=200, CREATED=201, ACCEPTED=202
        if resp.status == 200 or resp.status == 201 or resp.status == 202:
            module.exit_json(**result)
        else:
            module.fail_json(msg='Failed to send data. (status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to send data. (service_uri='+service_uri+', method='+method+') ' + e.message)

if __name__ == "__main__":
    main()
