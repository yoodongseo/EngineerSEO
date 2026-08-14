#!/usr/bin/python
# -*- coding: utf-8 -*-

# Original version : 25 May 2023
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

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP

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
module: make_report
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for make report
description:
- This module is for make report.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  fap_vars:
    description:
    - Input FAP variables. {{ fap | default(omit) }}
    required: True
  noti_name:
    description:
    - Input the notification name registered on the FAP system.
    required: false
  mail_subject:
    description:
    - Enter the subject of mail.
    required: false
  form_filename:
    description:
    - Input the name of the form file in the FAP system. (form-path=/fap/forms).
    required: false
  content:
    description:
    - Input the mail content.
    required: false
  content_type:
    description:
    - Enter the type of mail contents. (TEXT, HTML)
    choices: ['TEXT', 'HTML']
    required: false
    default: 'TEXT'
  recipients:
    description:
    - Enter the mailing list of mail recipients.
    required: false
  cc_list:
    description:
    - Enter the mailing list of mail CC recipients.
    required: false
  bcc_list:
    description:
    - Enter the mailing list of mail BCC recipients.
    required: false
"""

EXAMPLES = """
- fap.common.make_report:
    fap_vars: "{{ fap }}"
  delegate_to: localhost

- fap.common.make_report:
    fap_vars: "{{ fap }}"
    noti_name: "NOTIFICATION_NAME"
    mail_subject: "Mail subject"
    form_filename: "form_job_result"
    recipients: "test1@rtnet.co.kr|test2@rtnet.co.kr"
    cc_list: "lab1@rtnet.co.kr"
    bcc_list: "lab2@rtnet.co.kr"
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

HAS_HTTPLIB2 = True
try:
    import httplib2
except:
    HAS_HTTPLIB2 = False

def timestampMillisec64():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

def main():

    iniPath = '/fap/ansible/conf/fap.conf'

    # Module arguments
    module_args = dict(
        fap_vars=dict(type='dict', required=True),
        noti_name=dict(type='str', required=False),
        mail_subject=dict(type='str', required=False),
        form_filename=dict(type='str', required=False, default='form_job_result'),
        content=dict(type='str', required=False),
        content_type=dict(type='str', required=False, choices=['TEXT', 'HTML'], default='TEXT'),
        recipients=dict(type='str', required=False),
        cc_list=dict(type='str', required=False),
        bcc_list=dict(type='str', required=False),
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
    fap_vars = module.params.get('fap_vars', None)
    noti_name = module.params.get('noti_name', None)
    mail_subject = module.params.get('mail_subject', None)
    form_filename = module.params.get('form_filename', None)
    content = module.params.get('content', None)
    content_type = module.params.get('content_type', None)
    recipients = module.params.get('recipients', None)
    cc_list = module.params.get('cc_list', None)
    bcc_list = module.params.get('bcc_list', None)
  
    # Check required parameters
    if not fap_vars: module.fail_json(msg='fap_vars must be define')
    
    # Extract job info
    if fap_vars:
        job_id = FAP.getDicValue(fap_vars, 'job_id', None)
        template_id = FAP.getDicValue(fap_vars, 'template_id', None)
    
    # Check the config file exists.
    if os.path.isfile(iniPath) == False:
        module.fail_json(msg='Not found config file. (' + iniPath + ')')

    # Config parser
    config = configparser.ConfigParser()
    config.read(iniPath)

    # Make result data
    result = dict(changed=False, msg='')

    # Check mode
    if module.check_mode:
        module.exit_json(**result)

    # Make data structure
    resultData = {}
    resultData['job_id'] = job_id
    resultData['template_id'] = template_id
    resultData['noti_name'] = noti_name
    resultData['mail_subject'] = mail_subject
    resultData['form_filename'] = form_filename
    resultData['content'] = content
    resultData['content_type'] = content_type
    resultData['recipients'] = recipients
    resultData['cc_list'] = cc_list
    resultData['bcc_list'] = bcc_list
    resultData['insert_time'] = timestampMillisec64()

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/make_report'

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
            module.fail_json(msg='Failed to make report. (status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to make report. (url=' + url + ')')

if __name__ == "__main__":
    main()
