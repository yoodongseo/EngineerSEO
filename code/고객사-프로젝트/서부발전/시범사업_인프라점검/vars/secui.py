import os
import re
import json
import traceback
import requests
from requests.auth import HTTPBasicAuth
import urllib3
import time
import sys
from datetime import datetime, timedelta

class CustomerError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ansi_escape = re.compile(r"(?:\x1B[@-Z\\-_]|\x1B\[.*?[ -/]*[@-~])")

# 변수
hostname = os.environ.get('hostname', '')
username = os.environ.get('username', '')
password = os.environ.get('password', '')
raw = os.environ.get('raw', '')
port = os.environ.get('port', '')
become_password = os.environ.get('root_passwd', '')
vendor = os.environ.get('vendor', '')
sec = os.environ.get('time', '')

# 내부 사용 변수
token_api = 'api/au/external/login'
system_api = 'api/lr/dashboard?type=system_resource_status'
device_api = 'api/lr/dashboard?type=system_device_info'
time_api = 'api/co/current-time'

class Secui_Task:
    def GetStart(self, hostname, port, username, password, raw):
         verify_info = False
         url_auth = "https://" + hostname + ":" + port + "/" + token_api
        
         if raw == 'fan' or raw == 'psu' or raw == 'if':
             url = "https://" + hostname + ":" + port + "/" + device_api
         elif raw == 'cpu' or raw == 'mem' or raw == 'disk' :
             url = "https://" + hostname + ":" + port + "/" + system_api
         elif raw == 'time':
             url = "https://" + hostname + ":" + port + "/" + time_api
         elif raw == 'syslog':
             url = "https://" + hostname + ":" + port 
        
        
         status_code_ok = 200
         result = {}
        
         try:
             authdata = {
                 "ext_clnt_id": username,
                 "ext_clnt_secret": password,
                 "lang": "ko",
                 "force": 1
             }
            
             response = requests.post(url_auth, json=authdata, verify=verify_info)
             if hasattr(response, "status_code") and response.status_code == status_code_ok:
                 token = response.json().get("result").get("api_token")
                 if raw == 'time':
                     result = self.GetTime(url, token)
                 elif raw == 'syslog':
                     result = self.GetLog(raw, url, token)
                 else:
                     result = self.GetData(raw, url, token)
             elif hasattr(response, "status_code") and response.status_code != status_code_ok:
                 result = {
                     "status_code": response.status_code,
                     "err_msg": response.text
                 }
             else:
                 result = {
                     "status_code": "",
                     "err_msg": response.text
                 }
         except Exception as e:
             err_msg = e
             traceback_msg = traceback.format_exc()            
             result = {
                 "err_msg": str(err_msg),
                 "traceback_msg": traceback_msg
             }
            
        #result = {
        #     "fan": { "FAN1": "5700", "FAN2": "6000", "FAN3": "5600", "FAN4": "6000", "FAN5": "5500", "FAN6": "6000", "CRITICAL": 2000 }        
       # }
        
         return result
        # return json.dumps(result,default=str, indent=2)
       
    
    def GetData(self, raw, url, token):
        now = datetime.now()
        today = datetime(now.year, now.month, now.day)
        stime = today.strftime('%Y-%m-%d %H:%M:%S')
        etime = now.strftime('%Y-%m-%d %H:%M:%S')
        
        headers = {
            "Authorization": token
        }
        
        verify_info = False
        status_code_ok = 200
        result = {}
        
        try:
            url = url + "&stime=" + stime + "&etime=" + etime
            response = requests.get(url, headers=headers, verify=verify_info)
            
            if hasattr(response, "status_code") and response.status_code == status_code_ok:
                data = response.json().get("result").get("result")
                if raw == "fan":
                    for item in data:
                        result = {
                            "fan": item.get("hwmon").get("fan")
                        }
                        break
                elif raw == "psu":
                    for item in data:
                        result = {
                            "psu": item.get("hwmon").get("psu")
                        }
                        break
                elif raw == "cpu":
                    for item in data:
                        result = {
                            "cpu_usage": item.get("cpu_usage")
                        }
                        break
                elif raw == "mem":
                    for item in data:
                        result = {
                            "memory_usage": item.get("memory_usage")
                        }
                        break
                elif raw == "disk":
                    for item in data:
                        result = {
                            "disk_usage": item.get("disk_usage")
                        }
                        break
                elif raw == "if":
                    for item in data:
                        result = {
                            "interface": item.get("interface")
                        }
                        break
            elif hasattr(response, "status_code") and response.status_code != status_code_ok:
                result = {
                    "status_code": response.status_code,
                    "err_msg": response.text
                }
            else:
                result = {
                    "status_code": "",
                    "err_msg": response.text
                }
        except Exception as e:
            err_msg = e
            traceback_msg = traceback.format_exc()            
            result = {
                "err_msg": str(err_msg),
                "traceback_msg": traceback_msg
            }
        
        return result
    
    def GetTime(self,url, token):
          
        headers = {
            "Authorization": token
        }
        
        verify_info = False
        status_code_ok = 200
        result = {}
        
        try:
            response = requests.get(url, headers=headers, verify=verify_info)
            
            if hasattr(response, "status_code") and response.status_code == status_code_ok:
                result = {
                    "current_time": response.json().get("result").get("current_time")
                }
            elif hasattr(response, "status_code") and response.status_code != status_code_ok:
                result = {
                    "status_code": response.status_code,
                    "err_msg": response.text
                }
            else:
                result = {
                    "status_code": "",
                    "err_msg": response.text
                }
        except Exception as e:
            err_msg = e
            traceback_msg = traceback.format_exc()            
            result = {
                "err_msg": str(err_msg),
                "traceback_msg": traceback_msg
            }
        
        return result
    
    def GetLog(self, url, token):
        
        now = datetime.now()
        # today = datetime(now.year, now.month, now.day)        
        # stime = today.strftime('%Y-%m-%d %H:%M:%S')        
        stime = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S')
        etime = now.strftime('%Y-%m-%d %H:%M:%S')
                
        data = {
        'stime': stime,
        'etime': etime,
        'order_by': 'asc',
        'log_type': 'system'
        }
        
        headers = {
            "Authorization": token
        }       
        
        starturl = url + "/lr/log/start" 
        
        verify_info = False
        status_code_ok = 200
        result = {}
        
        try:
            
            # 로그 검색 시작
            response = requests.post(starturl , headers=headers, data=json.dumps(data), verify=verify_info)
                        
            if hasattr(response, "status_code") and response.status_code == status_code_ok:
                
                reqid = response.json()['result']['request_id']
                print(reqid)
                
                # 검색 상태 확인
                status = self.GetLogStatus(url, token, reqid)
                if status is None:
                    result = {                        
                        "status_code": "",
                        "err_msg": "status is None - GetLogStatus"
                    }
                                    
                while status['result']['status'] != 'DONE':
                    status = self.GetLogStatus(url, token, reqid)
                    if status is None:
                        result = {                        
                            "status_code": "",
                            "err_msg": "status is None - GetLogStatus"
                        }             
                
                # 로그 결과 가져오기
                logs = self.GetLogData(url, token, reqid, 0, 100)  # 범위 조정 가능
                if logs is not None:
                    result = {                        
                        "logs": logs,
                        "err_msg": ""
                    }
                else:
                    result = {                        
                            "logs": "",
                            "err_msg": "logs is None - GetLogData"
                        }   
                    
            elif hasattr(response, "status_code") and response.status_code != status_code_ok:
                result = {
                    "status_code": response.status_code,
                    "err_msg": response.text
                }
            else:
                result = {
                    "status_code": "",
                    "err_msg": response.text
                }
        except Exception as e:
            err_msg = e
            traceback_msg = traceback.format_exc()            
            result = {
                "err_msg": str(err_msg),
                "traceback_msg": traceback_msg
            }
        
        return result
    
    def GetLogStatus(self, url, token, reqid):        
        headers = {
        'Authorization': token,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
        }        
        
        response = requests.get(f'{url}/lr/log/{reqid}/status', headers=headers, verify=False)
    
        # 요청이 성공했는지 확인
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP 에러 발생: {err}")
            return None

        return response.json()
    
    def GetLogData(self, url, token, reqid,start,end):        
        headers = {
        'Authorization': token,
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0'
        }        
        
        response = requests.get(f'{url}/lr/log/{reqid}/page/{start}/to/{end}', headers=headers, verify=False)
    
        # 요청이 성공했는지 확인
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP 에러 발생: {err}")
            return None

        return response.json()
    


def main():
    task = Secui_Task()
    # hostname = "https://192.0.2.10"
    # port = "443"
    # username = "d148adc00ffc42bab9fda49b37460a45"
    # password = "CHANGE_ME_PASSWORD"
    # raw = "syslog"
    result = task.GetStart(hostname, port, username, password, raw)
    
    # print(json.dumps(result,default=str, indent=2))    
    # print(result)    
    # 각 항목을 "키": "값" 형태로 변환하여 한 줄씩 출력
    
    if raw == 'fan':        
        fresult = result['fan']
    else:
        fresult = result
    
    for key, value in fresult.items():
        if isinstance(value, str):
            print(f'"{key}": "{value}"')
        else:
            print(f'"{key}": {value}')    
    
    # print(result.replace('\n', ' '))    
    # print(json.dumps(result,default=str, indent=2))    
    print(" ")    
    

if __name__ == "__main__":
    main()
