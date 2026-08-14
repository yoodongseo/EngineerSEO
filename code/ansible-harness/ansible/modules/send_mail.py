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
module: send_mail
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for send email
description:
- This module is for send email.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  noti_name:
    description:
    - Input the notification name registered on the FAP system.
    required: true
  subject:
    description:
    - Enter the subject of mail.
    required: true
  contents:
    description:
    - Enter the contents of mail. Content can be written in TEXT or HTML format according to content_type.
    required: true
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
  attached_files:
    description:
    - Enter the file path for the attachment.
    required: false
  template_id:
    description:
    - Enter the template ID defined on the FAP variables. {{ fap.template_id }}
    required: false
  job_id:
    description:
    - Enter the job ID defined on the FAP variables. {{ fap.job_id }}
    required: false
"""

EXAMPLES = """
- fap.common.send_mail:
    noti_name: "test_google_mail"
    subject: "Mail subject"
    contents: "Mail contents...."
    content_type: "TEXT"
    recipients: "abc@rtnet.co.kr"
    template_id: "{{ fap.template_id | default(omit) }}"
    job_id: "{{ fap.job_id | default(omit) }}"
  delegate_to: localhost

- fap.common.send_mail:
    noti_name: "test_knox_mail"
    subject: "Mail subject"
    contents: "Mail contents...."
    content_type: "TEXT"
    recipients: "test1@rtnet.co.kr|test2@rtnet.co.kr"
    cc_list: "lab@rtnet.co.kr"
    attached_files: "/data/file.log|/data/report.csv"
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

def timestampMillisec64():
    return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

def main():

    iniPath = '/fap/ansible/conf/fap.conf'

    # Module arguments
    module_args = dict(
        noti_name=dict(type='str', required=True),
        subject=dict(type='str', required=True),
        contents=dict(type='str', required=True),
        content_type=dict(type='str', required=True, choices=['TEXT', 'HTML']),
        recipients=dict(type='str', required=False),
        cc_list=dict(type='str', required=False),
        bcc_list=dict(type='str', required=False),
        attached_files=dict(type='str', required=False),
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
    noti_name = module.params['noti_name']
    subject = module.params['subject']
    contents = module.params['contents']
    content_type = module.params['content_type']
    recipients = module.params['recipients']
    cc_list = module.params['cc_list']
    bcc_list = module.params['bcc_list']
    attached_files = module.params['attached_files']
    template_id = module.params['template_id']
    job_id = module.params['job_id']

    # Check input parameters
    if not noti_name: module.fail_json(msg='noti_name must be define')
    if not subject: module.fail_json(msg='subject is empty')
    if not contents: module.fail_json(msg='contents is empty')
    if not content_type: module.fail_json(msg='content_type is empty')
    
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
    resultData['noti_name'] = noti_name
    resultData['subject'] = subject
    resultData['contents'] = contents
    resultData['content_type'] = content_type
    resultData['recipients'] = recipients
    resultData['cc_list'] = cc_list
    resultData['bcc_list'] = bcc_list
    resultData['attached_files'] = attached_files
    resultData['template_id'] = template_id
    resultData['job_id'] = job_id
    resultData['insert_time'] = timestampMillisec64()

    api_url = config.get('API_SERVER', 'API_URL')
    api_token = config.get('API_SERVER', 'API_TOKEN')

    url = api_url + '/api/fap_common/send_mail'

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
            module.fail_json(msg='Failed to send mail. (status='+resp.status+', msg='+resp.msg+')')

    except Exception as e:
        module.fail_json(msg='Failed to send mail. (url=' + url + ')')

if __name__ == "__main__":
    main()
