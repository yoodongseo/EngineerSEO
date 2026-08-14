#!/usr/bin/python3
# 커스텀 모듈 사용을 위해서는 각 프로젝트의 ansible.cfg 파일에 아래와 같은 설정을 추가 한다.
# [dfeaults]1
# filter_plugins = /fap/ansible/projects/custom

"""
모듈 설명
1) make_report_dns -> DNS 정기점검 정보를 넘겨 받고 점검하여 보고서, to_json 형태로 반환
2) make_syslog_dns -> DNS SYSLOG 정보를 넘겨 받고 점검하여 보고서 to_json 형태로 변환
3) make_add_a_record_dns -> DNS A 레코드 추가 작업 정보를 넘겨 받고 to_json 형태로 변환
4) dns_async -> DNS 동기화
5) gslb_async -> GSLB 동기화
6) make_report_gslb -> GSLB 정기점검,추가,수정,삭제 작업 후 보고서, to_json 형태로 반환


반환값 설명
result = {
            'file_path': file_path, # 생성되는 보고서의 full path
            'is_success': is_success, # 작업 수행 여부
            'data': df, # 포탈로 넘겨줄 데이터. 포탈연계 인터페이스에 정의 필요. !!only json!! --> 예시) dataframe.to_json()
            'is_pass': is_pass, # 작업 성공 여부(한개라도 실패면 실패임)
            'err_msg': err_msg # 에러메시지 정보
        }
"""        

from ansible.plugins.filter.core import FilterModule # ansible 필터에 필요한 라이브러 호출
import pandas as pd
import os
import openpyxl
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
import numpy as np
import re, json
from datetime import datetime, timedelta

# authzone 찾기 함수
def search_authzone(authzone_list, a_record, authzone):
    tmp_list = []
    #  authzone_list 중에서 맨끝이 a_record로 끝나는 문자열을 찾아서 리스트로 만들기
    for item in authzone_list:
        if a_record.endswith(item):
            tmp_list.append(item)
    # 생성된 리스트 중, 문자열의 길이가 가장 긴 authzone을 추출하기
    matched_authzone = sorted(tmp_list, key=len, reverse=True)[0]

    # 입력받은 authzone과 추출된 authzone을 비교
    if authzone == matched_authzone:
        return True
    else:
        return False

# DNS A, CNAME 레코드 정보 동기화 함수
def dns_async_a_c_record(async_list: list, dns_type_name: str) -> list:
    async_dict = {
                    "_ref": None,
                    "delegate_to": None,
                    "fqdn": None,
                    "ipv4addr": None,
                    "name": None,
                    "canonical": None,
                    "zone_type": None,
                    "record_type": None,
                    "forward_to": None,
                    "view": None
                }    
    return_async_list = []
    dns_type = ''

    if dns_type_name in ['a_record', 'c_record']:
        dns_type = 'record_type'
    
    if dns_type_name in ['zone_forward', 'zone_auth', 'zone_delegated']:
        dns_type = 'zone_type'

    # a record 업데이트(존재 시)
    for record in async_list:                                    
        # record 정보 삽입
        async_dict.update({dns_type: dns_type_name})
        # 레코드 정보 업데이트                
        async_dict.update(record)
        # 동기화 항목에 추가
        return_async_list.append(async_dict)   
        # async_dict 초기화
        async_dict = {key: None for key in async_dict}
    # a record 업데이트(미 존재시)
    if not async_list:
        # a record 정보 삽입
        async_dict.update({dns_type: dns_type_name})
        # 레코드 정보 업데이트
        return_async_list.append(async_dict)   
        # async_dict 초기화
        async_dict = {key: None for key in async_dict}  

    return return_async_list

# 데이터 프레임으로 엑셀 만들어주는 함수
def make_excel(df, file_path):    
    # 데이터 프레임을 엑셀로 변환
    df.to_excel(file_path, index=False)
    # 워크북 객체 생성
    workbook = load_workbook(filename=file_path)
    # 시트 활성화
    sheet = workbook.active
    # 테두리 적용
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        for idx, cell in enumerate(row):
            cell.border = openpyxl.styles.Border(
                left = openpyxl.styles.Side(border_style="thin"),
                right = openpyxl.styles.Side(border_style="thin"),
                top = openpyxl.styles.Side(border_style="thin"),
                bottom = openpyxl.styles.Side(border_style="thin")
            )
            # 가운데 정렬
            if idx != 5:
                cell.alignment = Alignment(horizontal='center', vertical='center')

    # 크기 조정
    for column in sheet.columns:
        max_length = 0
        column = [cell for cell in column]
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
            except:
                pass
        adjusted_width = max_length + 2
        sheet.column_dimensions[openpyxl.utils.get_column_letter(column[0].column)].width = adjusted_width

    # 변경 내용 저장
    workbook.save(file_path)


