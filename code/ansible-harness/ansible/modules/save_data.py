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

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

import ansible_collections.fap.common.plugins.module_utils.fap_common as FAP

__metaclass__ = type

ANSIBLE_METADATA = {
  "metadata_version": "0.10.1",
  "status": ["stableinterface"],
  "supported_by": "community",
}

DOCUMENTATION = """
---
module: save_data
author:
- Sangsoo Jeon (ssjeon@rtnet.co.kr)
short_description: Module for inputting data into FAP DB
description:
- This module is for input data into the FAP DB.
  You must declare the 'delegate_to = localhost' statement
  because the module must be running in task-level at the ansible local.
requirements:
- httplib2
options:
  fap_vars:
    description:
    - Input FAP variables. {{ fap | default(omit) }}
    required: False
  hostname:
    description:
    - Input host name.
    required: True
  table_name:
    description:
    - Enter the target table name.
    required: False
  archive_days:
    description:
    - Enter the number of days to keep the table data (table_name required).
    required: False
  content:
    description:
    - Input ditionary type data.
    required: True
  data_type:
    description:
    - Define a name for each data type.
      Later, data conversion will be doen by the type name.
    required: True
  data_key:
    description:
    - Enter a key to identify the data.
      If do not enter the key, you can only query by the data type name.
    required: False
"""

EXAMPLES = """
- fap.common.save_data:
    fap_vars: "{{ fap }}"
    hostname: "{{ inventory_hostname }}"
    table_name: ansible_cli_data
    data_type: DATA_TYPE_1
    data_key: DATA_KEY
    content: "{{ input_data }}"
  delegate_to: localhost

- fap.common.save_data:
    fap_vars: "{{ fap }}"
    hostname: "{{ inventory_hostname }}"
    table_name: ansible_cli_data
    archive_days: 365
    data_type: DATA_TYPE_2
    content: "{{ input_data }}"
  delegate_to: localhost
"""

RETURN = """
result:
  description: Result message.
  returned: success
  type: dict
"""

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

def main():

  iniPath = '/fap/ansible/conf/fap.conf'

  # Module arguments
  module_args = dict(
    fap_vars=dict(type='dict', required=False),
    hostname=dict(type='str', required=False),
    table_name=dict(type='str', required=False),
    archive_days=dict(type='int', required=False),
    data_type=dict(type='str', required=True),
    data_key=dict(type='str', required=False),
    content=dict(type='dict', required=False),
    protocol=dict(type='str', required=False),     # Deprecated
    template_id=dict(type='int', required=False),  # Deprecated
    job_id=dict(type='int', required=False),       # Deprecated
  )

  # AnsibleModule
  module = AnsibleModule(
    argument_spec= module_args,
    supports_check_mode=False,
  )

  # Check library
  if not HAS_HTTPLIB2:
    module.fail_json(msg='This module requires httplib2.')

  # Parameters
  fap_vars = module.params.get('fap_vars', None)         # Added 2024.07.26
  hostname = module.params.get('hostname', None)
  table_name = module.params.get('table_name', None)
  archive_days = module.params.get('archive_days', None)
  data_type = module.params.get('data_type', None)
  data_key = module.params.get('data_key', None)
  content = module.params.get('content', None)
  template_id = module.params.get('template_id', None)    # Deprecated
  job_id = module.params.get('job_id', None)              # Deprecated
  
  if fap_vars:
    if not hostname: 
      hostname = FAP.getDicValue(fap_vars, 'host_ip', None)
    if not template_id:
      template_id = FAP.getDicValue(fap_vars, 'template_id', None)
    if not job_id:
      job_id = FAP.getDicValue(fap_vars, 'job_id', None)

  # Check input parameters
  if not data_type:
    module.fail_json(msg='data_type must be define')
  if not content:
    module.fail_json(msg='content is empty')
  
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
  resultData['hostname'] = hostname
  resultData['table_name'] = table_name
  resultData['archive_days'] = archive_days
  resultData['content'] = content
  resultData['data_type'] = data_type
  resultData['data_key'] = data_key
  resultData['template_id'] = template_id
  resultData['job_id'] = job_id
  resultData['insert_time'] = FAP.timestampMilliSec64()

  # API
  api_url = config.get('API_SERVER', 'API_URL')
  api_token = config.get('API_SERVER', 'API_TOKEN')

  url = api_url + '/api/fap_common/save_data'

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
      module.fail_json(msg='Failed to insert data. (protocol=http, status='+resp.status+', msg='+resp.msg+')')

  except Exception as e:
    module.fail_json(msg='Failed to insert data. (protocol=http, url=' + url + ') ' + e.message)

if __name__ == "__main__":
  main()
