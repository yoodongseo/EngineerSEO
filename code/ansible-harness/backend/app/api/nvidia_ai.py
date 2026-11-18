"""Dedicated NVIDIA AI API routes."""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.nvidia_ai import NvidiaAIChatRequest, NvidiaAIHealthResponse
from app.services.nvidia_ai_service import chat_with_nvidia_ai_stream, get_nvidia_ai_health

router = APIRouter(prefix="/api/nvidia-ai", tags=["nvidia-ai"])


@router.get("/health", response_model=NvidiaAIHealthResponse)
async def nvidia_ai_health():
    """NVIDIA AI 런타임 상태를 조회합니다."""

    return await get_nvidia_ai_health()


@router.post("/chat")
async def nvidia_ai_chat(request: NvidiaAIChatRequest):
    """NVIDIA AI 채팅 계약을 노출합니다 (Server-Sent Events)."""

    generator = await chat_with_nvidia_ai_stream(request)
    return StreamingResponse(generator, media_type="text/event-stream")
