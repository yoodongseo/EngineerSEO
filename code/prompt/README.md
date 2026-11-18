# prompt 코드 포트폴리오

이 폴더는 Ansible `command`, `shell`, `raw`처럼 단순 명령 실행만 하는 방식에서 벗어나, 원격 장비 세션의 prompt를 학습/판단해 명령 종료 시점을 안정적으로 잡기 위한 custom module 코드입니다.

## 왜 만들었는지

서버나 네트워크 장비에서 명령을 실행할 때 단순 timeout 기준으로 결과를 자르면, 출력이 늦게 도착하거나 prompt가 바뀌는 상황에서 결과가 잘리거나 명령 종료를 잘못 판단할 수 있습니다.

특히 아래와 같은 경우에는 prompt 상태를 보고 명령 종료를 판단하는 구조가 필요했습니다.

- SSH/Telnet 기반 원격 세션 유지
- 서버와 네트워크 장비의 인증 방식 차이
- `su`, `sudo`, `enable` 같은 권한 상승
- `sqlplus`, `rman` 같은 application prompt 진입
- 명령 실행 후 prompt가 바뀌거나 원래 prompt로 복귀하는 상황

## 구조

```text
prompt/
  PROMPT_DESIGN.md
  modules/
    prompt.py
  module_utils/
    fap_client_base_prompt.py
    fap_client_ssh_prompt.py
    fap_client_telnet_prompt.py
    fap_common_prompt.py
  examples/
    playbook.yml
    vars.yml
    fap_vars_example.yml
```

## 주요 파일

- `modules/prompt.py`: Ansible custom module 진입점
- `module_utils/fap_client_base_prompt.py`: prompt 학습/판정 공통 로직
- `module_utils/fap_client_ssh_prompt.py`: SSH 연결 및 인증 처리
- `module_utils/fap_client_telnet_prompt.py`: Telnet 연결 및 인증 처리
- `module_utils/fap_common_prompt.py`: 공통 유틸
- `PROMPT_DESIGN.md`: 설계 메모

## 주요 기능

- SSH/Telnet 기반 명령 실행
- 서버/네트워크 장비 인증 방식 분기
- prompt 복귀 감지 기반 명령 종료 판단
- 권한 상승 처리
- application prompt 후보 감지
- 명령별 `debug_info` 제공
- 출력 본문과 prompt/debug 정보 분리

## 공개용 정리 기준

원본 경로의 아래 파일은 공개 저장소에 포함하지 않았습니다.

- `*.log`
- `__pycache__/`
- `*.pyc`

예제의 사설 IP는 문서용 대역인 `192.0.2.10`으로 치환했습니다.
