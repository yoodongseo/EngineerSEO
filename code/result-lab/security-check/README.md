# security-check

서버 및 네트워크 장비 보안점검 자동화 코드입니다.

## 구성

```text
security-check/
  rules/
  vars/
```

- `rules/`: 보안점검 판정 로직
- `vars/`: OS/벤더별 점검 항목과 명령어 정의

## 네트워크 장비 대상

- Cisco
- Arista
- Citrix
- Piolink
- Alteon L4

## 주요 점검 항목

- 계정 및 권한 분리
- 디폴트 계정 삭제
- 비밀번호 설정
- 평문 서비스 포트 제거
- 원격접속 포트 변경 및 접속제한
- 랜섬웨어 관련 포트 제거
- Directed-broadcast 차단
- Mask-reply 차단
- IP Source Routing 제한
- 미사용 인터페이스 Shutdown

## 포트폴리오 포인트

- 기존 보안점검 구조를 result_lab rule 방식으로 마이그레이션
- 벤더별 장비 출력 차이를 rule에서 처리
- 네트워크/서버 보안 기준을 자동 판정 가능한 구조로 분리
