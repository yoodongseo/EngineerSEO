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
    
        if raw == 'fan' or raw == 'psu' or raw == 'interface':
            url = "https://" + hostname + ":" + port + "/" + device_api
        elif raw == 'cpu' or raw == 'mem' or raw == 'disk' :
            url = "https://" + hostname + ":" + port + "/" + system_api
        elif raw == 'time':
            url = "https://" + hostname + ":" + port + "/" + time_api
        elif raw == 'syslog':
            url = "https://" + hostname + ":" + port 
        
        
        status_code_ok = 200
        result = {}
         
        #  테스트용 결과 데이터 Start .. -> 체크 후 주석!
        if raw == 'fan': 
            result = {
                "fan": { "FAN1": "5700", "FAN2": "6000", "FAN3": "5600", "FAN4": "6000", "FAN5": "5500", "FAN6": "6000", "CRITICAL": 2000 }
                }
        elif raw == 'psu': 
            result = {
                "psu": { "PSU1": "OK", "PSU2": "OK" }
            }
        elif raw == 'interface':
            result = {
                "interface": {
                    "eth0": {
                        "zone": "DMZ",
                        "mode": "L3",
                        "ipaddress": ["10.10.2.20/20"],
                        "if_up": "Up",
                        "link_up": "yes",
                        "type": "Copper",
                        "speed": "1G",
                        "duplex": "Full Duplex"
                    },
                    "eth1": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth2": {
                        "zone": "HA",
                        "mode": "L3",
                        "ipaddress": ["1.1.1.1/24"],
                        "if_up": "Up",
                        "link_up": "yes",
                        "type": "Fiber",
                        "speed": "10G",
                        "duplex": "Full Duplex"
                    },
                    "eth3": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth111": {
                        "zone": "Internal",
                        "mode": "L2",
                        "ipaddress": [],
                        "if_up": "Up",
                        "link_up": "yes",
                        "type": "Copper",
                        "speed": "1G",
                        "duplex": "Full Duplex"
                    },
                    "eth112": {
                        "zone": "External",
                        "mode": "L2",
                        "ipaddress": [],
                        "if_up": "Up",
                        "link_up": "yes",
                        "type": "Copper",
                        "speed": "1G",
                        "duplex": "Full Duplex"
                    },
                    "eth113": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth114": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth115": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth116": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth117": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth118": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Copper", "speed": "", "duplex": "" },
                    "eth131": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth132": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth133": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth134": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth135": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth136": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth137": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" },
                    "eth138": { "zone": "None", "mode": "L3", "ipaddress": [], "if_up": "Up", "link_up": "no", "type": "Fiber", "speed": "", "duplex": "" }
                    }
            }
            
        elif raw == 'cpu':
            result = "1.4"
        elif raw == 'mem':
            result = "37.3"
        elif raw == 'disk' :
            result = "0.2"
        elif raw == 'time':
            result = "2024-08-12 04:46:49.901442"
        elif raw == 'syslog':
            result = "check url"
        
        #  테스트용 결과 데이터 End
        
        # try:
        #     authdata = {
        #         "ext_clnt_id": username,
        #         "ext_clnt_secret": password,
        #         "lang": "ko",
        #         "force": 1
        #     }
        
        #     response = requests.post(url_auth, json=authdata, verify=verify_info)
        #     if hasattr(response, "status_code") and response.status_code == status_code_ok:
        #         token = response.json().get("result").get("api_token")
        #         if raw == 'time':
        #             result = self.GetTime(url, token)
        #         elif raw == 'syslog':
        #             result = self.GetLog(url, token)
        #         else:
        #             result = self.GetData(raw, url, token)
        #     elif hasattr(response, "status_code") and response.status_code != status_code_ok:
        #         result = {
        #             "status_code": response.status_code,
        #             "err_msg": response.text
        #         }
        #     else:
        #         result = {
        #             "status_code": "",
        #             "err_msg": response.text
        #         }
        # except Exception as e:
        #     err_msg = e
        #     traceback_msg = traceback.format_exc()            
        #     result = {
        #         "err_msg": str(err_msg),
        #         "traceback_msg": traceback_msg
        #     }
        return result
        
       
    
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
                elif raw == "interface":
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
    
    def printKeyValue(self, result):
        for key, value in result.items():
            if isinstance(value, str):
                print(f'"{key}": "{value}"')
            else:
                print(f'"{key}": {value}')    

def main():
    task = Secui_Task()
    # hostname = "https://192.168.100.100"
    # port = "443"
    # username = "d148adc00ffc42bab9fda49b37460a45"
    # password = "7e92fc74f3f4ca84ea9acdc1eb3a64cbfdb80a1549aa0faeaed6308857022eca"
    # raw = "syslog"
    result = task.GetStart(hostname, port, username, password, raw)
    
    # print(json.dumps(result,default=str, indent=2))    
    # print(result)    
    # 각 항목을 "키": "값" 형태로 변환하여 한 줄씩 출력
    
    if raw == 'fan' or raw == "psu" or raw == "interface":        
        fresult = result[raw]
        task.printKeyValue(fresult)        
    else:
        fresult = result
        print(fresult)
        
    
    # for key, value in fresult.items():
    #     if isinstance(value, str):
    #         print(f'"{key}": "{value}"')
    #     else:
    #         print(f'"{key}": {value}')    
    
    # print(result.replace('\n', ' '))    
    # print(json.dumps(result,default=str, indent=2))    
    # print(" ")    
    

if __name__ == "__main__":
    main()
