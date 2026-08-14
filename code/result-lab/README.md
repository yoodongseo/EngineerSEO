# result_lab 코드 포트폴리오

이 폴더는 Ansible 기반 자체 솔루션 시스템 개발 과정에서 작업한 코드 중, 포트폴리오에서 보여주기 좋은 단위만 정리한 공간입니다.

원본 전체 작업 폴더를 그대로 올린 것이 아니라, 공개 저장소에 올리기 애매한 결과 파일, 샘플 로그, Excel/PDF, zip, 고객사 원본 자료는 제외했습니다.

## 구조

```text
result-lab/
  register-handler/
    module/
    core/
  preventive-check/
    ansible/
    rules/
    vars/
  security-check/
    rules/
    vars/
  replication-check/
    rules/
    vars/
```

## 구성 설명

### register-handler

Ansible 실행 결과를 받아 공통으로 검증하고, `report_type`과 `rule_key` 기준으로 점검 rule을 호출한 뒤, 최종 payload를 만드는 공통 처리 구조입니다.

주요 파일:

- `module/register_handler.py`
- `module/register_handler_local.py`
- `core/command_check.py`
- `core/result_build.py`
- `core/rule_result.py`
- `core/rules/__init__.py`

### preventive-check

서버 예방점검 자동화 코드입니다.

- rule 파일: 21개
- 대상 OS: Linux, Linux5, Solaris, AIX, HP-UX, Windows
- 주요 항목: CPU, Memory, Disk, Filesystem, Kernel Parameter, System Log, Cluster, Network, HBA 등

### security-check

보안점검 자동화 코드입니다.

- rule 파일: 19개
- 대상: 서버 보안점검 및 네트워크 장비 보안점검
- 네트워크 벤더 vars: Cisco, Arista, Citrix, Piolink, Alteon L4
- 주요 항목: 계정/권한, 디폴트 계정, 비밀번호, 평문 서비스, 원격접속, 랜섬웨어 포트, Directed-broadcast, Mask-reply, Source Routing, 미사용 인터페이스 등

### replication-check

복제 상태 점검 자동화 코드입니다.

- rule 파일: 4개
- 대상 벤더: NetApp, HPE, IBM
- 복제 관계의 before/after 데이터를 payload로 정리하는 구조를 포함합니다.

## prompt 코드 관련 메모

prompt custom module 코드는 `result_lab` 밖의 별도 작업 경로에 있었고, 이 저장소에서는 `code/prompt` 아래에 정리했습니다.

추후 `FAP_VARS/리팩토링` 코드도 경로가 확정되면 `code/fap-vars-refactoring` 아래에 추가할 예정입니다.
