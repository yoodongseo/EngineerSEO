import re

def parse_memory_usage(output):
    # Regex pattern to match the memory usage lines
    pattern = r"(\w+ Pool Total):\s+(\d+)\s+Used:\s+(\d+)\s+Free:\s+(\d+)"
    
    # Find all matches in the output
    matches = re.findall(pattern, output)
    
    usage_info = {}
    
    # Calculate usage percentage for each pool
    for match in matches:
        pool_name = match[0]
        total_memory = int(match[1])
        used_memory = int(match[2])
        
        usage_percentage = (used_memory / total_memory) * 100
        usage_info[pool_name] = usage_percentage
    
    return usage_info

# Example output from the `show processes memory` command
# cisco_output = """
# Processor Pool Total:  14446356 Used:   6786612 Free:   7669744
# I/O Pool Total:        8388608 Used:   202508 Free:   8186100
# PID TTY  Allocated      Freed    Holding    Getbufs    Retbufs Process
# 1   0          304        136      70408          0          0 Load Meter
# 2   0          168          0      59472          0          0 Exec
# """

# # Parse the output and get usage percentages
# usage_info = parse_memory_usage(cisco_output)

# # Check if any pool usage exceeds 70%
# for pool, usage in usage_info.items():
#     if usage > 70:        
#         print(f"{pool} usage is above 70%: {usage:.2f}%")
#     else:
#         print(f"{pool} usage is below 70%: {usage:.2f}%")


def parse_memory_usage_Windows(output):


# 파싱하기 위해 줄 단위로 나눔
    lines = output.strip().splitlines()

    # 데이터가 있는 마지막 줄에서 값을 추출
    memory_values = lines[-1].split()

    # TotalVisibleMemorySize와 FreePhysicalMemory 값을 추출하고 정수형으로 변환
    total_memory_kb = int(memory_values[0])  
    free_memory_kb = int(memory_values[1])   

    # 사용 중인 메모리 계산
    used_memory_kb = total_memory_kb - free_memory_kb

    # 메모리 사용률 계산 (퍼센트 단위)
    memory_usage_percentage = (used_memory_kb / total_memory_kb) * 100

    
    return memory_usage_percentage
    
    # # 결과 출력
    # print(f"Total Memory: {total_memory_kb / 1024:.2f} MB")
    # print(f"Free Memory: {free_memory_kb / 1024:.2f} MB")
    # print(f"Used Memory: {used_memory_kb / 1024:.2f} MB")
    # print(f"Memory Usage: {memory_usage_percentage:.2f}%")



# # Example output from the `Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory` command
# # # PowerShell 결과 문자열
# powershell_output = """
# TotalVisibleMemorySize FreePhysicalMemory
# ---------------------- ------------------
#                8105416             917572
# """

# # Parse the output and get usage percentages
# memory_usage = parse_memory_usage_Windows(powershell_output)
# print(f" 메모리 사용률: {memory_usage:.2f}%")  
    