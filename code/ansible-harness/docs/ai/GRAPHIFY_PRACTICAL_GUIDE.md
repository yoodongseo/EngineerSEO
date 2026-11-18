# Graphify 실전 활용 가이드

이 문서는 이 저장소에서 이미 만들어 둔 Graphify 결과를 **실제 수정/개발 작업에 어떻게 써먹는지**를 정리한 실전 가이드입니다.

핵심은 간단합니다.

- Graphify는 **코드를 대신 수정해주는 도구**가 아닙니다.
- 대신 **어디부터 봐야 하는지**, **어떤 파일이 같이 움직이는지**, **영향 범위가 어디까지인지**를 빠르게 잡아주는 지도입니다.
- 즉, 구현 전에 길을 찾는 도구이고, 구현 후에는 검증 포인트를 빠르게 모으는 도구입니다.

---

## 1. 왜 이 문서가 필요한가

이 프로젝트는 다음처럼 서로 얽힌 영역이 많습니다.

- backend API / 서비스 로직
- frontend 페이지 / 프록시 / SSE
- 배포 문서 / 운영 문서
- AI(RAG) 문서와 실제 구현
- Ansible 실행 흐름 / Job 로그 흐름

이런 구조에서는 문제 하나를 고칠 때도 보통 파일 하나만 보면 끝나지 않습니다.

예를 들어:

- backend를 고치면 frontend API 계약이 같이 바뀔 수 있고
- env 설정을 바꾸면 AI health, 배포 문서, compose가 같이 영향을 받고
- 로그/SSE를 바꾸면 backend 서비스, API, frontend viewer, 문서가 같이 엮입니다.

Graphify는 이런 연결을 한 번에 보여줘서, **작업 시작점**, **영향 범위**, **숨은 결합도**를 잡는 데 강합니다.

---

## 2. 이 저장소에서 Graphify 결과가 이미 있는 위치

현재 이 프로젝트에서는 아래 결과를 이미 만들어 둔 상태입니다.

### backend 기준
- `graphify-out/backend.GRAPH_REPORT.md`
- `graphify-out/backend.graph.html`
- `graphify-out/backend.graph.json`

### frontend 기준
- `graphify-out/frontend.GRAPH_REPORT.md`
- `graphify-out/frontend.graph.html`
- `graphify-out/frontend.graph.json`

### docs 기준
- `graphify-out/docs.GRAPH_REPORT.md`
- `graphify-out/docs.graph.html`
- `graphify-out/docs.graph.json`

### 기타
- `.graphifyignore`

### 아직 새로 돌려야 한다면
이미 만들어진 결과를 읽는 것이 가장 빠르지만, 그래프를 다시 만들고 싶다면 보통 아래처럼 시작합니다.

```bash
/graphify backend
/graphify frontend
/graphify docs
```

이 저장소에서는 보통 **backend → frontend → docs** 순서가 가장 실용적입니다.

실전에서는 보통 아래 순서로 보면 됩니다.

1. `*.GRAPH_REPORT.md`로 큰 구조 파악
2. `*.graph.html`로 연결 관계를 시각적으로 확인
3. `*.graph.json`은 필요할 때만 세부 구조 확인
4. 실제 코드/문서 파일을 열어서 검증

처음 열 파일 우선순위는 아래처럼 고정해두면 덜 헷갈립니다.

- **1순위:** `graphify-out/<target>.GRAPH_REPORT.md`
- **2순위:** `graphify-out/<target>.graph.html`
- **3순위:** 실제 소스/문서 파일

즉, **Graphify 보고 끝내는 게 아니라, Graphify로 어디를 읽을지 좁힌 다음 실제 파일을 읽는 방식**이 맞습니다.

---

## 3. 무엇을 먼저 보면 좋은가

처음 열 때는 항상 아래 3가지를 우선 봅니다.

### 3.1 Community Hubs
각 영역의 덩어리입니다.

예:
- backend에서는 `Job API and Project Catalog`, `AI Chat and Index Flow`, `Ansible Execution and Live Logs`
- frontend에서는 `Frontend API Client`, `AI Assistant Integration`, `Proxy Routes`
- docs에서는 `Deployment Release Model`, `AI RAG Design`, `SSE and Job Lifecycle`

이걸 보면 **지금 내가 건드리는 주제가 어느 묶음에 속하는지** 먼저 잡을 수 있습니다.

### 3.2 God Nodes
연결이 유독 많은 중심 노드입니다.

