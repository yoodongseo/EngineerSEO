# -*- coding: utf-8 -*-
# Copyright: RTNET-Solution

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys, os, time, datetime, re, json, argparse, io, datetime, re
import httplib2, configparser, logging

# Patterns
TN_PATTERN_FIRST_LOGIN    = [b'([Uu]ser\\s?[Nn]ame|[Ll]ogin\\s?(as|[Nn]ame)?|[Pp]assword)\\s*:\\s*']
TN_PATTERN_PASSWORD       = [b'([Pp]assword|PASSCODE):\\s*|.*\xec\x95\x94\xed\x98\xb8:|[Pp]assword.*:\\s*']
TN_PATTERN_PROMPT         = [b'^[\\[<]?[\\w()@.~\\]_\\-\\s]*[\\$#?>]\\s?$', b'^[\\w()@._\\-\\s\\*]*\\.\\d{1,}\\s*#\\s*$']
TN_PATTERN_EN_PROMPT      = [b'^[\\w()@._\\-\\s]*[\\$#?>]\\s?(\\(enable\\))?\\s*$|.*\xec\x95\x94\xed\x98\xb8:']
TN_PATTERN_MORE           = [b'\\s*--(-)*\\s*[Mm][Oo][Rr][Ee]\\s*--', b'\\s*Press <SPACE> to continue\\s*']

PATTERN_USERNAME        = r'([Uu]ser\s?[Nn]ame|[Ll]ogin\s?(as|[Nn]ame)?)\s*:\s*$'
PATTERN_PASSWORD        = r'([Pp]assword|PASSCODE):\s*|.*암호.*:\s*|[Pp]assword.*:\s*'
PATTERN_PROMPT          = r'^[\[<]?[\w()@.~\]_\-\s]*[\$#?>]\s?$|%|^[^\n\r]*[\$#>] ?$'
#PATTERN_PROMPT2         = r'^[\w()@._\-\s\*]*\.\d{1,}\s*#\s*$'
PATTERN_PROMPT2         = r'([a-zA-Z0-9\-\_\.\@\(\)\<\>:/]+)([>#\]])\s*$'
#PATTERN_PROMPT2         = r'^(?:(?:\$\s*)+|(?:%\s*)+|[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+\s*[>#]\s*|N1adm\s*[>#]\s*)$|([a-zA-Z0-9\-\_\.\@\(\)\<\>]+)([>#\]])\s*$|([a-zA-Z0-9\-\_\.\@\(\)\<\>:/]+)([>#\]])\s*$'
PATTERN_EN_PROMPT       = r'^[\w()@._\-\s]*[\$#?>]\s?(\(enable\))?\s*$|.*암호:\s*'
PATTERN_MORE            = r'\s*--(-)*\s*[Mm][Oo][Rr][Ee]\s*--'
PATTERN_MORE2           = r'\s*Press <SPACE> to continue\s*'
PATTERN_AUTH_FAIL       = (
  r'Authentication failure|'
  r'unknown user|'
  r'denied|'
  r'PAM authentication error|'
  r'실패|'
  r'없음|'
  r'거부'
)
        
    

PATTERN_QUESTION        = r'(please enter|press enter|continue\s*\?|are you sure|yes/no|y/n)'

#==================================================
# [Error] Define
#==================================================
class EnablePromptError(Exception):
    """Custom exception for enable prompt mode failures."""
    pass

#==================================================
# [ENUM] Session Status
#==================================================
from enum import Enum
class SessionStatus(Enum):
  READY = 0
  CONNECTED = 1
  LOGINED = 2
  PROMPT = 3
  EN_PROMPT = 4
  EXECUTE_COMMANDS = 5
  DISCONNECTED = 9


#==================================================
# Functions
#==================================================

