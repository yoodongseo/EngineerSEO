# 🚀 Ansible Harness + AI RAG 통합 배포 가이드

## 📌 1. 시스템 아키텍처 및 요구사항
이번 배포는 크게 **(1) Ansible Harness가 구동되는 메인 VM**과 **(2) 로컬망에 위치한 외부 AI 엔진(Ollama)** 두 가지 서버를 설정하는 과정으로 나뉩니다.

### [메인 VM (Rocky Linux 9.4)]
- **역할:** FastAPI 백엔드, Next.js 프론트엔드, PostgreSQL 구동 (Docker Compose 기반)
- **요구사항:** 4 vCPU, 4GB RAM 이상, Docker 및 Docker Compose 플러그인 설치
- **필수 포트오픈:** `3000`(프론트엔드), `8000`(백엔드 API)

### [외부 AI 서버 (Windows PC 또는 별도 GPU 서버)]
- **역할:** 데이터 보안과 폐쇄망을 고려하여 내부망에서 Ollama 엔진 및 LLM 모델 구동
- **요구사항:** 로컬망 통신 가능 IP (예: `192.0.2.238`), 인바운드 방화벽 오픈(`11434` 포트)

---

## 📌 2. 1단계: 외부 AI 서버(Ollama) 설정 (Windows 환경 기준)

메인 서비스 배포 전, 챗봇의 뇌 역할을 할 AI 서버를 먼저 세팅합니다.

