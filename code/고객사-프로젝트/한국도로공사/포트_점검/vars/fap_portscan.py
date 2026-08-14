# -*- coding: utf-8 -*-

# File: fap_portscan.py
# Descripton: Scan ports
# Version: 1.0.0
# Generated: Nov 714, 2023
# Author: Ted Kim
# Copyright: RTNET Corporation

import nmap
import os
import sys
import socket
import threading
import time


# 결과 저장 변수 정의
results = []
results_lock = threading.Lock()

# 포트 스캔 함수 정의
def port_scan(host, port, protocol):
    # 결과 저장 변수 전역 변수 처리
    global results

    try:
        # 소켓 생성
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if protocol == 'tcp' else socket.SOCK_DGRAM)
        sock.settimeout(1)
        
        # 포트 스캔
        _conn = sock.connect_ex((host, port))
        # 포트가 open일 경우 nmap 스캔 처리
        if _conn == 0:
            scan_result = nmap_scan(host, port, protocol)
            print(f'{protocol.upper()} {port}\t{scan_result}')
            with results_lock:
                results.append([protocol.upper(), port, scan_result])
        sock.close()

    except Exception as e:
        print(f"{protocol.upper()} 포트 {port} 상태: 에러 ({str(e)})")

# nmap 포트 스캔 함수 정의
def nmap_scan(host, port, protocol):
    # nmap 스캔 인스턴스 생성
    nm = nmap.PortScanner()
    # TCP, UDP 경우 scan_type 정의
    protocol_type = '-sT' if protocol == 'tcp' else '-sU'
    argv = f'-p {port} --max-rtt-timeout 1000ms --max-retries 3 {protocol_type} -sV'
    nm.scan(host, arguments=argv)
    
    # 스캔 결과 출력
    for host in nm.all_hosts():
        if protocol in nm[host]:
            for port, result in nm[host][protocol].items():
                if result['state'] == 'open' and 'product' in result and 'version' in result:
                    scan_result = f"{result['name']}  {result['product']}  {result['version']}"
                    return scan_result

# 프로그램 시작
# # 시작 시간
# start_time = time.time()

mesg = """
사용방법:
fap_portscan.py host_ip
"""
# 대상 호스트 정의
if len(sys.argv) == 1 or len(sys.argv) > 2:
    print(mesg)
    exit()
else:
    host = sys.argv[1]

    # 스캔 프로토콜 정의
    scan_protocols = ('TCP',)
    # scan_protocols = ('TCP', 'UDP')

    # 포트 범위 설정
    start_port = 1
    end_port = 65535

    # 스레드 개수 설정
    num_threads = 50

    # 포트 스캔 스레드로 실행
    port_step = (end_port - start_port + 1) // num_threads
    threads = []
    for i in range(num_threads):
        start = start_port + i * port_step
        end = start + port_step - 1 if i < num_threads - 1 else end_port
        # TCP 스캔 스레드 생성
        if 'TCP' in scan_protocols:
            tcp_thread = threading.Thread(target=lambda s=start, e=end: [port_scan(host, port, 'tcp') for port in range(s, e + 1)])
            threads.append(tcp_thread)
            tcp_thread.start()
        # UDP 스캔 스레드 생성
        if 'UDP' in scan_protocols:
            udp_thread = threading.Thread(target=lambda s=start, e=end: [port_scan(host, port, 'udp') for port in range(s, e + 1)])
            threads.append(udp_thread)
            udp_thread.start()
    # 스레드 종료까지 대기
    for thread in threads:
        thread.join()

    # 포트 스캔 결과 출력
    if len(results) > 0:
        # Protocol로 정렬
        results = sorted(results, key=lambda x:x[0], reverse=False)
        # Port로 정렬
        results = sorted(results, key=lambda x:x[1], reverse=False)
        for r in results:
            print(f'{r[0]} {r[1]}\t{r[2]}')

    # # 소요 시간 출력
    # end_time = time.time()
    # elapsed_time = end_time - start_time
    # elaps_min = int(elapsed_time // 60)
    # elaps_sec = int(elapsed_time % 60)
    # print(f'running time: {elaps_min}:{elaps_sec}')

#
#
#