def iniLogger(logger, module, moduleName, fap_vars):

  if isBlank(moduleName): moduleName="UNKNOWN"
  
  dateFmt='%Y-%m-%d %H:%M:%S'
  format=f'%(asctime)s %(levelname).5s [{moduleName}] %(message)s'
  currDate = datetime.datetime.now().strftime('%Y%m%d')
  currTime = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
  
  host_ip = getDicValue(fap_vars, 'host_ip', None)
  job_id = getDicValue(fap_vars, 'job_id', None)
  
  if host_ip and job_id:
    # log_dir
    log_dir=f'/fap/logs/ansible/{currDate}'

    # Create log directory
    try:
      if not os.path.exists(log_dir): os.makedirs(log_dir)
    except:
      None
    
    # log_file
    #log_file=f'{log_dir}/job_{job_id}_{host_ip}_{currTime}.log'
    log_file=f'{log_dir}/job_{job_id}_{host_ip}.log'
    
  else:
    log_file=None
    
  # Config
  logging.basicConfig(filename=log_file, datefmt=dateFmt, format=format)

  # Log Level
  if module._verbosity > 0:
    logger.setLevel(logging.DEBUG)
  else:
    logger.setLevel(logging.INFO)


 # 사용자가 넣은 입력값이 유효하지 않을때 default 값 사용
def get_valid_param(ssh_params, param_name, default, valid_type=None):
    if not ssh_params or param_name not in ssh_params:
        return default
    value = ssh_params.get(param_name)
    if valid_type:
        try:
            value = valid_type(value)
        except Exception:
            return default
    if value is None:
        return default
    return value

# Compare input line with device_prompt
def comparePromptString(device_prompt, line):
  if isBlank(device_prompt) or isBlank(line): return False
  if device_prompt == line: return True

  # Compare special character removed strings
  if len(line) >= 3 and re.search(PATTERN_PROMPT, line) or re.search(PATTERN_PROMPT2, line):
    cleaned_device_prompt = re.sub(r'[^A-Za-z0-9\s]', '', device_prompt)
    cleaned_line = re.sub(r'[^A-Za-z0-9\s]', '', line)
    if cleaned_device_prompt == cleaned_line:
      return True
  
  return False

# Clean output data
def cleanOutput(output):
  clean_text = []
  
  for char in output:
    # Is backspace ?
    if char == '\x08':
      # Remove previous char  
      if clean_text: clean_text.pop()
    else:
      clean_text.append(char)
  
  output = ''.join(clean_text)
  
  # Remove ANSI escape chars
  # osc_escape = re.compile(r'\x1B]8;;.*?\x1B\\', re.DOTALL)  # OSC 8 링크
  ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')      # ANSI CSI/SGR
  # ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
  # osc_escape = re.compile(r'\x1B]8;;.*?\x1B\\')
  # output = osc_escape.sub('', output)
  output = ansi_escape.sub('', output)
  
  
  return output

# Decode string
def decodeString(data):        
  # utf-8
  try:
    return data.decode('utf-8', errors='ignore')
  except Exception as err:
    None
  # ascii
  try:
    return data.decode('ascii')
  except Exception as err:
    None
  # unicode_escape
  try:
    return data.decode('unicode_escape')
  except Exception as err:
    None
  # str()
  return str(data).replace("\r", "")

# Check data type ( [0] type, [1] data )
def checkDataType(data):
  if isinstance(data, str):
    # string to json
    try:
      _data = json.loads(data)
      return 'json', _data
    except:
      None
    # string to dictionary
    try:
      _data = eval(data)
      return 'dict', _data
    except:
      None
  # Others (str, float, list, dict, tuple, set, Namespace)
  return type(data).__name__, data

# Convert to dictionary
def convertToDict(data):
  try:
    if data is None: return None
    
    _chkData = checkDataType(data)
    if _chkData[0] == 'json':
      return dict(_chkData[1]) # Convert json to dict
    elif _chkData[0] == 'dict':
      return _chkData[1]
    else:
      return None
  except:
    None
  return None

# Convert to dictionary
def convertToJson(data, isPretty=False):
  try:
    _chkData = checkDataType(data)
    if _chkData[0] == 'json':
      if isPretty:
        return json.dumps(data, indent=4)
      else: 
        return data
    elif _chkData[0] == 'dict':
      if isPretty:
        # Convert dict to json
        return json.dumps(_chkData[1], indent=4)
      else:
        return json.dumps(_chkData[1])
    else:
      if isPretty:
        # Convert dict to json
        return json.dumps(_chkData[1], indent=4)
      else:
        return json.dumps(_chkData[1])
  except:
      None
  return None

