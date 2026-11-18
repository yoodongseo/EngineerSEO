
---

## 1. Ansible Playbook 키워드 및 활용 예제



### Play 및 Task 키워드 개요와 실무 예시
Playbook은 대상 호스트 지정부터 세부 작업 제어까지 다양한 키워드를 조합하여 구성됩니다.

* **기본 웹 서버 설정**: `hosts`, `become`, `vars` 등을 사용하여 권한 상승과 변수를 정의하고, `notify`와 `handlers`를 통해 상태 변경 시에만 서비스를 재시작하도록 설계합니다.
* **조건부 실행과 루프**: `loop`를 사용하여 여러 사용자를 생성하거나, `register`로 명령 결과를 저장한 뒤 `when` 조건을 사용하여 특정 상황(예: 리턴 코드 확인)에서만 작업을 수행합니다.
* **성능 및 배포 최적화**:
    * `serial`: 한 번에 작업을 수행할 호스트 배치를 조절합니다. (예: `serial: "20%"`)
    * `strategy`: `linear`(순차) 또는 `free` 전략을 선택합니다.
    * `delegate_to`: 특정 작업을 다른 서버(예: 로드밸런서)에서 실행하도록 위임합니다.
    * `async` & `poll`: 대용량 다운로드 등 오래 걸리는 작업을 비동기로 처리합니다.

### 상세 제어 예제 코드
```yaml
- name: "대규모 서버 그룹 업데이트 및 고급 제어"
  hosts: all
  gather_facts: true              # 실행 전 정보 수집 활성화
  any_errors_fatal: true          # 한 대라도 실패 시 전체 중단
  serial: "20%"                   # 한 번에 전체의 20%씩 작업 진행
  
  vars_files:                     # 외부 변수 파일 로드
    - "vars/common_config.yml"
    - "vars/{{ ansible_os_family }}.yml"

  pre_tasks:                      # Role 실행 전 선행 작업
    - name: "업데이트 시작 로그 기록"
      ansible.builtin.raw: "logger 'Ansible update started'"

  tasks:
    - name: "서비스 응답 대기 (재시도 로직)"
      ansible.builtin.uri:
        url: "http://localhost:8080"
      register: result             # 결과를 변수에 저장
      until: "result.status == 200" # 조건 충족 시까지 반복
      retries: 5                   # 최대 5번 재시도
      delay: 10                    # 재시도 사이 10초 대기

    - name: "사용자 정의 상태 판단"
      ansible.builtin.command: "/usr/bin/custom_check.sh"
      register: check_out
      changed_when: "'NEW_DATA' in check_out.stdout" # 특정 문구 포함 시 '변경됨'으로 간주
      failed_when: "check_out.rc != 0 and check_out.rc != 2" # 리턴코드가 0이나 2가 아니면 실패

    - name: "접속 불가 무시 작업"
      ansible.builtin.ping:
      ignore_unreachable: yes      # 서버 다운 시에도 에러 처리 안 함
```

---

## 2. Blocks를 활용한 그룹화 및 예외 처리

### Block 기능 및 지시어 상속
Block은 여러 작업을 논리적으로 묶어 공통 설정(`when`, `become` 등)을 상속시키거나, 프로그래밍의 try-catch와 유사하게 오류를 처리합니다.

* **rescue**: `block` 내 작업 실패 시에만 실행되는 복구 섹션입니다.
* **always**: 성공/실패 여부와 관계없이 마지막에 반드시 실행됩니다.
* **특수 변수**: `ansible_failed_task.name`으로 실패한 작업을 확인하고, `ansible_failed_result.msg`로 에러 원인을 분석할 수 있습니다.

### 종합 예제: DB 설정 및 트랜잭션 관리
```yaml
- name: "고급 DB 설정 및 예외 처리 시나리오"
  hosts: db_servers
  tasks:
    - block:
        - name: "기존 데이터베이스 백업"
          ansible.builtin.shell: "/usr/bin/mysqldump my_db > /tmp/db_backup.sql"
          notify: "백업 로그 기록"

        - name: "새로운 스키마 적용"
          ansible.builtin.command: "/usr/bin/mysql my_db < /opt/app/new_schema.sql"

        - name: "의도적 에러 발생"
          ansible.builtin.command: "/bin/false"

      become: true                 # 블록 내 지시어 상속
      when: ansible_facts['os_family'] == "Debian"

      rescue:
        - name: "실패 정보 출력 (특수 변수 활용)"
          ansible.builtin.debug:
            msg: "실패 작업: {{ ansible_failed_task.name }}, 사유: {{ ansible_failed_result.msg }}"

        - name: "핸들러 즉시 실행"
          ansible.builtin.meta: flush_handlers # 에러 전 성공 작업의 핸들러 처리

        - name: "데이터베이스 롤백"
          ansible.builtin.shell: "/usr/bin/mysql my_db < /tmp/db_backup.sql"
          when: "'스키마 적용' in ansible_failed_task.name"

      always:
        - name: "임시 파일 정리"
          ansible.builtin.file:
            path: "/tmp/db_backup.sql"
            state: absent
```

---

## 3. Roles 구성 및 고급 활용



### 역할(Role) 구조 및 호출 방식
Role은 관련 변수, 작업, 템플릿 등을 독립된 디렉토리 구조로 묶어 재사용성을 높입니다.

* **표준 구조**: `tasks/`, `handlers/`, `defaults/`, `vars/`, `templates/`, `meta/` 디렉토리를 사용합니다.
* **정적 호출 (`import_role`)**: 플레이북 파싱 시점에 역할이 포함되어 속도가 빠릅니다.
* **동적 호출 (`include_role`)**: 실행 시점에 역할이 결정되므로 루프(`loop`)나 조건문과 조합할 수 있습니다.
* **고급 옵션**:
    * `tasks_from`: `main.yml` 대신 특정 파일을 실행합니다.
    * `public: yes`: 역할 내 변수를 이후 작업에서도 사용 가능하게 노출합니다.
    * `allow_duplicates: true`: 동일 플레이 내에서 역할의 중복 실행을 허용합니다. (meta 설정)

### 상세 활용 예제
```yaml
# meta/argument_specs.yml: 역할 인수 검증
argument_specs:
  main:
    options:
      backup_interval:
        type: "str"
        choices: ["daily", "weekly"]
        default: "daily"
      backup_targets:
        type: "list"
        required: true

# playbook.yml: 역할 호출 상세 예제
- name: "역할 파일 커스터마이징 및 변수 전파"
  hosts: app_servers
  tasks:
    - name: "동적 로드: 특정 설정 파일만 실행"
      ansible.builtin.include_role:
        name: common
        tasks_from: security_setup.yml  # 특정 태스크 파일 실행
        public: yes                     # 이후 태스크에서도 변수 사용 가능
      become: yes
      become_user: app_admin            # 역할 전체를 특정 사용자로 실행

    - name: "핸들러 별도 로드 예제"
      ansible.builtin.include_role:
        name: nginx_config
        handlers_from: reload_handlers.yml # 별도 핸들러 파일 로드
```