# 데이터 프레임으로 엑셀 만들어주는 함수 (For GSLB)
def make_excel_GSLB(df, file_path,columnString):    
    # 데이터 프레임을 엑셀로 변환
    df.to_excel(file_path, index=False)
    # 워크북 객체 생성
    workbook = load_workbook(filename=file_path)
    # 시트 활성화
    sheet = workbook.active
    
    font = Font(size=9)

    for column in sheet.columns:
        max_length=0    
        column = [cell for cell in column]            
        column_letter = openpyxl.utils.get_column_letter(column[0].column)
        for cell in column:
            try:                                 
                match = re.match(r"([A-Z]+)(\d+)",cell.coordinate)                        
                addrcol = match.group(1)
                addrrow = int(match.group(2))
                # pydebug += "addrcol = " + f"{addrcol}" + "\n"                        
                # pydebug += "addrrow = " + f"{addrrow}" + "\n" 
                if  addrrow == 1: 
                    cell.alignment = Alignment(horizontal='center',vertical='center',wrap_text=True)                                                                               
                else:                                            
                    cell.alignment = Alignment(horizontal='left',vertical='top',wrap_text=True)  
                    cell.font = font                                                                                                                                      

                

                if len(str(cell.value)) > max_length:
                    max_length = len(cell.value)
                    if max_length > 100:
                        max_length = 100                 
                    # if addrcol == columnString:   # Data 컬럼은 열넓이가 너무 넓어 강제 정의 함
                    #     max_length = 70
            except:
                pass
        adjusted_width = (max_length + 2) * 1.2
        sheet.column_dimensions[column_letter].width = adjusted_width

    # 테두리 적용
    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
        for cell in row:
            cell.border = openpyxl.styles.Border(
                left = openpyxl.styles.Side(border_style="thin"),
                right = openpyxl.styles.Side(border_style="thin"),
                top = openpyxl.styles.Side(border_style="thin"),
                bottom = openpyxl.styles.Side(border_style="thin")
            )

    # 변경 내용 저장
    workbook.save(file_path)

