# Exec Command Prompt Design

## 목적

`prompt` 모듈은 Ansible `command`, `shell`, `raw`처럼 사용자는 명령만 넘기고, 내부적으로 세션 프롬프트를 학습/재학습해 명령 종료 시점을 안정적으로 판정하는 것을 목표로 한다.

이 모듈은 특히 아래 환경을 대상으로 한다.

- 원격 서버의 Python/OS 제약으로 기본 Ansible 모듈 사용이 어려운 환경
- SSH/Telnet 기반 세션 유지형 명령 실행
- `su`, `su -`, `sudo`, `sqlplus`, `rman` 등으로 세션 프롬프트가 바뀌는 환경

현재 구현에서는 장비/서버 모델명 분기보다, `target_type`으로 `server`/`network`를 구분해 SSH 인증 전략을 나눈다.

## 현재 합의된 핵심 원칙

1. 사용자에게 추가 메타데이터를 강요하지 않는다.
- `prompt_transition`, `expected_prompt` 같은 정보를 vars에 강제하지 않는다.
- 사용자는 기존처럼 command 목록만 정의한다.
- 단, SSH 인증 전략 분기를 위해 `target_type`(`server`/`network`)은 허용한다.

2. 프롬프트 판단은 실행 전/실행 후 두 단계 모두 필요하다.
- 실행 전: 현재 유효 프롬프트를 확보하고 기준점으로 저장
- 실행 후: 기존 프롬프트 복귀인지, 새로운 프롬프트 전환인지 판단

3. 프롬프트는 고정값이 아니라 상태값이다.
- 단일 `device_prompt`만 보는 것이 아니라 현재 세션 상태에 따라 바뀔 수 있다.
- shell prompt, 전환된 user prompt, application prompt를 모두 다룰 수 있어야 한다.

4. 상태 전환은 하드코딩보다 자동 재학습이 우선이다.
- `su`, `sudo`, `sqlplus`, `rman`, `exit` 같은 대표 케이스는 참고할 수 있으나,
- 최종 판단은 실제 세션에서 관찰한 반복 프롬프트로 결정한다.

5. 프롬프트 반복은 안정성 신호이지 성공 신호가 아니다.
- 프롬프트가 반복적으로 보인다는 것은 세션이 안정화되었다는 의미일 뿐,
- 명령 성공 여부는 에러 출력과 별도로 판단해야 한다.

## 현재 구현 단계

현재 코드는 "일반 shell 명령의 종료 판정"을 우선하는 단계로 맞춘다.

### 현재 단계에서 보장하려는 것

1. 로그인 직후 현재 shell prompt를 학습한다.
2. 명령 실행 후 현재 유효 prompt가 다시 보이면 즉시 종료한다.
3. 종료 prompt 라인은 최종 output에서 제외한다.
4. `expect`/`global_expect`는 선언된 명령에서만 후처리로 탄다.

### 현재까지 반영된 것

1. 일반 shell 명령
- 현재 유효 프롬프트가 다시 보이면 즉시 종료

2. SSH 인증 전략 분기
- `target_type=server`면 `mixed-auth`
- `target_type=network`면 `password-only`
- `target_type`은 대소문자를 구분하지 않고, 비어 있거나 잘못된 값이면 `server`로 처리한다
- `server`: `look_for_keys=True`, `allow_agent=True`, `password=ansible_password`
- `network`: `look_for_keys=False`, `allow_agent=False`, `password=ansible_password`
- `connect_timeout` 기본값은 5초
- `banner_timeout`, `auth_timeout` 기본값은 `server=30초`, `network=60초`

3. 디버그 정보 결과 포함
- 각 명령 결과에 `debug_info` 포함
- `current_prompt`, `last_line`, `last_line_type`, `prompt_match`, `timed_out` 확인 가능
- `prompt_changed`, `prompt_changed_from`, `prompt_changed_to` 확인 가능
- `prompt_change_confirmed`, `prompt_probe_lines`, `prompt_probe_error_lines`, `prompt_change_probe_result` 확인 가능