# Convert to list
def convertToList(data):
  if data is None:
    return None
  elif isinstance(data, list):
    return data
  elif isinstance(data, str):
    # string to json (list)
    try:
      return json.loads(data)
    except:
      None
    # Split by delimiters
    try:
      return data.split(r'[|,]')
    except:
      None

  return None

# Is ASCII
def isAscii(data):
  try:
    if data.encode("ascii", "ignore").decode("ascii") == data:
      return True
    else:
      return False
  except Exception as err:
    return False

# Current milli time 
def timestampMilliSec64():
  return int((datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)

# Save result data
def saveResultData(param, os_type, table_name, data_type, data_key, output_list) :
  if output_list == None:
    return

  # Check ini file
  iniPath = '/fap/ansible/conf/fap.conf'
  if os.path.isfile(iniPath) == False:
    logger.error('[ERROR] Not found config file. ('+ iniPath+')')
    exit()
  
  # Config parser
  config = configparser.ConfigParser()
  config.read(iniPath)

  api_url = config.get('API_SEVER', 'API_URL')
  api_token = config.get('API_SERVER', 'API_TOKEN')

  url  = api_url + '/api/fap_common/save_data'

  try:
    # Make result data
    resultData = {}
    resultData['hostname'] = param['ip']
    resultData['data_type'] = data_type
    resultData['data_key'] = data_key
    resultData['table_name'] = table_name
    resultData['insert_time'] = timestampMilliSec64()
    resultData['content'] = {}
    resultData['content']['data_list'] = []

    if 'template_id' in param:
      resultData['template_id'] = (int)(param['template_id'])
    if 'job_id' in param:
      resultData['job_id'] = (int)(param['job_id'])

    for output in output_list:
      data_item = {}
      data_item['host_name'] = param['ip']
      data_item['cmd_id'] = output['cmd_id']
      data_item['cmd_name'] = output['cmd']
      data_item['cmd'] = output['cmd']
      data_item['os'] = output['os_type']
      data_item['is_success'] = output['is_success']
  
      resultData['content']['data_list'].append(data_item)

    # Debug
    print("########## SEND_DATA_START ##########")
    print(json.dumps(resultData))
    print("########## SEND_DATA_END ##########")

    # Http
    http = httplib2.Http()

    # Make header
    headers = {'Cache-Control':'no-cache', 'x-auth-token':'Bearer '+api_token}

    # Send data
    resp, content = http.request(uri=url, method="PUT", headers=headers, body=json.dumps(resultData))

    # OK=200, CREATED=201, ACCEPTED=202
    if resp.status == 200 or resp.status == 201 or resp.status == 202:
      if content != None:
        #printLog(str(content))
        logger.debug(str(content))
      else:
        logger.error('Failed to send data. (protocol=http, status='+resp.status+', msg='+resp.msg+')')

  except Exception as err:
    logger.error("[ERROR] " + str(err) )


# Set default encoding
def setDefaultEncoding():
  if sys.version_info[0] == 2:
    if sys.getdefaultencoding() == 'ascii':
      reload(sys)
      sys.setdefaultencoding("utf-8")
  else:
    None
  
  #logger.debug('Default Encoding = {}'.format(sys.getdefaultencoding()))
  #logger.debug("한글 테스트.")

# Make directory
def makeDirectory(folder):
  if not os.path.exists(folder):
    # Python 2.x
    if sys.version_info[0] == 2:
      os.makedirs(folder)
    # Python 3.x
    elif sys.version_info[0] >= 3:
      os.makedirs(folder, exist_ok=True)

# Make Result data
def makeResult(isSuccess, output, message):
  result={}
  result['is_success'] = isSuccess
  result['output'] = nomalizeDict(output)
  result['message'] = message
  return result

# Get dictionary value
def getDicValue(dic, column, default_value):
  if column in dic:
    if dic[column] is None:
      return default_value
    else:
      return dic[column]
  else:
    return default_value

# Make error data
def makeErrorResult(errorMessage):
  result={}
  result['is_success'] = False
  result['error_message'] = errorMessage
  return result

# Is blank or null string
def isBlank(str):
  if str is None or len(str) == 0 or str.isspace():
    return True
  else:
    False

# Regex match
def isRegexMatch(strPattern, value):
  try:
    if isBlank(strPattern): return False
    if isBlank(value): return False

    regex = re.compile(strPattern)
    if regex.search(value):
      return True
    else:
      return False
  except Exception as e:
    logger.exception(e)
    return False

# Netmask to PrefixLength ('255.255.255.0' -> 24)
def netmaskToCidr(netmask):
    return sum(bin(int(x)).count('1') for x in netmask.split('.'))

# Netmask to PrefixLength (ex. 24 -> '255.255.255.0' )
def cidrToNetmask(cidr):
  cidr = int(cidr)
  mask = (0xffffffff >> (32 - cidr)) << (32 - cidr)
  return (str( (0xff000000 & mask) >> 24)   + '.' +
          str( (0x00ff0000 & mask) >> 16)   + '.' +
          str( (0x0000ff00 & mask) >> 8)    + '.' +
          str( (0x000000ff & mask)))

# Cleanup empty or null data from dictionary
def cleanupDict(value, isRecursive=True):
  if isinstance(value, list):
    if isRecursive == False:
      # Only current depth
      return [x for x in value if x is not None]
    else:
      # Recursively
      return [cleanupDict(x) for x in value if x is not None]
  elif isinstance(value, dict):
    if isRecursive == False:
      # Only current depth
      return {
          key: val for key, val in value.items() if val is not None
      }
    else:
      # Recursively
      return { 
          key: cleanupDict(val) for key, val in value.items() if val is not None 
      }
  else:
    return value

# Normalize (Convert objects to dictionary)
def nomalizeDict(value):
  # List
  if isinstance(value, list):
    return [nomalizeDict(x) for x in value if x is not None]
  # Dictionary
  elif isinstance(value, dict):
    tmpVal = dict()
    if '__values__' in value:
        for key, val in value['__values__'].items():
            tmpVal[key] = nomalizeDict(val)
    else:
        for key, val in value.items():
            tmpVal[key] = nomalizeDict(val)
    return tmpVal 
  # datetime to string
  elif isinstance(value, datetime.datetime):
    # with timezone
    if value.tzinfo is not None:
      return value.isoformat()
    # datetime
    elif value.__class__.__name__ == 'datetime':
      return value.strftime('%Y-%m-%d %H:%M:%S')
    # date
    elif value.__class__.__name__ == 'date':
      return value.strftime('%Y-%m-%d')
    else:
      return value.isoformat()
  # timedelta to string
  elif isinstance(value, datetime.timedelta):
    return str(value)
  # Object
  elif hasattr(value, '__dict__'):
    return nomalizeDict(value.__dict__)
  else:
    return value

# string to number
def str2num(value, defaultValue=None, minValue=None, maxValue=None):
  if value is None: return defaultValue

  try:
    floatValue = float(value)

    if minValue:
      try:
        if floatValue < float(minValue):
          floatValue = float(minValue)
      except ValueError:
        None

    if maxValue:
      try:
        if floatValue > float(maxValue):
          floatValue = float(maxValue)
      except ValueError:
        None
    
    return floatValue
        
  except ValueError as err:
    if logger: logger.exception(err)
    return defaultValue


# Boolean argument
# ex)  parser.add_argument('--save_flag', required=False, default='False', type=str2bool, help='save flag')
def str2bool(v):
  if isinstance(v, bool):
    return v
  if v.lower() in ('yes', 'true', 't', 'y', '1'):
    return True
  elif v.lower() in ('no', 'false', 'f', 'n', '0'):
    return False
  else:
    raise argparse.ArgumentTypeError('Boolean value expected.')

# terminate
def terminate(params, result, isDisplayResult=True):
  if params is None: return

  try:
    # Put requet_id to result
    result['time'] = int(time.time())
    result['local_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

    # Remove empty or null data
    result = cleanupDict(result, isRecursive=False)

    # Convert dict to json
    jsonResult = json.dumps(result)

    # Print result data
    if (isDisplayResult):
      print('===== RESULT_DATA_START =====')
      print(jsonResult)
      print('===== RESULT_DATA_END =====')

  except Exception as e:
    print(e)

  # Terminate
  os._exit(1)