class FilterModule(FilterModule):
    def filters(self):
        return {
            'make_report_dns': self.make_report_dns, # 서버별 상태 점검 보고서, dataframe 생성
            'make_syslog_dns': self.make_syslog_dns, # 시스로그 보고서, dataframe 생성
            'make_add_a_record_dns': self.make_add_a_record_dns, # a/cname/forward 추가 작업 보고서, dataframe 생성
            'dns_async': self.dns_async,
            'gslb_async': self.gslb_async,
            'make_report_gslb': self.make_report_gslb
        }

    def gslb_async(self, data_list, file_path, pool_member_list, vsvr_ref_list, wideipsstats_list):
        try:
            #변수 설정
            gslb_async_list = []
            err_msg = ""
            # 파일 경로 생성
            if len(data_list) > 0:                
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True                                         
                
                # wideips_a 추출
                wideips_a = []
                for item in data_list[0]:
                    wideips_a.append({
                        "name": item.get("name"),
                        "fullPath": item.get("fullPath"),
                        "enabled": item.get("enabled"),
                        "poolLbMode": item.get("poolLbMode"),
                        "pools": [
                            {
                                "name": pool.get("name"),
                                "order": pool.get("order"),
                                "ratio": pool.get("ratio")
                            } for pool in item.get("pools", [])
                            ],
                    })
                
                # pool_a 추출
                pool_a = []
                idx = 0
                for item in data_list[1]:                    
                    pool_a.append({
                        "name": item.get("name"),
                        "loadBalancingMode": item.get("loadBalancingMode"),
                        "alternateMode": item.get("alternateMode"),
                        "fallbackMode": item.get("fallbackMode"),
                        "ttl": item.get("ttl"),
                        "monitor": item.get("monitor"),
                        "members": []
                    })
                for item in pool_member_list:                    
                    for item2 in item:
                        pool_a[idx]["members"].append({
                            "name": item2.get("name"),
                            "ratio": item2.get("ratio"),
                            "memberOrder": item2.get("memberOrder")
                        })                        
                    idx += 1

                # monitor 추출
                monitors = []
                for item in (data_list[2] + data_list[3] + data_list[4]):
                    monitors.append({
                        "name": item.get("name"),
                        "fullPath": item.get("fullPath")
                    })                
                
                # virtual server 추출
                vsvr_ref = []
                idx = 0
                for item in data_list[5]:                    
                    vsvr_ref.append({
                        "name": item.get("name"),
                        "datacenter": item.get("datacenter"),
                        "addresses": item.get("addresses"),
                        "virtualServer": []
                    })
                for item in vsvr_ref_list:                    
                    for item2 in item:
                        vsvr_ref[idx]["virtualServer"].append({
                            "name": item2.get("name"),
                            "destination": item2.get("destination"),                            
                        })                        
                    idx += 1

                # wideips_a 상태 추출
                wideips_astats = []             
                for item in wideipsstats_list:
                    wideips_a.append({
                        "status.availabilityState": item.get("status.availabilityState").get("description"),
                        "status.enabledState": item.get("status.enabledState").get("description"),
                        "status.statusReason": item.get("status.statusReason").get("description")                        
                    })
                # merge
                result = []
                result = [{
                    "WideipsA": wideips_a,
                    "PoolA": pool_a,
                    "MonitorInfo": monitors,
                    "ServerInfo": vsvr_ref
                }]
                # 데이타프레임 생성
                df = pd.DataFrame(data_list)
                # 보고서 생성
                make_excel(df, file_path)
                 # 작업 정상 수행 여부                 
                is_success = True
            else:
                result = {}
                df = {}
                is_pass = False
                is_success = True
                
            is_pass = True
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(result), # df.to_json(force_ascii=False),
                'is_pass': is_pass,  # 점검 성공 여부
                'err_msg': err_msg
                }

            return result
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': df,
                'is_pass': is_pass, 
                'err_msg': err_msg
                }
            return result
            
    def dns_async(self, data_list, file_path):
        try:
            # 파일 경로 생성
            if len(data_list) > 0:                
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True            
                err_msg = ""
                orin_async_list = []  
                dns_key_list = ["a_record", "cname_record", "zone_auth", "zone_forward", "zone_delegated"]
                dns_zone_list = ["zone_auth", "zone_forward", "zone_delegation"]                  
                async_dict = {}
                async_dict_new = {}                
                
                # data_list 파싱
                for data in data_list:
                    orin_async_list.append(data['json'])

                # DNS 동기화 정보 Ver1 -> Orin data
                for dns_key, async_data in zip(dns_key_list, orin_async_list):
                    async_dict[dns_key] = async_data

                # DNS 동기화 정보 Ver2 -> Parsing data                
                auth_fqdn_list = []
                forward_fqdn_list = []
                delegated_fqdn_list = []
                data_zone_auth = []

                # dns_zone_list 별로 데이터 파싱 시작
                for zone in dns_zone_list:
                    # zone_auth 키에 데이터 저장 시작
                    if zone == "zone_auth": 
                        async_dict_new.update({zone: []})                        
                        data_a_record = []
                        data_c_record = []
                        # auth zone fqdn 정보 생성                   
                        for zune_auth in async_dict["zone_auth"]:
                            auth_fqdn_list.append(zune_auth["fqdn"])          
                        # a, c record 정보 추출 후에 data에 저장
                        for auth_fqdn in auth_fqdn_list:                                          
                            data_a_record = [d for d in async_dict["a_record"] if d.get("name", "").endswith(auth_fqdn)] 
                            data_c_record = [d for d in async_dict["cname_record"] if d.get("name", "").endswith(auth_fqdn)] 
                            async_dict_new[zone].append({
                                "fqdn": auth_fqdn,
                                "data": data_a_record + data_c_record
                                })
                            
                    elif zone == "zone_forward":
                        async_dict_new.update({zone: async_dict["zone_forward"]})
                        for item in async_dict_new[zone]:
                            item["data"] = item.pop("forward_to")          
                    elif zone == "zone_delegation":
                        async_dict_new.update({zone: async_dict["zone_delegated"]})
                        for item in async_dict_new[zone]:
                            item["data"] = item.pop("delegate_to")     
                    else:
                        pass
                
                
                # 2차 파싱
                new_zone_auth = []
                idx = 0


                for orin_zone_auth in async_dict_new["zone_auth"]:
                    # set uniq zone name, merged a record
                    uniq_zone_name = {}    
                    merged_a_record = []

                    # remove a record 
                    new_zone_auth.append({
                        "fqdn": orin_zone_auth["fqdn"],
                        "data": [item_orin_zone_auth for item_orin_zone_auth in orin_zone_auth["data"] if "canonical" in item_orin_zone_auth]
                        })    
                    for item in orin_zone_auth["data"]:        
                        # a record 인 경우~        
                        if "ipv4addr" in item and "name" in item:
                            # 유니크 존 네임에 이름이 없으면 추가
                            if item["name"] not in uniq_zone_name: 
                                # 유니크 존네임 키 생성                
                                uniq_zone_name[item["name"]] = [item["ipv4addr"]]
                            else:
                                uniq_zone_name[item["name"]].append(item["ipv4addr"]) 


                    # 추출한 유니크 존 별 아이피 정보를 name, ipv4addr 형태로 변환  
                    for key, value in uniq_zone_name.items():
                        new_zone_auth[idx]["data"].append({
                            "name": key,
                            "ipv4addr": value
                            })
                        # merged_a_record.append({
                        #     "name": key,
                        #     "ipv4addr": value
                        #     })            

                    
                    # new_zone_auth[idx]["data"].append(merged_a_record)
                    idx = idx + 1               

                async_dict_new["zone_auth"] = new_zone_auth 
                
                # # 3차 파싱
                # authzone을 목록형태로 만들기
                authzone_list = [item["fqdn"] for item in async_dict_new["zone_auth"]]
                 
                for i, zone_auth_data in enumerate(async_dict_new["zone_auth"]):
                    # set tmp record info
                    tmp_record_info = []
                    # get authzone name
                    zone_auth = zone_auth_data["fqdn"]
                    # check authzone name with dot count info
                    for j, record_info in enumerate(zone_auth_data["data"]):
                        if search_authzone(authzone_list, record_info["name"], zone_auth):
                            tmp_record_info.append(record_info)
                    zone_auth_data["data"] = tmp_record_info
               

                # async data 파싱을 위한 data_list의 인덱스 정보
                a_record_idx = 0
                cname_record_idx = 1
                zone_auth_idx = 2
                zone_forward_idx = 3
                zone_delegated_idx = 4

                result_a_record = dns_async_a_c_record(orin_async_list[a_record_idx], "a_record")
                result_cname_record = dns_async_a_c_record(orin_async_list[cname_record_idx], "c_record")   
                result_auth_zone = dns_async_a_c_record(orin_async_list[zone_auth_idx], "zone_auth")  
                result_forward_zone = dns_async_a_c_record(orin_async_list[zone_forward_idx], "zone_forward")
                result_delegated_zone = dns_async_a_c_record(orin_async_list[zone_delegated_idx], "zone_delegated")

                result = (result_a_record +
                          result_cname_record +  
                          result_auth_zone +
                          result_forward_zone +
                          result_delegated_zone)              
                            
                # 데이타프레임 생성
                df = pd.DataFrame(result)
                # 보고서 생성
                make_excel(df, file_path)
                 # 작업 정상 수행 여부
                 
                is_success = True
            else:
                df = {}
                is_pass = False
                is_success = True
                
            is_pass = True
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': async_dict_new, # df.to_json(force_ascii=False),
                'is_pass': is_pass,  # 점검 성공 여부
                'err_msg': err_msg
                }

            return result
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': df,
                'is_pass': is_pass, 
                'err_msg': err_msg
                }
            return result
    def make_add_a_record_dns(self, data_list, file_path, err_flag, connection_info={}):
        try:
            # 파일 경로 생성
            directory_path, file_name = os.path.split(file_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)     

            # 접속 실패
            if connection_info.get("is_connected") == False or connection_info.get("is_active") == False:                
                try:
                    # 실패 정보 보고서 생성
                    df = pd.DataFrame([connection_info])
                    make_excel(df, file_path)                

                    result = {
                        'file_path': file_path,
                        'is_success': True, 
                        'data': json.dumps(connection_info, ensure_ascii=False),
                        'is_pass': True if connection_info.get("is_active") == False else False,
                        'err_msg': connection_info.get("err_msg"),
                        'err_flag': True
                    }

                    return result
                except Exception as e:
                    return e

            # 파일 경로 생성
            if len(data_list) > 0:                
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True            
                err_msg = ""            

                """
                검증 정보 저장
                1) 작업 실행 전, 검증 플래그가 false이면 본작업 미실행
                2) 작업 실행 전, 검증 플래그가 true이면 본작업 실행
                """
                if err_flag:
                    data_list = [{**data, "검증 결과": "검증 실패"} for data in data_list]                                               
                else:
                    data_list = [{**data, "검증 결과": "검증 성공"} for data in data_list]                    

                # 작업 성공 판단
                for data in data_list:
                    if data["err_flag"]: is_pass = False
                
                # 데이타프레임 생성
                df = pd.DataFrame(data_list)
                # 보고서 생성
                make_excel(df, file_path)
                 # 작업 정상 수행 여부
                 
                is_success = True
            else:
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                df = {}
                is_pass = False
                is_success = True

                # 접속 실패 시, 보고서 생성을 위한 데이타프레임 생성
                df = pd.DataFrame([{
                    'is_success': is_success,
                    'data': {}, #.to_json(force_ascii=False),
                    'is_pass': is_pass,  # 점검 성공 여부
                    'err_msg': err_msg
                }])

                # 보고서 생성
                make_excel(df, file_path) 
            
            # error info update
            if err_flag:                
                if isinstance(data_list, dict):
                    err_msg = err_info.get("err_msg") if err_flag else ""
                elif isinstance(data_list, list):                
                    err_msg = data_list[0].get("err_msg") if err_flag else ""
                elif isinstance(data_list, str):
                    err_msg = data_list if err_flag else ""

            kst_time = datetime.now() + timedelta(hours=9)
            data_list.append({"creation_time": kst_time.strftime("%Y-%m-%d %H:%M:%S")})
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': data_list, #.to_json(force_ascii=False),
                'is_pass': is_pass,  # 점검 성공 여부
                'err_msg': err_msg
                }

            
            return result
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(df),
                'is_pass': is_pass, 
                'err_msg': err_msg
                }
            return result

    def make_add_c_record_dns(self, data_list, file_path, err_flag):
        try:
            # 파일 경로 생성
            if len(data_list) > 0:                
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True            
                err_msg = ""            

                """
                검증 정보 저장
                1) 작업 실행 전, 검증 플래그가 false이면 본작업 미실행
                2) 작업 실행 전, 검증 플래그가 true이면 본작업 실행
                """
                if err_flag:
                    data_list = [{**data, "검증 결과": "검증 실패"} for data in data_list]                    
                else:
                    data_list = [{**data, "검증 결과": "검증 성공"} for data in data_list]

                # 작업 성공 판단
                for data in data_list:
                    if data["err_flag"]: is_pass = False
                
                # 데이타프레임 생성
                df = pd.DataFrame(data_list)
                # 보고서 생성
                make_excel(df, file_path)
                 # 작업 정상 수행 여부
                 
                is_success = True
            else:
                df = {}
                is_pass = False
                is_success = True
                
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(data_list, ensure_ascii=False), #.to_json(force_ascii=False),
                'is_pass': is_pass,  # 점검 성공 여부
                'err_msg': err_msg
                }

            return result
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': df,
                'is_pass': is_pass, 
                'err_msg': err_msg
                }
            return result

    def make_syslog_dns(self, data_list, file_path, connection_info=False):       
        try:
            directory_path, file_name = os.path.split(file_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)

            # 접속 실패
            if connection_info.get("is_connected") == False or connection_info.get("is_active") == False:                
                try:
                    # 실패 정보 보고서 생성
                    df = pd.DataFrame([connection_info])
                    make_excel(df, file_path)                

                    result = {
                    'file_path': file_path,
                    'is_success': True, 
                    'data': json.dumps(connection_info, ensure_ascii=False),
                    'is_pass': False,
                    'err_msg': connection_info.get("err_msg"),
                    'err_flag': True
                    }

                    return result
                except Exception as e:
                    return e
                    
            # 파일 경로 생성
            if len(data_list) > 0:
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True            
                err_msg = ""
                filtered_list = []
                log_lines_cnt = 1000

                # 시스템 로그 인덱스 정보
                timestamp_idx = 0
                facility_idx = 1
                host_idx = 2 
                server_idx = 3
                level_idx = 4
                msg_idx =5
                
                # 불필요한 로그 제거
                for data in (list(reversed(data_list)))[0:log_lines_cnt]:
                    matcheds = re.findall(r'\d{4}-\d{2}-\d{2}', data)                
                    if matcheds:
                        split_data = data.split()
                        if split_data[facility_idx] == 'kern':
                            split_data[server_idx] += split_data[level_idx]
                            del split_data[level_idx]
                        filtered_list.append({
                            "TimeStamp": split_data[timestamp_idx],
                            "Facility": split_data[facility_idx],
                            "Host": split_data[host_idx],
                            "Server": split_data[server_idx],
                            "Level": split_data[level_idx],
                            "Message": " ".join(split_data[msg_idx:])
                        })         
                # 데이타프레임 생성
                df = pd.DataFrame(filtered_list)
                # 데이터 프레임을 엑셀로 변환
                df.to_excel(file_path, index=False)
                # 워크북 객체 생성
                workbook = load_workbook(filename=file_path)
                # 시트 활성화
                sheet = workbook.active
                # 테두리 적용
                for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
                    for idx, cell in enumerate(row):
                        cell.border = openpyxl.styles.Border(
                            left = openpyxl.styles.Side(border_style="thin"),
                            right = openpyxl.styles.Side(border_style="thin"),
                            top = openpyxl.styles.Side(border_style="thin"),
                            bottom = openpyxl.styles.Side(border_style="thin")
                        )
                        # 가운데 정렬
                        if idx != 5:
                            cell.alignment = Alignment(horizontal='center', vertical='center')

                # 크기 조정
                for column in sheet.columns:
                    max_length = 0
                    column = [cell for cell in column]
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = max_length + 2
                    sheet.column_dimensions[openpyxl.utils.get_column_letter(column[0].column)].width = adjusted_width

                # 변경 내용 저장
                workbook.save(file_path)
                is_success = True # 데이터 생성 여부
            else:
                df = {}
                is_pass = False
                is_success = True
            
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(filtered_list),
                'is_pass': is_pass,  # 점검 필요 여부
                'err_msg': err_msg,
                'err_flag': False
                }

            return result
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': df,
                'is_pass': is_pass, 
                'err_msg': err_msg,
                'err_flag': True
                }
            return result
    def make_report_dns(self, data, file_path, option='default', connection_info=False):        
        try:                    
            # 파일 경로 생성
            directory_path, file_name = os.path.split(file_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)            
            
            # 접속 실패
            if connection_info.get("is_connected") == False or connection_info.get("is_active") == False:                
                try:
                    # 실패 정보 보고서 생성
                    df = pd.DataFrame([connection_info])
                    make_excel(df, file_path)                

                    result = {
                    'file_path': file_path,
                    'is_success': True, 
                    'data': json.dumps(connection_info, ensure_ascii=False),
                    'is_pass': True if connection_info.get("is_active") == False else False,
                    'err_msg': connection_info.get("err_msg"),
                    'err_flag': False if connection_info.get("is_active") == False else True
                    }

                    return result
                except Exception as e:
                    return e

            # 작업 결과 변수 설정
            is_pass = True

            # err_msg 변수 설정
            err_msg = ""

            # 실패 키워드 리스트
            fail_keywords = ['WARNING', 'FAILED'] # 'INACTIVE'] << only for debug

            # 서비스 상태 점검 컬럼 정보 순서 설정
            col_list = ['grid_member_name', 'service', 'description', 'status']
            # option이 DNS 인 경우 예외처리
            if option in ['dns', 'DNS']:
                # 빈 데이터 프레임 생성
                df = pd.DataFrame()
                dfs = []
                # 원하는 컬럼 리스트
                selected_columns = ['grid_member_name', 'ha_status', 'service', 'description', 'status']
                
                for item in data:
                    if "service_status" in item:
                        service_status = item.pop("service_status")
                        for service in service_status:
                            row = item.copy()
                            row.update(service)
                            df = pd.DataFrame(row, index=[0])                        
                            dfs.append(df)
                    else:
                        df = pd.DataFrame(row, index=[0])
                        dfs.append(df)            
                df = pd.concat(dfs, ignore_index=True) 
                df = df[selected_columns] 
                # dict_list = df.to_dict(orient='records')  
                
            else:
                df = pd.DataFrame(data) 
                # 열 순서 변경                
                df = df[col_list]

            # 데이터 프레임을 엑셀로 변환
            df.to_excel(file_path, index=False)
            # dict_list = df.to_dict(orient='records')
            
            # 워크북 객체 생성
            workbook = load_workbook(filename=file_path)
            # 시트 활성화
            sheet = workbook.active
            # 테두리 적용
            for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=sheet.max_column):
                for cell in row:
                    cell.border = openpyxl.styles.Border(
                        left = openpyxl.styles.Side(border_style="thin"),
                        right = openpyxl.styles.Side(border_style="thin"),
                        top = openpyxl.styles.Side(border_style="thin"),
                        bottom = openpyxl.styles.Side(border_style="thin")
                    )
                    # 붉은색 글짜 표기
                    if any(keyword in str(cell.value) for keyword in fail_keywords):
                        cell.fill = PatternFill(start_color="FF0000", end_color="FF0000", fill_type="solid")
                        is_pass = False
                        err_msg= f"점검 항목 중, {fail_keywords} 항목이 존재 합니다. 보고서 내용을 확인해 주세요."
                    # 가운데 정렬
                    cell.alignment = Alignment(horizontal='center', vertical='center')

            # 크기 조정
            for column in sheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(cell.value)
                    except:
                        pass
                adjusted_width = max_length + 2
                sheet.column_dimensions[openpyxl.utils.get_column_letter(column[0].column)].width = adjusted_width

            # 변경 내용 저장
            workbook.save(file_path)
            is_success = True # 데이터 생성 여부
            json_string = df.to_json(orient='records')
            json_string = df.to_dict(orient='records')
            # new_json_string = json_string[1:-1]
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(json_string),
                'is_pass': is_pass,  # 점검 필요 여부
                'err_msg': err_msg,
                'err_flag': False
                }
            return result
                
        except Exception as e:
            if option == 'default':
                data = [{key: None for key in col_list}]
                is_pass = False
                is_success = False
                err_msg = e 
                result = {
                    'file_path': file_path,
                    'is_success': is_success, 
                    'data': json.dumps(data),
                    'is_pass': is_pass, 
                    'err_msg': err_msg,
                    'err_flag': False
                    }
            else:
                df = {}
                is_pass = False
                is_success = False
                err_msg = e 
                result = {
                    'file_path': file_path,
                    'is_success': is_success, 
                    'data': json.dumps(data),
                    'is_pass': is_pass, 
                    'err_msg': err_msg,
                    'err_flag': False
                    }
            return result

    # GSLB_Report
    def make_report_gslb(self, data_list, file_path, err_flag,columnString):
        
        pydebug = "Python Msg\n"

        try:
            # 파일 경로 생성
            if len(data_list) > 0:                
                directory_path, file_name = os.path.split(file_path)
                if not os.path.exists(directory_path):
                    os.makedirs(directory_path)

                # 변수 설정
                is_pass = True            
                err_msg = ""            
              
                """
                검증 정보 저장
                1) 작업 실행 전, 검증 플래그가 false이면 본작업 미실행
                2) 작업 실행 전, 검증 플래그가 true이면 본작업 실행
                """
                if err_flag:
                    data_list = [{**data, "검증 결과": "검증 실패"} for data in data_list]                    
                else:
                    data_list = [{**data, "검증 결과": "검증 성공"} for data in data_list]

                # 작업 성공 판단
                for data in data_list:
                    if data["err_flag"]: is_pass = False
                    if data["err_msg"] != "" and data["err_msg"] != {} : err_msg = data["err_msg"]
                
                # 데이타프레임 생성
                df = pd.DataFrame(data_list)
                # 보고서 생성
                make_excel_GSLB(df, file_path,columnString)
                 
                 # 작업 정상 수행 여부                 
                is_success = True
            else:
                err_msg = ""
                df = {}
                is_pass = True
                is_success = True
                
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': json.dumps(data_list, ensure_ascii=False), #.to_json(force_ascii=False),
                'is_pass': is_pass,  # 점검 성공 여부
                'err_msg': err_msg,
                'pydebug': pydebug 
                }

            return json.dumps(result, default=str, indent=2)
                
        except Exception as e:
            df = {}
            is_pass = False
            is_success = False
            err_msg = e 
            result = {
                'file_path': file_path,
                'is_success': is_success, 
                'data': df,
                'is_pass': is_pass, 
                'err_msg': err_msg,
                'pydebug': pydebug 
                }
            return json.dumps(result, default=str, indent=2)            
