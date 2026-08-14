# AI RAG 설정 및 구성 가이드

## 먼저 읽을 것
- 본 문서는 AnsibleHarness 솔루션에 연동된 로컬 AI(RAG 기반) 기능을 구성하고 재빌드하는 전체 워크플로를 다룹니다.
- 환경 구성은 로컬망에 위치한 Windows 기반 Ollama 서버와 백엔드 컨테이너 간의 네트워크 통신을 전제로 합니다.

## 1. 외부 AI 서버 구성 (Ollama)
로컬 데이터 보안과 폐쇄망 환경을 고려하여 외부 AI 엔진인 Ollama를 별도 호스트(Windows PC 등)에 설치합니다.

1. **설치**: [ollama.com](https://ollama.com/download) 에서 다운로드 및 설치
2. **필수 모델 다운로드**: 백엔드에서 사용할 두 가지 모델을 받아야 합니다.
   ```bash
   ollama pull gemma4:e4b
   ollama pull ibm/granite-embedding:278m
   ```
3. **네트워크 개방**: 기본적으로 `localhost`만 허용되는 Ollama의 외부 접속을 허용합니다.
   - 윈도우 환경 변수 설정에서 `OLLAMA_HOST` 값을 `0.0.0.0` 으로 추가합니다.
   - 추가 후 Ollama를 트레이에서 완전히 종료 후 재시작해야 합니다.
4. **방화벽 설정**: 인바운드 규칙에 TCP 포트 `11434` 를 허용하도록 설정합니다. (예: `192.0.2.238:11434` 접근 허용)

## 2. 백엔드 환경 변수
AnsibleHarness 백엔드에서 AI 서버와 통신하고 인덱싱할 위치를 지정합니다. `docker-compose.yml` 또는 `.env` 에 설정합니다.

- `AI_BASE_URL`: Ollama 서버 주소 (예: `http://192.0.2.238:11434/v1`)
- `AI_CHAT_MODEL`: 대화 생성 모델 (`gemma4:e4b` 등)
- `AI_EMBEDDING_MODEL`: 임베딩 모델 (`ibm/granite-embedding:278m` 등)
- `AI_TIMEOUT_SECONDS`: AI API 타임아웃
- `AI_KNOWLEDGE_BASE_DIR`: 지식베이스 디렉터리 위치 (컨테이너 내 경로)
- `AI_INDEX_DIR`: FAISS 인덱스 저장 디렉터리
- `AI_RETRIEVAL_K`: 검색할 최종 문서 개수
- `AI_RETRIEVAL_FETCH_K`: MMR 필터링을 위한 초기 검색 개수

## 3. 지식베이스 관리 (Knowledge Base)
솔루션 루트의 `knowledge_base/` 디렉터리에 참조할 파일들을 보관합니다.
- 지원 확장자: `.txt`, `.md`, `.html`, `.yml`, `.yaml`, `.py`
- 규칙 가이드, 예제 코드, 앤서블 모범 사례 등을 서브 디렉터리별로 관리하면 RAG 과정에서 `doc_group`으로 활용됩니다.
- 내용이 추가되거나 수정되면 자동으로 반영되지 않으며, **수동 재빌드**가 필요합니다.

## 4. 인덱스 수동 재빌드 단계
문서를 수정한 후에는 RAG 인덱스(FAISS)를 새로 생성해야 챗봇이 변경된 내용을 알 수 있습니다.

- API 호출을 통해 재빌드를 트리거합니다: `POST /api/ai/index/rebuild`
  ```bash
  curl -sf -X POST http://localhost:8000/api/ai/index/rebuild
  ```
- **동시성 주의**: 재빌드는 프로세스 단위 락(`_REBUILD_LOCK`)에 의해 동시 수행이 방지됩니다. 이미 진행 중인 경우 409를 반환합니다.
- 재빌드 중에도 기존 `index.faiss`를 활용한 채팅은 계속 서비스됩니다. 재빌드가 완료되면 원자적(Atomic) 교체가 이루어집니다.

## 5. 알려진 실패 상태 (Troubleshooting)
1. **Ollama 서버 통신 불가 (`provider_unreachable`)**: Ollama 프로세스가 내려갔거나 방화벽/IP 문제.
2. **필수 모델 누락 (`model_not_installed`)**: 명시한 모델(`gemma4:e4b` 등)이 Ollama에 pull 되지 않았습니다.
3. **인덱스 파일 없음 (`index_missing`)**: `metadata.json` 혹은 `index.faiss` 파일이 없는 상태입니다. `/api/ai/index/rebuild`를 수행하세요.
4. **재빌드 실패 (`ai_index_rebuild_failed`)**: 텍스트 파싱 오류 또는 파일 권한, 디렉터리 경로 오류입니다.
