앤서블(Ansible) 프로젝트가 커질수록 잘 짜인 폴더 구조는 **Execution Harness**와 **Operation Harness**의 효율성을 결정짓는 핵심 요소가 됩니다. 앤서블 공식 문서의 권장 사항과 실무 베스트 프랙티스를 결합한 구조를 Markdown 형식으로 정리해 드립니다.

---

## 📂 Ansible 프로젝트 표준 디렉토리 구조

이 구조는 재사용성과 확장성을 고려한 **Best Practice** 설계입니다.

```text
ansible-project/
├── ansible.cfg            # 앤서블 설정 파일 (고정 설정 등)
├── inventory/             # 환경별 인벤토리 관리
│   ├── production.ini     # 운영 환경 서버 리스트
│   ├── staging.ini        # 스테이징 환경 서버 리스트
│   └── group_vars/        # 그룹별 변수 (all.yml, webservers.yml 등)
│   └── host_vars/         # 개별 호스트별 변수
├── library/               # (선택) 커스텀 모듈
├── filter_plugins/        # (선택) 커스텀 Jinja2 필터
├── playbooks/             # 실행 단위 플레이북 모음
│   ├── site.yml           # 전체 인프라 배포 메인 플레이북
│   ├── webservers.yml     # 웹 서버 전용 플레이북
│   └── dbservers.yml      # DB 서버 전용 플레이북
├── roles/                 # 재사용 가능한 역할(Role) 단위
│   └── common/            # 공통 설정 역할
│       ├── tasks/         # 실제 실행될 작업 (main.yml)
│       ├── handlers/      # 서비스 재시작 등 이벤트 처리 (main.yml)
│       ├── templates/     # Jinja2 템플릿 파일 (*.j2)
│       ├── files/         # 그대로 복사할 정적 파일
│       ├── vars/          # 우선순위 높은 변수
│       ├── defaults/      # 기본값 변수 (가장 낮은 우선순위)
│       └── meta/          # 역할 의존성 정의
└── requirements.yml       # 외부 Role(Ansible Galaxy) 정의 파일
```

---

## 📝 주요 구성 요소 설명

| 항목              | 용도 및 설명                                              | 하네스 연결 포인트                       |
| :---------------- | :-------------------------------------------------------- | :--------------------------------------- |
| **`ansible.cfg`** | 로그 경로, SSH 타임아웃, 인벤토리 경로 등을 정의합니다.   | **Execution:** 실행 환경 최적화          |
| **`inventory/`**  | 서버 정보를 환경별로 분리하여 관리합니다.                 | **Operation:** 권한별 환경 접근 제어     |
| **`playbooks/`**  | 어떤 호스트에 어떤 Role을 적용할지 결정하는 진입점입니다. | **Operation:** 템플릿 실행의 기준        |
| **`roles/`**      | 기능을 컴포넌트화하여 관리합니다. (예: `nginx`, `docker`) | **Observation:** Task 단위 이벤트 추적   |
| **`group_vars/`** | DB 암호, API 키 등 환경별 변수를 정의합니다.              | **Security:** Vault를 이용한 암호화 관리 |

---

## 💡 하네스 엔지니어링을 위한 관리 팁

### 1. 멱등성 유지 (Control Harness)

`roles` 내부의 `tasks`를 작성할 때, 여러 번 실행해도 결과가 같아야 합니다. 이는 **Retry** 로직이 동작할 때 시스템 상태가 꼬이는 것을 방지합니다.

### 2. 가시성 확보 (Observation Harness)

`tasks` 작성 시 `name` 속성을 명확하게 작성하세요.

- **Bad:** `- name: install pkg`
- **Good:** `- name: [Nginx] 최신 버전의 패키지가 설치되어 있는지 확인`
  이렇게 하면 실시간 로그 수집 시 어떤 구간에서 지연이 발생하는지 한눈에 알 수 있습니다.

### 3. 변수 분리 (Operation Harness)

민감한 정보는 `group_vars/all.yml`에 직접 적지 말고, **Ansible Vault**를 사용하여 암호화하세요. 하네스 솔루션 UI에서는 변수 입력창만 제공하고, 백엔드에서 Vault 패스워드를 주입하는 방식이 안전합니다.

---

이 폴더 체계를 기반으로 도커 컨테이너 내에서 `ansible-playbook -i inventory/staging.ini playbooks/site.yml` 명령어를 실행하도록 자동화 로직을 구성하시면 됩니다.

혹시 특정 **Role(역할)** 내부에 들어갈 세부 코드 예시도 필요하신가요?
