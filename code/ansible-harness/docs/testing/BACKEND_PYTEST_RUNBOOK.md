# Backend pytest 실행 Runbook

이 문서는 이 저장소에서 **백엔드 pytest를 실제로 실행하는 가장 안전한 기준 절차**를 정리합니다.

## 왜 이 문서가 필요한가

- 이 프로젝트의 백엔드 테스트는 `backend/app/...`를 기준으로 import 합니다.
- 그래서 단순히 `pytest`만 실행하면 `ModuleNotFoundError: No module named 'app'`가 날 수 있습니다.
- 실제로는 **백엔드 전용 venv + `cd backend` + `PYTHONPATH=.`** 조합으로 실행해야 안정적으로 동작합니다.

## 1. 최초 1회: 가상환경 생성

프로젝트 루트에서 실행합니다.

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements.txt
```

## 2. pytest 실행 기본형

프로젝트 루트에서 실행합니다.

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

핵심은 아래 두 가지입니다.

- `backend/.venv`를 사용해야 함
- `cd backend` 후 `PYTHONPATH=.`로 실행해야 `app.config`, `app.services...` import가 정상 동작함
- 이 방식은 루트 `.env`를 잘못 읽어오는 문제도 피할 수 있음

## 3. 자주 쓰는 실행 예시

### AI 서비스 테스트만 빠르게 실행

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

### 백엔드 테스트 전체 실행

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests -q
```

### 상세 로그로 실행

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -vv
```

## 4. 현재 기준 검증된 상태

이 문서를 추가하는 시점 기준으로 아래 명령은 실제 통과 확인이 끝났습니다.

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

결과:

- `21 passed`

## 5. 흔한 실패 원인

### `No module named 'app'`

원인:

- `PYTHONPATH` 없이 실행했거나
- `backend/`가 아닌 다른 기준 경로에서 import가 잡힘

해결:

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

### `pytest: command not found`

원인:

- 시스템 파이썬에는 pytest가 설치되지 않았고
- `backend/.venv`를 활성화하지 않았음

해결:

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

### 의존성 import 에러

원인:

- `backend/requirements.txt` 설치 전이거나
- venv가 오래돼서 현재 requirements와 어긋남

해결:

```bash
backend/.venv/bin/pip install -r backend/requirements.txt
```

### 루트 `.env` 때문에 Settings 검증 에러가 나는 경우

증상 예시:

- `Extra inputs are not permitted`
- `db_password`, `next_public_api_url` 같은 값이 Settings 로딩 중 예기치 않게 들어옴

원인:

- 프로젝트 루트에서 바로 실행하면서 루트 `.env`가 같이 읽힘

해결:

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest tests/test_ai_service.py -q
```

## 6. 운영 원칙

- 백엔드 테스트는 가능하면 항상 **프로젝트 루트에서 venv를 활성화한 뒤 `cd backend`로 들어가서** 실행합니다.
- 테스트 명령은 문서/메모/운영 가이드에 적을 때 아래 형식을 표준으로 사용합니다.

```bash
source backend/.venv/bin/activate
cd backend
PYTHONPATH=. python -m pytest <target> -q
```

- 앞으로 테스트 실행 예시를 추가할 때도 `pytest <file>` 단독 표기는 피하고, 위 표준 명령을 우선합니다.
