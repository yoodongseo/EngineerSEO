# Ansible Playbook 계층 구조 상세 설명

이 문서는 `Playbook_tree.png` 시각화 자료를 바탕으로 구성된 Ansible Playbook의 논리적 트리 구조와 각 요소에 대한 설명입니다.

## 1. Playbook 트리 구조 시각화

```text
PLAYBOOK (최상위 계층)
├── PLAY_PREFIX ($playbook features: hosts, become, vars, etc.)
├── PRE_TASKS (Role 실행 전 선행 작업)
│   └── TASK (내부 구조 동일)
├── ROLES (재사용 가능한 독립적 단위)
├── TASKS (주요 작업 목록)
│   ├── BLOCK (작업 그룹화)
│   │   └── MODULES
│   ├── [RESCUE] (에러 발생 시 복구 작업)
│   │   └── MODULES
│   ├── [ALWAYS] (성공/실패 여부 무관하게 항상 실행)
│   │   └── MODULES
│   └── TASK (개별 작업)
├── POST_TASKS (주요 작업 및 Role 실행 후 후행 작업)
│   └── TASK (내부 구조 동일)
└── PLAY_POSTFIX ($playbook features)
```

## 2. 세부 구성 요소 설명

### 2.1. Play 수준 (Global Level)
*   **PLAY_PREFIX / POSTFIX:** Play 전체에 영향을 주는 설정입니다. `hosts`, `user`, `become` 설정 및 전역 변수(`vars`) 정의가 여기에 해당합니다.
*   **실행 순서:** `PRE_TASKS` → `ROLES` → `TASKS` → `POST_TASKS` 순으로 순차 실행됩니다.

### 2.2. 작업 구조 (TASK/MODULES Level)
모든 Task는 다음과 같은 세부 구조를 가집니다.
*   **TASK_PREFIX ($task features):** 모듈 실행 전 정의하는 속성입니다.
    *   `name`: 작업의 이름
    *   `become`: 권한 상승 여부
    *   `when`: 실행 조건 (Condition)
    *   `loop`: 반복 실행 정의
*   **MODULE (#module):** 실제 작업을 수행하는 핵심 유닛입니다. (예: `yum`, `copy`, `service`)
    *   `#module_params`: 모듈에 전달되는 파라미터
        *   `#mandatory`: 작업을 위해 반드시 입력해야 하는 필수 값
        *   `#optional`: 필요에 따라 설정하는 선택 값
*   **TASK_POSTFIX ($task features):** 모듈 실행 결과에 따라 처리되는 속성입니다.
    *   `register`: 실행 결과를 변수에 저장
    *   `notify`: 상태 변경 시 핸들러 호출
    *   `ignore_errors`: 에러 발생 시 무시 여부

### 2.3. 고급 제어 구조 (BLOCK/RESCUE/ALWAYS)
에러 핸들링과 논리적 그룹화를 위해 사용됩니다.
*   **BLOCK:** 여러 Task를 하나로 묶어 공통 설정(예: `when`, `become`)을 적용합니다.
*   **RESCUE:** `BLOCK` 내의 Task가 실패했을 때만 실행되는 예외 처리 구문입니다. (복구 로직)
*   **ALWAYS:** `BLOCK`과 `RESCUE` 결과에 상관없이 마지막에 반드시 실행되는 작업입니다. (정리 로직)

---
*본 문서는 Playbook_tree.png 분석 데이터를 기반으로 작성되었습니다.*