예:
- backend: `Job`, `AIChatRequest`, `rebuild_ai_index()`, `chat_with_ai_stream()`
- frontend: `apiFetch()`, `AI assistant page`, `Catch-all /api proxy route`
- docs: `Shared Folder and Release Package Architecture`, `RAG Pipeline`

이 노드들은 보통:
- 영향 범위가 크고
- 수정 리스크가 높고
- 리팩터링 우선순위 후보가 됩니다.

### 3.3 Surprising Connections / Suggested Questions
의외의 연결과, Graphify가 스스로 제안한 질문입니다.

이 부분은 특히 좋습니다. 왜냐하면 사람이 놓치기 쉬운 연결을 먼저 보여주기 때문입니다.

예:
- env 설정 문제인데 사실 frontend localhost misrouting과 backend AI health가 같이 연결되어 있다
- Job lifecycle 문서가 실제 frontend/로그/SSE 흐름과 강하게 이어진다
- AI rebuild 함수가 schema, retrieval, runtime health를 동시에 건드린다

---

## 4. 실전 1. 버그 수정에 쓰는 방법

이 모드는 아래처럼 **이미 증상이 있는 경우**에 씁니다.

- “작업실행에서 서버 연결 실패”
- “AI 질문했는데 문서를 못 찾음”
- “로그가 안 따라온다”
- “프론트에서 localhost로 붙는다”

### 언제 쓰면 좋은가
- 에러 메시지는 있는데 시작 파일을 모르겠을 때
- backend/frontend/docs 중 어디부터 봐야 할지 헷갈릴 때
- 한 군데 수정하면 다른 군데가 깨질 것 같을 때

### 시작점
1. 증상과 가장 가까운 축을 고릅니다.
   - API/작업실행 → `backend.GRAPH_REPORT.md`
   - 화면/프론트 요청 → `frontend.GRAPH_REPORT.md`
   - 배포/환경변수/운영 절차 → `docs.GRAPH_REPORT.md`

2. 그 다음 아래를 봅니다.
   - Community Hubs
   - God Nodes
   - Suggested Questions

### 실제 작업 흐름
예를 들어 “작업실행에서 서버에 연결할 수 없습니다”라면:

1. frontend graph에서 `Frontend API Client`, `Proxy Routes`, `AI Assistant Integration` 같은 허브를 봅니다.
2. `apiFetch()` 같은 God Node가 어디와 연결되는지 확인합니다.
3. 연결된 실제 파일을 엽니다.
   - `frontend/src/lib/api.ts`
   - `frontend/src/app/api/[...path]/route.ts`
   - 관련 page 파일
4. backend 쪽도 이어서 봅니다.
   - `backend/app/api/jobs.py`
   - `backend/app/services/ansible_service.py`
   - `backend/app/config.py`
5. docs graph에서 env/deploy 문서와 연결되는지 확인합니다.

이렇게 하면 “프론트 문제처럼 보였는데 사실 env/compose 문제였다” 같은 케이스를 빨리 좁힐 수 있습니다.

### 실전 예시: 프론트 "서버 연결 실패"가 env/API 라우팅 혼선이었던 경우
이 저장소에서 실제로 겪었던 대표적인 사례는, 화면에서는 단순히 "서버에 연결할 수 없습니다"처럼 보였지만 실제 원인은 **브라우저용 API 주소와 서버 프록시용 API 주소의 역할이 섞여 있었던 것**입니다.

#### 증상
- 작업실행이나 목록 화면에서 서버 연결 실패처럼 보였습니다.
- 처음에는 backend 자체가 죽었거나 서버가 내려간 문제처럼 보였습니다.
- 하지만 실제로는 frontend가 `/api/*` 프록시를 타지 않고 잘못된 절대 주소를 바라보는 상황이 핵심이었습니다.

#### 왜 Graphify로 시작하는 게 맞았나
- 이 문제는 frontend 한 파일만 보면 끝나는 종류가 아니었습니다.
- API 호출 방식, Next 프록시, compose env, 운영 문서가 같이 엮여 있었습니다.
- 그래서 `frontend.GRAPH_REPORT.md`에서 `Frontend API Client`, `Proxy Routes`, `apiFetch()` 같은 허브/중심 노드부터 보는 방식이 효과적이었습니다.

#### Graphify가 실제로 좁혀줘야 하는 파일
- `frontend/src/lib/api.ts`
- `frontend/src/app/api/[...path]/route.ts`
- `frontend/src/app/health/route.ts`
- `docker-compose.yml`
- `docs/architecture/DEV_PLAN_FRONTEND_API_ROUTING.md`
- `docs/architecture/ENV_SINGLE_SOURCE_OF_TRUTH.md`

