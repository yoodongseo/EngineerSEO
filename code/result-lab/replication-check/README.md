# replication-check

스토리지/복제 상태 점검 자동화 코드입니다.

## 대상

- NetApp
- HPE
- IBM

## 구성

```text
replication-check/
  rules/
  vars/
```

- `rules/`: 복제 상태 판정 로직
- `vars/`: 벤더별 복제 상태 점검 명령과 항목 정의

## 포트폴리오 포인트

- 기존 filter 기반 복제점검 로직을 register_handler rule 방식으로 정리
- 복제 관계의 `before_data`, `after_data`를 payload에 포함
- 예방점검/보안점검과 같은 결과 처리 구조로 통합
