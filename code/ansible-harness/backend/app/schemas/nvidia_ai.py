"""Pydantic schemas for NVIDIA AI request and response contracts."""

# pyright: reportMissingImports=false

from typing import Literal

from pydantic import BaseModel, Field


class NvidiaAICapabilities(BaseModel):
    """Capabilities exposed by the NVIDIA AI integration."""

    chat: bool = Field(True, description="채팅 지원 여부")
    streaming: bool = Field(True, description="스트리밍 지원 여부")
    knowledge_base: bool = Field(False, description="지식베이스 검색 지원 여부")
    index_rebuild: bool = Field(False, description="인덱스 재빌드 지원 여부")
    sources: bool = Field(False, description="출처 패널 지원 여부")
    timeline: bool = Field(True, description="타임라인 이벤트 지원 여부")


class NvidiaAIHealthResponse(BaseModel):
    """NVIDIA AI runtime health contract."""

    status: Literal["ok", "degraded"] = Field(..., description="서비스 상태")
    provider: Literal["nvidia"] = Field("nvidia", description="AI 제공자")
    provider_reachable: bool = Field(..., description="AI 제공자 연결 가능 여부")
    base_url: str = Field(..., description="OpenAI 호환 API 기본 URL")
    chat_model: str = Field(..., description="기본 채팅 모델")
    chat_model_installed: bool = Field(..., description="기본 채팅 모델 사용 가능 여부")
    timeout_seconds: int = Field(..., description="AI 요청 타임아웃(초)")
    capabilities: NvidiaAICapabilities = Field(..., description="지원 기능 집합")
    detail: str | None = Field(None, description="상태 상세 메시지")


class NvidiaAIChatRequest(BaseModel):
    """NVIDIA AI chat request payload."""

    question: str = Field(..., min_length=1, description="사용자 질문")


class NvidiaAIStreamMeta(BaseModel):
    """Bootstrap metadata emitted before NVIDIA chat chunks."""

    provider: Literal["nvidia"] = Field("nvidia", description="AI 제공자")
    model: str = Field(..., description="응답 생성에 사용된 모델")
    grounded: Literal[False] = Field(False, description="지식베이스 근거 여부")
    capabilities: NvidiaAICapabilities = Field(..., description="지원 기능 집합")
