# 운영 가이드: 환경설정은 env 파일 하나로만 관리하기

목표는 배포 때마다 `docker-compose.yml`을 수정하는 일을 없애고, **`/opt/ansible-harness/shared/.env` 한 파일만 수정**하면 운영 설정이 반영되게 만드는 것입니다.

## 원칙

1) 운영 서버에서 설정은 **오직** `/opt/ansible-harness/shared/.env`에만 둡니다.

2) 배포/재기동/롤백 명령은 항상 아래 형식을 사용합니다.

```bash
docker compose --env-file /opt/ansible-harness/shared/.env -p ansible-harness up -d --build
```

3) `docker-compose.yml`에는 IP/localhost를 하드코딩하지 않고 `${VAR}`로만 받습니다.

## 어떤 값들을 .env에 넣어야 하나?

레포의 `.env.example`을 그대로 복사해서 시작하세요.

```bash
cp /opt/ansible-harness/.env.example /opt/ansible-harness/shared/.env
vi /opt/ansible-harness/shared/.env
```

### 필수(운영에서 거의 항상 필요)

- `DB_PASSWORD`

### AI 사용 시 필수

- `AI_BASE_URL` (예: `http://192.0.2.238:11434/v1`)
- `AI_CHAT_MODEL`
- `AI_EMBEDDING_MODEL`

### 프론트 관련(실수 방지 정책)

- `NEXT_PUBLIC_API_URL`은 **운영에서는 비워두는 것을 권장**합니다.
  - 비워두면 프론트는 항상 `/api/*` 상대경로로 호출하고 Next 프록시가 내부 `BACKEND_URL`로 전달합니다.
  - 이 방식이 “localhost/IP로 잘못 붙어서 전 페이지 에러” 같은 문제를 가장 확실히 막습니다.

## 변경을 반영하는 방법

### 1) 대부분의 설정 변경(backend/frontend 재기동 필요)

```bash
cd /opt/ansible-harness
docker compose --env-file /opt/ansible-harness/shared/.env -p ansible-harness up -d --build --force-recreate
```

### 2) AI 설정만 바꿨을 때(backend만)

```bash
cd /opt/ansible-harness
docker compose --env-file /opt/ansible-harness/shared/.env -p ansible-harness up -d --build --force-recreate backend
```

### 3) NEXT_PUBLIC_API_URL을 바꿨을 때(프론트는 빌드 시점 반영)

`NEXT_PUBLIC_API_URL`은 프론트 **빌드 시점** 값이라, 바꾸면 `frontend`를 반드시 `--build` 해야 합니다.

```bash
cd /opt/ansible-harness
docker compose --env-file /opt/ansible-harness/shared/.env -p ansible-harness up -d --build --force-recreate frontend
```

## 배포 후 확인(필수)

```bash
# 컨테이너 상태
cd /opt/ansible-harness
docker compose --env-file /opt/ansible-harness/shared/.env -p ansible-harness ps

# 헬스
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:3000/health

# API 프록시
curl -fsS http://localhost:3000/api/projects
curl -fsS "http://localhost:3000/api/jobs?page=1&size=20"

# AI 상태
curl -fsS http://localhost:8000/api/ai/health
```
