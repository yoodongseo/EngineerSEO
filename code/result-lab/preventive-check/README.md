# preventive-check

서버 예방점검 자동화 코드입니다.

## 대상

- Linux
- Linux5
- Solaris
- AIX
- HP-UX
- Windows

## 구성

```text
preventive-check/
  ansible/
  rules/
  vars/
```

- `ansible/`: 로컬 검증용 playbook/task 예시
- `rules/`: 예방점검 판정 로직
- `vars/`: OS별 점검 항목과 명령어 정의

## 자동화 항목

- CPU 사용률
- CPU Core
- Memory 사용률
- Memory Scan
- Paging Space
- Filesystem 사용률
- Disk Swap 사용률
- Disk 이중화
- Device 상태
- Disk 상태
- Inode 사용률
- Kernel Parameter
- System Log
- Cluster 상태
- Shared Volume 상태
- Network Link 상태
- NIC 이중화
- Ping Loss
- Path 이중화
- HBA 연결 상태

## 포트폴리오 포인트

- OS별 명령어와 출력 형식 차이를 rule/vars 구조로 분리
- 점검 기준, 판정 결과, 상세 내용을 payload로 표준화
- Linux5 같은 레거시 환경 fallback 명령을 별도 vars로 관리