#### 실제 원인
- `NEXT_PUBLIC_API_URL`은 **프론트 번들에 박히는 브라우저용 값**이고, 빌드 시점에 고정됩니다.
- 반면 `BACKEND_URL`은 **Next 서버 프록시가 backend로 붙을 때 쓰는 서버 런타임 값**입니다.
- 이 둘을 같은 성격으로 생각하면, 브라우저가 `/api/*` 프록시를 거치지 않고 잘못된 절대 주소로 직접 붙어버릴 수 있습니다.
- 즉, 이 혼선의 본질은 **서버 프록시가 처리해야 할 요청을 브라우저가 직접 backend로 보내려 한 것**이었습니다.

#### 수정 방향
- 브라우저 요청은 기본적으로 상대 경로 `/api/*`를 타게 둡니다.
- 서버 안의 프록시 라우트가 `BACKEND_URL=http://backend:8000`을 사용하도록 둡니다.
- 이 저장소처럼 `/api/*` 프록시를 기준으로 운영하는 구성이라면, 운영에서 `NEXT_PUBLIC_API_URL`을 굳이 채우지 않도록 두는 경우가 많습니다.
- 이 저장소에서는 이 원칙이 `docs/architecture/DEV_PLAN_FRONTEND_API_ROUTING.md`, `.env.example`, `docs/architecture/ENV_SINGLE_SOURCE_OF_TRUTH.md`에도 같이 반영돼 있어야 합니다.

#### 수정 후 검증
- 브라우저 네트워크 탭에서 요청이 `http://...:8000/...`이 아니라 `/api/...`로 나가는지 확인합니다.
- `curl http://localhost:3000/api/projects`가 정상인지 확인합니다.
- `curl http://localhost:3000/health` 또는 관련 health 경로가 정상인지 확인합니다.
- `NEXT_PUBLIC_API_URL`은 빌드 시점에 주입되므로, 값을 바꿨다면 frontend를 재빌드해서 반영 여부를 확인합니다.

#### 이 예시에서 Graphify로 얻은 실전 가치
- frontend 문제처럼 보이던 것을 proxy/env/docs까지 포함한 문제로 바로 넓혀볼 수 있었습니다.
- 먼저 열 파일과 나중에 볼 파일을 구분할 수 있었습니다.
- 결국 수정 포인트는 적었지만, 영향 범위는 넓다는 걸 초반에 파악할 수 있었습니다.

### 이 모드에서 Graphify로 얻어야 하는 결과물
- 가장 가능성 높은 원인 경로 1~3개
- 먼저 읽어야 할 파일 목록
- 수정 후 확인해야 할 검증 포인트

### 검증 방법
Graphify 결과만 믿지 말고 반드시 아래로 닫습니다.

- 실제 코드 읽기
- 실제 서버 상태 확인
- 관련 테스트 / build / health check 실행

### 여기까지 확인하면 이 단계는 끝입니다
- 원인 후보가 1~3개 수준으로 줄었고
- 실제로 열어볼 파일 목록이 정리됐고
- 수정 후 확인할 테스트/health check가 정해졌다면
- 그때부터는 Graphify 탐색 단계가 끝나고 실제 수정 단계로 넘어가면 됩니다

즉, **Graphify는 가설 생성기**, 최종 판정기는 아닙니다.

---

## 5. 실전 2. 기능 개발에 쓰는 방법

이 모드는 아래처럼 **새 기능이나 기능 확장**에 씁니다.

- AI 페이지에 새 패널 추가
- Job 실행 흐름 개선
- AI RAG 동작 확장
- API 계약 변경 + 프론트 연동

### 언제 쓰면 좋은가
- 어느 레이어부터 바꿔야 할지 모를 때
- backend만 바꾸면 되는지, frontend/docs까지 같이 바뀌는지 보고 싶을 때
- 빠르게 “최소 변경 셋”을 만들고 싶을 때

### 시작점
1. 기능의 중심 축을 먼저 정합니다.
   - backend 중심 기능인지
   - frontend 중심 기능인지
   - docs/운영 절차까지 바뀌는 기능인지

2. 해당 graph report에서 아래를 봅니다.
   - 어떤 Community가 중심인지
   - 중심 God Node가 무엇인지
   - Surprising Connections가 어디로 이어지는지

### 실제 작업 흐름
예를 들어 AI 기능 추가라면:

