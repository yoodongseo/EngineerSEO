# 금융권 네트워크 L4/L7(F5) 프로비저닝 자동화

## 📖 Background Story
대형 금융권 인프라 환경에서는 매주, 매달 수십 개의 새로운 서비스가 오픈되고 닫힙니다. 이때마다 네트워크 엔지니어들은 F5 로드밸런서(LB) 장비에 접속해 Virtual Server를 뚫고, Pool을 만들고, Pool Member를 연결하는 지루하고 위험한 작업을 반복합니다.

만약 작업자가 IP를 하나 잘못 입력한다면? 대규모 서비스 장애로 직결됩니다.
단순 서버 점검 자동화를 성공적으로 안착시킨 후, 저는 **"가장 휴먼 에러가 치명적인 네트워크 장비 프로비저닝(설정) 작업이야말로 자동화가 필요하다"**고 판단했습니다.

## ⚙️ Architecture & Features

이 코드는 F5 장비의 단순 상태 값을 읽어오는 데 그치지 않고, 실제로 **L4/L7 네트워크 아키텍처를 동적으로 생성(Create)하고 삭제(Delete)**하는 프로비저닝 스크립트입니다.

### 1. F5 리소스 생애주기 관리
- **Virtual Server:** IP, Port, Protocol을 받아 가상 서버 생성 및 삭제 (`add_vserver.yml`, `del_vserver.yml`)
- **Pool & Member:** 로드밸런싱 대상이 될 풀 생성 및 실제 서버 노드 연결 (`add_pool.yml`, `add_poolmember.yml`)
- **Monitor:** Health Check 모니터링 정책 동적 할당 (`add_monitor.yml`)

### 2. API 기반의 정교한 제어
- 전통적인 CLI 스크래핑 방식이 아닌, REST API 또는 F5 전용 모듈 기반으로 설계하여 상태(State)의 정확성을 보장합니다.
- 변수 파일(`vars/COMPANY-DEV_vars.yml` 등)에 타겟 정보만 정의해 두면, 버튼 클릭 한 번으로 무중단 서비스 배포 라인이 완성됩니다.

## 📂 Directory Structure

```text
금융권-네트워크-LB-자동화/
└── f5-lb-automation/
    ├── playbooks/       # GSLB 등록 등 상위 플레이북
    ├── tasks/           # vserver, pool, monitor 생성 및 삭제 task
    └── vars/            # 고객사/환경(DEV, OP)별 환경 변수 정의
```

## 🚀 The Impact
기존에는 네트워크 엔지니어가 신청서를 보고 수동으로 수십 줄의 CLI를 타이핑해야 했지만, 이제는 포탈(사용자 인터페이스)에서 넘어오는 변수를 받아 즉각적으로(Idempotent하게) F5 설정을 반영합니다. 휴먼 에러율은 0%로 수렴하게 되었습니다.
