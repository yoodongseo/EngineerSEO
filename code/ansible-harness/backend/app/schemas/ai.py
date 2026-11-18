"""Pydantic schemas for AI request and response contracts."""

# pyright: reportMissingImports=false

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AIIndexState(BaseModel):
    """Current AI index status summary."""

    status: Literal["missing", "ready", "building", "error"] = Field(..., description="인덱스 상태")
    document_count: int = Field(0, description="인덱싱된 문서 수")
    chunk_count: int = Field(0, description="인덱싱된 청크 수")
    last_rebuilt_at: datetime | None = Field(None, description="마지막 재빌드 시각")
    detail: str | None = Field(None, description="상태 상세 메시지")


class AISourceItem(BaseModel):
    """Grounding source item returned by chat responses."""

    source: str = Field(..., description="knowledge_base 기준 상대 경로")
    filename: str = Field(..., description="원본 파일명")
    doc_group: str = Field(..., description="문서 그룹")
    ext: str = Field(..., description="파일 확장자")
    chunk_id: str = Field(..., description="청크 식별자")
    excerpt: str = Field(..., description="응답 근거 발췌문")


class AIHealthResponse(BaseModel):
    """AI runtime health contract."""

    status: Literal["ok", "degraded"] = Field(..., description="서비스 상태")
    provider: str = Field(..., description="AI 제공자")
    provider_reachable: bool = Field(..., description="AI 제공자 연결 가능 여부")
    base_url: str = Field(..., description="OpenAI 호환 API 기본 URL")
    chat_model: str = Field(..., description="기본 채팅 모델")
    chat_model_installed: bool = Field(..., description="기본 채팅 모델 설치 여부")
    embedding_model: str = Field(..., description="기본 임베딩 모델")
    embedding_model_installed: bool = Field(..., description="기본 임베딩 모델 설치 여부")
    timeout_seconds: int = Field(..., description="AI 요청 타임아웃(초)")
    index_state: AIIndexState


class AIIndexRebuildResponse(BaseModel):
    """Manual index rebuild contract."""

    status: str = Field(..., description="재빌드 요청 처리 상태")
    message: str = Field(..., description="상태 설명")
    document_count: int = Field(0, description="현재 문서 수")
    chunk_count: int = Field(0, description="현재 청크 수")
    index_path: str = Field(..., description="저장된 인덱스 경로")
    index_state: AIIndexState


class AIChatRequest(BaseModel):
    """AI chat request payload."""

    question: str = Field(..., min_length=1, description="사용자 질문")
    use_knowledge_base: bool = Field(True, description="지식베이스 기반 검색 사용 여부")


class AIChatResponse(BaseModel):
    """AI chat response contract."""

    answer: str = Field(..., description="AI 응답")
    grounded: bool = Field(..., description="지식베이스 근거 여부")
    sources: list[AISourceItem] = Field(default_factory=list, description="근거 출처 목록")
    model: str = Field(..., description="응답 생성에 사용된 모델")
    retrieval_count: int = Field(0, description="실제로 사용된 검색 청크 수")
    index_state: AIIndexState


class AITimelineCounts(BaseModel):
    """Observable counts that can be surfaced in the AI timeline."""

    index_document_count: int | None = Field(default=None, description="현재 인덱스 문서 수")
    index_chunk_count: int | None = Field(default=None, description="현재 인덱스 청크 수")
    candidate_count: int | None = Field(default=None, description="검색 후보 청크 수")
    selected_count: int | None = Field(default=None, description="최종 선택된 청크 수")
    retrieval_count: int | None = Field(default=None, description="실제로 답변에 사용된 검색 청크 수")
    output_chunk_count: int | None = Field(default=None, description="스트리밍된 출력 청크 수")
    output_char_count: int | None = Field(default=None, description="스트리밍된 출력 문자 수")


class AITimelineEvent(BaseModel):
    """Public-safe observable workflow milestone for streamed AI responses."""

    seq: int = Field(..., description="응답 스트림 내 순차 번호")
    stage: Literal["request", "retrieval", "sources", "generation", "complete", "error"] = Field(
        ..., description="처리 단계"
    )
    status: Literal["started", "completed", "streaming", "no_hit", "failed"] = Field(
        ..., description="단계 상태"
    )
    label: str = Field(..., description="짧은 단계 제목")
    detail: str | None = Field(None, description="사용자에게 보여줄 상세 설명")
    mode: Literal["knowledge_base", "direct"] = Field(..., description="응답 생성 모드")
    counts: AITimelineCounts | None = Field(None, description="관찰 가능한 수치 정보")
    ts: datetime = Field(..., description="이벤트 생성 시각")