1. backend graph에서 `AI Chat and Index Flow`, `AI Retrieval Internals`, `AI Schemas and Route Contracts`를 봅니다.
2. frontend graph에서 `AI Assistant Integration`, `AI Page Actions`, `Frontend API Client`를 봅니다.
3. docs graph에서 `AI RAG Design`, `AI Operations and Recovery`, `Deployment Release Model`을 같이 봅니다.
4. 그 다음 실제 변경 파일을 좁힙니다.

예시 최소 변경 셋:
- backend
  - `backend/app/services/ai_service.py`
  - `backend/app/schemas/ai.py`
  - `backend/app/api/ai.py`
- frontend
  - `frontend/src/lib/api.ts`
  - `frontend/src/app/ai/page.tsx`
  - `frontend/src/components/...`
- docs
  - `docs/ai/DEPLOYMENT_GUIDE_AI.md`
  - `docs/ai/AI_RAG_SETUP.md`

이렇게 하면 처음부터 “어디까지 같이 바꿔야 하는지”를 큰 틀에서 보고 시작할 수 있습니다.

### 이 모드에서 Graphify로 얻어야 하는 결과물
- 최소 변경 파일 목록
- 구현 순서
- 같이 업데이트해야 하는 문서/테스트/운영 항목

### 추천 구현 순서
1. 계약(API/schema) 확인
2. backend 핵심 로직 수정
3. frontend 연결부 수정
4. docs/runbook 보정
5. 테스트/빌드/health 검증

### 여기까지 확인하면 이 단계는 끝입니다
- 최소 변경 파일 목록이 나왔고
- 구현 순서가 정리됐고
- 같이 고쳐야 할 문서/운영 항목이 잡혔고
- 마지막 검증 명령(build/test/health)이 정해졌다면
- 그 상태에서 구현에 들어가면 됩니다

Graphify의 장점은 여기서 **숨은 동반 수정 범위**를 놓치지 않게 해준다는 점입니다.

---

## 6. 실전 3. 우선순위 정리 / 리팩터링 / 영향도 분석

이 모드는 급한 버그나 기능이 아니라, 아래 같은 질문에 씁니다.

- “어디가 제일 복잡한가?”
- “뭘 먼저 리팩터링해야 안전한가?”
- “문서가 코드와 어디서 어긋나고 있나?”
- “이 함수/페이지 하나 바꾸면 어디까지 영향이 가나?”

### 언제 쓰면 좋은가
- 큰 수정 전에 안전한 진입점을 찾고 싶을 때
- 기술부채를 우선순위로 정리하고 싶을 때
- 리팩터링 범위를 과하게 키우지 않으려 할 때

### 시작점
이 모드에서는 **God Nodes**를 가장 먼저 봅니다.

왜냐하면 God Node는 보통:
- 많이 연결된 중심축이고
- 변경 시 영향도가 크고
- 구조상 병목일 가능성이 높기 때문입니다.

예:
- backend의 `Job`, `rebuild_ai_index()`, `chat_with_ai_stream()`
- frontend의 `apiFetch()`, AI assistant page, proxy route
- docs의 `Shared Folder and Release Package Architecture`, `RAG Pipeline`

### 실제 작업 흐름
1. God Node를 고릅니다.
2. 그 노드가 연결된 Community를 확인합니다.
3. 연결이 많은 이유를 분해합니다.
   - 정말 중심이라 그런지
   - 너무 많은 책임이 몰려 있어서 그런지
4. Surprising Connections를 같이 봅니다.
   - 내가 생각 못한 영향 방향이 있는지
5. 작은 안전 구간으로 잘라서 리팩터링 후보를 만듭니다.

예를 들어:
- `apiFetch()`가 너무 많은 영역을 연결하고 있으면
  - 공통 fetch 레이어는 유지하되
  - AI 전용 로직 / Jobs 전용 로직 / health 체크 로직을 분리할지 검토할 수 있습니다.

- `chat_with_ai_stream()`가 너무 많은 역할을 가지면
  - retrieval 준비
  - timeline 생성
  - chunk streaming
  - no-hit 처리
  - error 처리
  를 더 작은 함수로 나누는 후보가 됩니다.

### 이 모드에서 Graphify로 얻어야 하는 결과물
- 우선순위가 붙은 hotspot 목록
- 안전하게 자를 수 있는 리팩터링 단위
- 영향 범위 요약
- 같이 보강해야 할 테스트 목록

### 여기까지 확인하면 이 단계는 끝입니다
- 어디가 중심 결합점인지 보이고
- 한 번에 다 건드리지 않을 안전한 분리 단위가 보이고
- 영향 범위를 확인할 테스트/로그/API가 정해졌다면
- 그때부터는 우선순위 결정 또는 리팩터링 설계 단계로 넘어가면 됩니다

