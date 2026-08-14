# Ansible Harness

Ansible 기반 자동화 작업을 웹에서 생성, 실행, 관찰할 수 있도록 만든 자동화 툴 handoff 코드입니다.

이 저장본은 포트폴리오 및 이력서 정리용으로 공개 가능한 소스만 선별한 버전입니다. 원본 프로젝트의 로컬 DB, 배포 압축 파일, 빌드 산출물, 실제 inventory/credential 샘플, 내부 배포 로그는 제외했습니다.

## 구성

- `backend/`: FastAPI 기반 API 서버, 작업 실행/템플릿/inventory/AI 연동 API
- `frontend/`: Next.js 기반 웹 UI, 작업 실행 화면, inventory 관리, 템플릿 관리, AI 보조 화면
- `ansible/`: 커스텀 Ansible module/filter/module_utils 및 Ansible 실행 환경 구성
- `docs/`: 아키텍처, AI/RAG, inventory, 테스트, handoff 문서
- `knowledge_base/`: AI/RAG 응답과 운영 문서화를 위한 지식 문서
- `docker-compose.yml`: 로컬 개발 및 배포 구성을 이해하기 위한 예시 compose 파일

## 핵심 작업 범위

- Ansible 실행 흐름을 웹 API와 UI로 감싼 자동화 harness 구조 분석 및 정리
- 작업 템플릿, 프로젝트, inventory, 실행 로그를 분리한 백엔드 구조 구성
- Next.js 화면에서 작업 실행 상태와 로그를 확인할 수 있는 운영 UI 구성
- AI/RAG 기반 문서 검색 및 자동화 보조 기능의 기초 구조 반영
- 팀 작업물 공개를 위해 내부 IP, credential, sample inventory, 배포 산출물 제거

## 제외한 항목

- `frontend/node_modules`, `frontend/.next`, `graphify-out` 등 생성 산출물
- `backend/data/*.db` 등 로컬 실행 데이터
- `deploy.zip`, `deploy.tar.gz`, `*.log` 등 배포/로그 파일
- 실제 접속 정보가 포함된 `ansible/inventory`, 일부 sample project
- 내부 배포 대상 서버를 특정하는 deployment archive 문서

## 실행 개요

민감 정보는 `.env.example`을 기준으로 별도 `.env`에 설정합니다.

```powershell
docker compose --env-file .env up --build
```

기본 포트는 다음과 같습니다.

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- PostgreSQL: `localhost:5433`

## 포트폴리오 정리 메모

이 프로젝트는 팀원들과 방향을 논의하고 프로토타입을 개발한 뒤, 실사용에 가까운 구조로 마이그레이션한 Ansible 자동화 웹 도구입니다.

후속 Notion 정리에서는 다음 기준으로 나누면 좋습니다.

- 프로젝트 목적: Ansible 자동화 실행을 웹 기반으로 표준화
- 기술 스택: FastAPI, Next.js, PostgreSQL, Docker Compose, Ansible Runner, AI/RAG
- 본인 기여: 프로토타입 개발 참여, 실사용 구조 마이그레이션, 코드 handoff 정리, 민감 정보 제거, GitHub 포트폴리오화
- 보여줄 성과: 실행/관찰/inventory/템플릿/AI 보조 흐름을 하나의 운영 도구로 묶은 경험
