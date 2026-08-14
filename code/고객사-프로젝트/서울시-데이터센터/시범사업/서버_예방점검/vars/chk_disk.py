import re
import json

def parse_disk_status_Windows(output):
    
    # 정규 표현식을 사용하여 각 드라이브의 정보를 분리
    pattern = r"DriveLetter\s+:\s*(\w)\s+HealthStatus\s+:\s*(\w+)\s+OperationalStatus\s+:\s*(\w+)\s+SizeRemaining\s+:\s*(\d+)\s+Size\s+:\s*(\d+)"
    matches = re.findall(pattern, output)

    
    # 결과를 딕셔너리 형식으로 변환
    drives = []
    for match in matches:
        # 사용률 계산
        used_size = float(match[4].strip()) - float(match[3].strip())
        usage_percentage = 0 
        if used_size != 0:                       
            usage_percentage = (used_size / float(match[4].strip())) * 100
        
        drivesinfo ={
                "DriveLetter": match[0],
                "HealthStatus": match[1],
                "OperationalStatus": match[2],
                "SizeRemaining": int(match[3]),
                "Size": int(match[4]),
                "UsagePercentage": round(usage_percentage, 2)}   
        
        drives.append(drivesinfo)

    return drives




    # 파싱을 위해 줄 단위로 나눔
    # lines = output.strip().splitlines()

    # 데이터의 헤더와 구분선 제거
    lines = output.strip().split("\n")[2:]

    # return lines

    # 각 라인을 파싱하여 딕셔너리로 변환
    result = []
    for line in lines:
        # 최소 1 개 이상의 연속된 공백으로 데이터를 분리
        parts = re.split(r'\s{1,}', line.strip())

        # DriveLetter가 없는 경우 감지
        if len(parts) == 3 and not re.match(r'^[A-Z]:?$', parts[0]):
            # DriveLetter 자리에 빈 문자열을 삽입
            parts.insert(0, "")
        
        # # FriendlyName이 없는 경우 감지 (DriveLetter가 비어 있고 다음 값이 FileSystemType인 경우)
        # if len(parts) >= 7 and not parts[1].strip() and re.match(r'^(NTFS|FAT32|exFAT|CD-ROM|Unknown)$', parts[2]):
        #     parts.insert(1, "")  # FriendlyName 자리에 빈 문자열을 삽입

        # OperationalStatus와 SizeRemaining을 분리하기 위해 추가 처리
        # if len(parts) >= 6:
        #     last_part = parts[-1]
        #     second_last_part = parts[-2]

        #     # 두 항목이 크기 형식인 경우
        #     if re.match(r'^\d+(\.\d+)?\s(GB|MB)$', last_part) and re.match(r'^\d+(\.\d+)?\s(GB|MB)$', second_last_part):
        #         # OperationalStatus에 잘못된 데이터가 들어간 경우 수정
        #         parts[-2] = second_last_part
        #         parts[-1] = last_part
        #     elif len(parts) == 8:
        #         # 경우에 따라 OperationalStatus와 SizeRemaining이 밀린 경우 처리
        #         if re.match(r'^\d+(\.\d+)?\s(GB|MB)$', parts[-2]):
        #             parts[-1] = parts[-2]  # 마지막 항목으로 이동
        #             parts[-2] = ""  # 빈 문자열로 설정

        # 열의 개수가 8개가 아닌 경우 빈 문자열로 채워서 보정
        while len(parts) < 4:
            parts.append("")


        # 사용률 계산
        used_size = float(parts[3].strip()) - float(parts[2].strip())
        usage_percentage = 0 
        if used_size != 0:                       
            usage_percentage = (used_size / float(parts[3].strip())) * 100
        
        # if parts[0].strip() != "":
        # 각 열의 값을 딕셔너리로 매핑
        volume_info = {
            "DriveLetter": parts[0].strip(),
            # "FriendlyName": parts[1].strip(),
            # "FileSystemType": parts[2].strip(),
            # "DriveType": parts[3].strip(),
            "HealthStatus": parts[1].strip(),
            # "OperationalStatus": parts[2].strip(),
            "SizeRemaining": parts[2].strip(),
            "Size": parts[3].strip(),
            "UsagePercentage": round(usage_percentage, 2)
        }
        result.append(volume_info)


    return result







    # 데이터가 있는 줄들을 추출 (헤더와 구분선 제외)
    # drive_data_lines = lines[3:]

    # 결과를 저장할 리스트


    
    # result = []

    # for line in lines[2:]:  # 헤더와 구분선을 건너뛰고 데이터만 가져옴
    #     values = line.split()
    #     # 각 행의 값을 적절히 정렬 (여유 공간이 있는 부분을 처리)
    #     if len(values) > 0:
    #         # DriveLetter, FriendlyName, FileSystemType, DriveType, HealthStatus, OperationalStatus
            
    #         # size_remaining = float(values[6].replace("GB", "").replace(",", "").strip())  # 남은 공간 (GB 단위)
    #         # total_size = float(values[7].replace("GB", "").replace(",", "").strip())  # 총 공간 (GB 단위)
            
    #         drive_info = {
    #             "DriveLetter": values[0].strip(),
    #             "FriendlyName": values[1].strip(),
    #             "FileSystemType": values[2].strip(),
    #             "DriveType": values[3].strip(),
    #             "HealthStatus": values[4].strip(),
    #             "OperationalStatus": values[5].strip(),
    #             "SizeRemaining": " ".join(values[6:8]).strip(),  # 남은 용량과 단위를 합침
    #             "Size": " ".join(values[8:10]).strip()  # 전체 크기와 단위를 합침
    #         }
    #     result.append(drive_info)

    # return result

    # drive_info = []
    
    # # 각 드라이브 정보를 파싱
    # for line in drive_data_lines:
    #     parts = line.split()
        
    #     len = len(parts) - 1

    #     # 필요한 데이터 추출
    #     if(len==7)
    #     drive_letter = parts[0]  # 드라이브 문자
    #     friendly_name = parts[1]  # Friendly Name
    #     health_status = parts[4]  # Health Status
    #     operational_status = parts[5]  # Operational Status
    #     size_remaining = float(parts[6].replace("GB", "").replace(",", "").strip())  # 남은 공간 (GB 단위)
    #     total_size = float(parts[8].replace("GB", "").replace(",", "").strip())  # 총 공간 (GB 단위)


    #     # 사용률 계산
    #     used_size = total_size - size_remaining
    #     usage_percentage = (used_size / total_size) * 100
        
    #     # 드라이브 정보 저장
    #     drive_info.append({            
    #         "DriveLetter": drive_letter,
    #         "FriendlyName": friendly_name,
    #         "HealthStatus": health_status,
    #         "OperationalStatus": operational_status,
    #         "SizeRemaining_GB": size_remaining,
    #         "TotalSize_GB": total_size,
    #         "UsagePercentage": round(usage_percentage, 2)
    #     })

    # drive_info.append({ 
    #     "parts": lines
    # })
        
    # return drive_info

    # 결과 출력
    # for drive in drive_info:
    #     print(f"Drive {drive['DriveLetter']} ({drive['FriendlyName']})")
    #     print(f"  Health Status: {drive['HealthStatus']}")
    #     print(f"  Operational Status: {drive['OperationalStatus']}")
    #     print(f"  Total Size: {drive['TotalSize_GB']} GB")
    #     print(f"  Size Remaining: {drive['SizeRemaining_GB']} GB")
    #     print(f"  Usage Percentage: {drive['UsagePercentage']}%\n")



# # PowerShell 결과 문자열
# output = """
# DriveLetter FriendlyName FileSystemType DriveType HealthStatus OperationalStatus SizeRemaining     Size
# ----------- ------------ -------------- --------- ------------ ----------------- -------------     ----
# C           RTNET        NTFS           Fixed     Healthy      OK                     36.41 GB 140.7 GB
# D           Work         NTFS           Fixed     Healthy      OK                     37.43 GB 97.66 GB
# """

# # 과기대 결과
# [
#   {
#     "parts": [
#       "C                        NTFS           Fixed     Healthy      OK                      9.93 GB 49.46 GB",
#       "E                        Unknown        CD-ROM    Healthy      Unknown                     0 B      0 B",
#       "                         NTFS           Fixed     Healthy      OK                     83.38 MB   450 MB",
#       "D                        Unknown        CD-ROM    Healthy      Unknown                     0 B      0 B"
#     ]
#   }
# ]



# disk_usage = parse_disk_status_Windows(output)
# print(disk_usage)  