4. shell prompt 변경 최소 처리
- 현재 프롬프트와 다른 새 prompt 후보가 마지막 줄에 나타나면 후보로 본다
- 이 경우에만 조건부 추가 확인을 수행한다
- `Enter` 1회 + 짧은 polling으로 같은 prompt가 다시 나오면 전환 성공으로 본다

5. application prompt 최소 처리
- `RMAN>`, `SQL>` 같은 application prompt 후보를 prompt 후보로 인식한다
- probe 중 공란/에러 라인이 섞여도 같은 prompt가 다시 나타나면 prompt 변경 성공으로 본다

6. 승격 처리
- `become_method`가 비어 있으면 승격 안 함
- `become_method=enable`인데 현재 prompt가 이미 `#`면 `enable` 생략
- `become_method=su|sudo`인데 로그인 유저가 이미 `root`이고 `become_user`가 비었거나 `root`면 생략

7. 성공 판정 보정
- output이 비어 있어도 `prompt_match` 또는 `prompt_changed`가 true면 성공으로 본다
- `password_prompt`, `auth_fail`, `error_line`은 성공으로 보지 않는다
- `last_line_type=non_prompt`인데 `prompt_match`/`prompt_changed`가 없으면 성공으로 보지 않는다

8. output / debug 분리
- 최종 `output`에는 실제 본문/배너 출력만 남긴다
- shell/application prompt 라인은 종료 판정과 전환 판정 용도로만 사용한다
- prompt 변화 사실은 `debug_info`에서 확인한다

### 현재까지 확인된 성공 시나리오

1. 일반 shell 명령
- `hostname`, `pwd`, `ls -al`
- prompt 복귀 즉시 종료

2. shell prompt 변경
- `su - oracle`
- `[root@... ]#` -> `[oracle@... ]$` 전환 확인
- 다음 명령은 변경된 oracle prompt 기준으로 즉시 종료

3. application prompt 변경
- `rman`
- `[oracle@... ]$` -> `RMAN>` 전환 확인
- `exit`
- `RMAN>` -> `[oracle@... ]$` 복귀 확인

4. SSH 인증 분기
- `target_type=server`에서 `mixed-auth` 로그인 성공 확인
- 패스워드만 맞는 서버, 키가 있는 서버, 둘 다 실패하는 서버 케이스를 로그로 검증
- `target_type=network`에서 `password-only` 로그인 성공 확인
- 이미 `#` prompt인 네트워크 장비에서 `enable` 생략 확인

### 아직 본격 반영하지 않는 것

1. `sqlplus` 실환경 검증
2. probe 기반 세부 정책 고도화
3. 복잡한 출력 정제 정책
4. 실패/오류 패턴의 본격 분류
5. 인증 성공 방식(`password`/`key`) 로그 구분 필요 여부 검토

즉 현재 단계의 기준은 아래 한 줄이다.

- "현재 유효 프롬프트가 다시 보이면 즉시 종료"

## 프롬프트 판단 모델

## 1. 실행 전 체크

명령 실행 전 아래를 확인한다.

- 현재 세션의 기준 프롬프트(`current_prompt`)
- 이전 프롬프트 스택 존재 여부
- 현재 세션이 shell 상태인지 application 상태인지

이 단계의 목적은 "이번 명령 실행의 기준 prompt"를 확보하는 것이다.

## 2. 실행 후 체크

명령 실행 후 아래를 판단한다.

- 기존 prompt가 다시 돌아왔는가
- 기존과 다른 새 prompt 후보가 등장했는가
- 그 새 prompt 후보가 반복적으로 안정적으로 보이는가
- timeout 안에 안정화되지 않았는가

## 재학습 규칙

새로운 프롬프트 후보를 발견했다고 바로 current prompt로 승격하지 않는다.

아래 규칙을 따른다.

1. 마지막 비공백 라인에서 새로운 prompt 후보를 탐지한다.
2. 기존 prompt와 동일하면 일반 명령 종료 가능성으로 본다.
3. 기존 prompt와 다르면 새 prompt 후보로 저장한다.
4. 같은 후보가 2회 이상 반복적으로 관찰될 때만 새 current prompt로 승격한다.
5. 반복되지 않거나 timeout까지 안정화되지 않으면 승격하지 않는다.

## 예시

### shell -> shell user 전환

초기:
- `[root@host ~]#`