### 주의할 점
연결이 많다고 무조건 나쁜 것은 아닙니다.

예:
- 진짜 허브 역할이라서 당연히 연결이 많을 수도 있습니다.
- 반대로 연결은 적어도, 실제 운영 리스크는 클 수도 있습니다.

그래서 Graphify는 “우선 의심할 곳”을 주는 것이지, 자동으로 리팩터링 결론을 내려주지는 않습니다.

---

## 7. Graphify 결과 해석법

실전에서 가장 중요한 부분입니다.

### 7.1 EXTRACTED
문서나 코드에 **명시적으로 있는 연결**입니다.

예:
- import
- 함수 호출
- 명시적 참조
- 문서 내 직접 설명

이건 비교적 신뢰도가 높습니다.

### 7.2 INFERRED
직접 적혀 있진 않지만, **합리적으로 추론한 연결**입니다.

예:
- 같은 데이터를 공유하는 흐름
- 사실상 같이 움직이는 기능
- 같은 책임을 묶는 문서/구성요소

이건 실전에서 매우 유용하지만, 반드시 실제 파일로 확인해야 합니다.

### 7.3 AMBIGUOUS
가능성은 있지만 **확실하지 않은 연결**입니다.

이건 절대 바로 구현 판단에 쓰면 안 됩니다.

해야 할 일은 하나입니다.

- “가설”로만 두고 실제 코드/문서/서버에서 검증

### 7.4 God Nodes
연결이 많아서 눈에 띄는 중심 노드입니다.

실전 의미:
- 영향 범위 크다
- 리팩터링 후보일 수 있다
- 버그 진단 시작점일 수 있다

### 7.5 Surprising Connections
사람이 예상 못 한 연결입니다.

실전 의미:
- 놓치기 쉬운 영향 범위
- 숨은 결합도
- 문서-구현 불일치 힌트

---

## 8. 주의사항

### 8.1 Graphify만 보고 바로 수정하지 말 것
항상 실제 파일을 읽고, 현재 서버/런타임 상태를 확인해야 합니다.

### 8.2 문서는 과거 상태일 수 있음
특히 `docs/`는 작성 시점의 가정을 담고 있어서, 실제 운영과 다를 수 있습니다.

### 8.3 그래프의 연결과 운영 장애는 다를 수 있음
구조상 연결은 약해 보여도, 운영에서는 env 하나 때문에 전체가 깨질 수 있습니다.

### 8.4 AMBIGUOUS는 구현 근거가 아님
AMBIGUOUS는 “확인 후보”지 “수정 근거”가 아닙니다.

### 8.5 God Node를 무조건 쪼개는 게 정답은 아님
허브 역할이 자연스러운 경우도 많습니다. 책임 과밀인지, 정상 허브인지 구분이 필요합니다.

---

## 9. 작업 전/후 체크리스트

## 작업 전
- [ ] 이번 작업이 bug fix / feature / impact analysis 중 어디인지 정했다
- [ ] backend / frontend / docs 중 어느 graph부터 볼지 정했다
- [ ] `GRAPH_REPORT.md`의 Community Hubs를 먼저 읽었다
- [ ] God Nodes와 Surprising Connections를 확인했다
- [ ] 실제로 열어볼 파일 목록을 3~10개 정도로 좁혔다

## 작업 중
- [ ] EXTRACTED와 INFERRED를 구분해서 보고 있다
- [ ] AMBIGUOUS 연결은 실제 파일/로그/서버 상태로 검증 중이다
- [ ] 수정 범위가 커질 때 docs/test/deploy 영향도도 같이 보고 있다

## 작업 후
- [ ] 실제 코드 변경이 Graphify에서 예상한 영향 범위와 맞는지 점검했다
- [ ] 테스트 / build / health check / 배포 검증을 했다
- [ ] 필요하면 문서도 같이 갱신했다
- [ ] 다음 작업자가 볼 수 있게 변경 이유와 영향 범위를 남겼다

---

## 10. 한 줄로 정리

Graphify는 이 프로젝트에서 **“어디를 어떻게 읽고 들어갈지 정해주는 실전 지도”**입니다.

잘 쓰는 방법은 단순합니다.

- 버그 수정할 때는 **원인 경로를 좁히는 데 쓰고**
- 기능 개발할 때는 **최소 변경 셋을 잡는 데 쓰고**
- 리팩터링할 때는 **영향 범위와 우선순위를 정하는 데 쓰면 됩니다**.

다만 최종 판단은 항상 실제 코드, 실제 서버 상태, 실제 검증 결과로 닫아야 합니다.
