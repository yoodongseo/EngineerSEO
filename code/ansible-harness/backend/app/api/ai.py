"""Dedicated AI API routes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.ai import AIChatRequest, AIHealthResponse, AIIndexRebuildResponse
from app.services.ai_service import chat_with_ai_stream, get_ai_health, rebuild_ai_index

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/health", response_model=AIHealthResponse)
async def ai_health():
    """AI 런타임 설정과 인덱스 상태를 조회합니다."""

    return await get_ai_health()


@router.post("/index/rebuild", response_model=AIIndexRebuildResponse)
async def rebuild_index():
    """AI 지식 인덱스 전체 재빌드 계약을 노출합니다."""

    return await rebuild_ai_index()


@router.post("/chat")
async def chat(request: AIChatRequest):
    """AI 채팅 계약을 노출합니다 (Server-Sent Events)."""

    generator = await chat_with_ai_stream(request)
    return StreamingResponse(generator, media_type="text/event-stream")
