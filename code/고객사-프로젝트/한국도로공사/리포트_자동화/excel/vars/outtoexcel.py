import pandas as pd
import re
import os



# /usr/bin/python3 ../vars/outtoexcel.py

with open('/APP/fap/ansible/projects/Out_TO_Excel/vars/fap_manager.txt','r') as file:
        lines = [line.strip() for line in file.readlines()]

#array count number reset
temp_num=-1

#line count array
new_array = [0]*len(lines)

for string in lines:
        temp_num=temp_num+1
        if 'ok' in string:
#               print(lines[temp_num])
                temp_str=lines[temp_num].split(":")[1].strip()
                ip_address=temp_str.replace("[","").replace("]","").replace("=","").replace(">","").replace(" ","")
                print(ip_address)
                new_array[temp_num]=1
        else:
                continue

#배열 넘버 초기화
temp_num=-1

df = pd.DataFrame(new_array)
df.to_excel("output.xlsx",index=False,header=False)