**1. Ollama 설치 및 실행**
- [Ollama 공식 홈페이지](https://ollama.com/download)에서 Windows 버전을 다운로드 및 설치합니다.

**2. 필수 AI 모델 다운로드**
설치 후 터미널(또는 명령 프롬프트)을 열고, 백엔드에서 사용할 채팅 모델과 임베딩(검색용) 모델을 다운로드합니다.
```bash
ollama pull gemma4:e4b
ollama pull ibm/granite-embedding:278m
```

**3. 외부 접속(0.0.0.0) 허용 및 방화벽 설정**
기본적으로 Ollama는 로컬(localhost)에서만 접속할 수 있습니다. 메인 VM이 접속할 수 있도록 허용해야 합니다.
1. Windows **시스템 환경 변수 편집** 메뉴를 엽니다.
2. 새 시스템 변수를 추가합니다.
   - 변수 이름: `OLLAMA_HOST`
   - 변수 값: `0.0.0.0`
3. 작업 표시줄 트레이 아이콘에서 Ollama를 완전히 **Quit** 한 후 다시 실행하여 환경 변수를 적용합니다.
4. **Windows 방화벽 인바운드 규칙**에서 TCP 포트 `11434`를 개방합니다.

---

## 📌 3. 2단계: 메인 시스템(Ansible Harness) 배포 준비

VM(Rocky Linux 등) 환경에 접속하여 프로젝트를 다운로드하고 배포를 준비합니다.

**1. 프로젝트 복사 및 구조 확인**
```bash
sudo mkdir -p /opt/ansible-harness
sudo chown $USER:$USER /opt/ansible-harness
cd /opt/ansible-harness

# (Git이나 rsync, SCP 등을 이용해 이 디렉토리에 프로젝트를 위치시킵니다.)
```

**2. 권한 및 파일 정리**
프로젝트 내 `knowledge_base` 디렉터리가 루트에 있는지 확인합니다.
이 폴더는 이후 AI가 읽어들일 학습용 마크다운, 코드 파일 등이 들어갈 자리입니다.

---

## 📌 4. 3단계: 통합 환경 변수(.env) 설정

`docker-compose.yml`이 위치한 경로(`/opt/ansible-harness`)에 `.env` 파일을 생성합니다.
특히 **AI_BASE_URL**은 1단계에서 구성한 Ollama 서버의 실제 IP로 맞춰주세요.

```bash
cat > .env << 'EOF'
# === Database ===
DB_PASSWORD=CHANGE_ME_DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://harness:CHANGE_ME_DB_PASSWORD@db:5432/ansible_harness

# === Backend ===
ANSIBLE_DATA_DIR=/ansible
CORS_ORIGINS=http://localhost:3000,http://<VM_IP>:3000

# === Frontend ===
# 운영 권장: 비워두기(상대경로 /api/* + Next 프록시 사용)
# NEXT_PUBLIC_API_URL을 VM IP로 고정하면, 접속 경로/포워딩/도메인 변경 시 깨질 수 있습니다.
NEXT_PUBLIC_API_URL=

# === AI RAG Configuration ===
# 1단계에서 구성한 Ollama PC의 내부 IP를 입력합니다.
AI_BASE_URL=http://192.0.2.238:11434/v1

# 사용하고자 하는 AI 모델 지정
AI_CHAT_MODEL=gemma4:e4b
AI_EMBEDDING_MODEL=ibm/granite-embedding:278m

# 임베딩/검색 파라미터 
AI_RETRIEVAL_K=6
AI_RETRIEVAL_FETCH_K=20
EOF
```

---

## 📌 5. 4단계: 시스템 구동 및 서비스 확인

환경 변수가 준비되었으면 Docker Compose를 이용해 전체 시스템을 빌드하고 실행합니다.

```bash
# 전체 서비스 백그라운드 실행 (최초 실행 시 빌드 진행)
docker compose up -d --build

# 컨테이너 상태 확인
docker compose ps
```

**정상 확인 방법:**
- 백엔드 상태: `curl http://localhost:8000/health` (응답에 healthy 포함)
- AI 연동 상태: `curl http://localhost:8000/api/ai/health`
  - 응답에 `provider_reachable: true`, 모델 설치 여부가 `true`인지 확인합니다. (처음에는 인덱스가 없으므로 전체 `status`는 `degraded`로 표시되는 것이 정상입니다.)

---

## 📌 6. 5단계: 지식베이스(KB) 구성 및 인덱스 재빌드

AI 챗봇이 Ansible 시스템에 대한 지식을 가질 수 있도록 문서를 제공하고 검색 인덱스를 생성해야 합니다.

**1. 지식 파일 추가**
- 프로젝트 루트의 `knowledge_base/` 디렉터리 내부에 읽히고 싶은 `.md`, `.txt`, `.py`, `.yaml`, `.html` 파일들을 추가합니다.
- 디렉터리 구조(예: `coding_rules/파이선가이드.md`) 자체가 그룹핑 기준으로 작동합니다.

**2. 인덱스 빌드 트리거 (최초 1회 및 문서 갱신 시마다)**
- AI는 파일이 추가되었다고 자동으로 갱신하지 않으므로 수동 재빌드가 필요합니다.
```bash
# 터미널에서 API를 호출하여 재빌드 시작
curl -sf -X POST http://localhost:8000/api/ai/index/rebuild
```
- 재빌드가 성공하면 `backend/data/faiss_index` 디렉터리에 `index.faiss`와 `metadata.json` 파일이 안전하게 교체 저장됩니다.

**3. 프론트엔드 확인**
- 브라우저를 열고 프론트엔드(`http://<VM_IP>:3000/ai`)로 접속합니다.
- 상단 시스템 상태에 **"🟢 AI Ready"** 뱃지가 떠 있다면 모든 구성이 완벽하게 완료된 것입니다!
- 이제 자유롭게 질문을 입력하여 답변과 출처(Sources)를 확인하실 수 있습니다.

---

## 💡 문제 해결 (Troubleshooting) 요약

1. **AI 서비스 오류 배너 노출 / 503 에러 발생**
   - **원인:** Ollama 서버 연결 실패 혹은 모델명 오타
   - **해결:** 메인 VM에서 Ollama 쪽 포트 통신이 되는지 테스트(`curl http://192.0.2.238:11434`)하고, `.env`의 모델명과 `ollama list` 결과가 정확히 일치하는지 확인하세요.
2. **AI 페이지 접속 시 "AI 인덱스를 찾을 수 없습니다" 표시**
   - **원인:** 초기 설치 시 `index.faiss` 파일이 없는 정상적인 상태입니다.
   - **해결:** `POST /api/ai/index/rebuild` 를 한 번 실행해주시면 해결됩니다.
3. **Ansible Playbook 실행 권한 에러**
   - 백엔드 도커 컨테이너가 시스템의 SSH 키(`~/.ssh/id_rsa`)를 이용해야 한다면 `docker-compose.yml`의 backend volumes에 SSH 경로를 마운트 하거나 내부 env에 키를 복사해 주어야 합니다.
