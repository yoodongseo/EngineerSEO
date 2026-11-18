# register-handler

Ansible 자동점검 실행 결과를 공통으로 처리하기 위한 핵심 모듈입니다.

## 목적

점검 유형이 예방점검, 보안점검, 복제점검으로 나뉘어도 결과 처리 흐름은 동일하게 가져가기 위해 만들었습니다.

처리 흐름:

1. Ansible 명령 실행 결과 수집
2. `inspection_items`와 `result_items` 매칭
3. 명령어/출력/rule_key 누락 여부 검증
4. `command_check`로 공통 실행 실패 판정
5. `report_type`과 `rule_key` 기준 rule 선택
6. rule에서 업무 판정 수행
7. `result_build`에서 최종 payload 생성

## 주요 구성

- `module/register_handler.py`: 실제 Ansible module 진입점
- `module/register_handler_local.py`: 로컬 테스트용 진입점
- `core/command_check.py`: 공통 명령 실패 검증
- `core/result_build.py`: 최종 결과 payload 생성
- `core/rule_result.py`: rule 결과 생성 헬퍼
- `core/rules/__init__.py`: 예방/보안/복제 rule map 로딩

## 포트폴리오 포인트

- 점검 유형별 로직을 공통 handler와 개별 rule로 분리
- 명령 실패와 업무 판정을 계층화
- 결과 payload 형식을 표준화
- 새로운 점검 항목을 rule 단위로 확장 가능하게 구성