명령:
- `su - oracle`

전환 후:
- `[oracle@host ~]$`
- `[oracle@host ~]$`

이 경우 `[oracle@host ~]$`가 반복되므로 새 current prompt로 승격한다.

### shell -> RMAN 전환

초기:
- `[oracle@localhost ~]$`

명령:
- `rman`

출력:
- `Recovery Manager: ...`
- `Version ...`
- `RMAN>`
- `RMAN>`

이 경우 `RMAN>`가 반복되므로 application prompt로 승격한다.

## timeout 정책

프롬프트 판단이 끝나지 않으면 timeout으로 처리한다.

권장 동작:

1. timeout 발생 시 `Ctrl+C` 전송
2. 짧은 drain 수행
3. 세션 오염 여부 점검
4. 다음 명령과 응답이 섞이지 않도록 정리

## 검증용 입력(probe) 정책

새 prompt 후보 검증 시 가능한 한 추가 입력 없이 관찰(passive observe)을 우선한다.

권장 순서:

1. 추가 입력 없이 짧게 재관찰
2. 필요 시 newline probe 수행
3. probe 결과는 최종 output에 포함하지 않음

주의:

- 공란 입력이 에러를 유발하는 프롬프트가 있다.
- probe 출력은 필터 결과를 오염시키면 안 된다.
- probe는 내부 버퍼에서만 처리하고 사용자 결과에서는 제거해야 한다.

## 결과 버퍼 정책

최종 `output`에는 아래만 포함한다.

- 사용자가 실행한 실제 명령의 출력
- 배너/본문 출력

최종 `output`에 포함하면 안 되는 것:

- 검증용 newline probe 출력
- 내부 prompt 재학습을 위한 관측 출력
- 반복 확인용 내부 제어 출력
- 종료/전환 판정에 사용한 prompt 라인

프롬프트 관련 정보는 `debug_info`에 남긴다.

## 성공/실패 판정 분리

프롬프트 안정화와 명령 성공은 분리해서 판단한다.

### 의미

- 프롬프트 반복: 세션 안정
- 성공 여부: 별도 판단 필요

### 실패 가능성 예시

- 기존 prompt로 즉시 복귀
- `command not found`
- `invalid`
- `unknown`
- `usage`
- `permission denied`
- `authentication failure`
- `ORA-`
- `RMAN-`
- `SP2-`

즉 프롬프트가 안정적으로 보여도 명령은 실패했을 수 있다.

## 즉시 보완이 필요한 구현 포인트

1. 프롬프트 오탐 방지
- 학습된 prompt가 있을 때 generic regex fallback 최소화

2. timeout 시 세션 정리
- `Ctrl+C` + drain 복원

3. global_expect 카운트 누적 버그 수정

4. sleep 시점 호환성 정리
- pre/post 여부 명확화

5. prompt match 개선
- 단순 contains 기반 한계 보완

6. 관측 로그 보강
- 어떤 기준으로 prompt를 확정했는지 로그 필요

## 단계별 진행 순서

1. 일반 shell 명령
- `pwd`, `hostname`, `ls -al`
- timeout을 거의 쓰지 않고 prompt 복귀 즉시 종료해야 한다.

2. shell prompt 변경
- `su`, `su -`
- 새 shell prompt 후보를 조건부 재확인 후 current prompt로 갱신한다.

3. application prompt 변경
- `rman`, `sqlplus`
- shell prompt와 별도 prompt를 다룬다.

4. 부가 기능
- `expect`
- `global_expect`
- 고급 출력 정리
- 세션 복구/로그 강화

## 현재 방향 요약

`prompt`는 아래 철학으로 정리한다.

- 사용자 인터페이스는 단순하게 유지
- `target_type`만으로 서버/네트워크 인증 전략을 분기한다
- 내부적으로 프롬프트를 자동 학습/재학습
- 명령 전/후 프롬프트를 모두 본다
- 프롬프트 변경은 반복 관찰 후에만 확정한다
- probe 출력은 결과에서 숨긴다
- 프롬프트 안정과 명령 성공은 분리해서 판단한다


gemini --resume "a27cfe5d-e093-4a97-a4c1-6ce964a46e5e" 