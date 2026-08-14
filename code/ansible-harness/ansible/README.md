# Ansible Assets

이 디렉터리는 공개 가능한 Ansible 확장 코드만 남긴 포트폴리오용 정리본입니다.

포함 항목:

- `modules/`: 프로젝트에서 사용한 커스텀 Ansible module
- `module_utils/`: module 공통 로직
- `conf/`: Ansible 실행 환경 구성 예시
- `requirements.yml`: collection 의존성

제외 항목:

- 실제 서버 IP, 계정, 비밀번호가 포함될 수 있는 inventory
- 고객사/내부 환경 기준 sample project
- 운영 서버 기준 배포 산출물

공개 샘플이 필요할 경우 `192.0.2.0/24` 문서용 IP 대역과 `CHANGE_ME` placeholder를 사용해서 별도 예시를 추가합니다.
