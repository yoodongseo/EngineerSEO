"""NVIDIA AI service (chat-only, OpenAI-compatible hosted provider)."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from openai import AsyncOpenAI  # type: ignore[reportMissingImports]

from app.config import settings
from app.schemas.ai import AITimelineEvent
from app.schemas.nvidia_ai import (
    NvidiaAICapabilities,
    NvidiaAIChatRequest,
    NvidiaAIHealthResponse,
    NvidiaAIStreamMeta,
)

_NVIDIA_CLIENT: AsyncOpenAI | None = None
_API_KEY_MISSING_DETAIL = "nvidia_api_key_missing"


def _capabilities() -> NvidiaAICapabilities:
    return NvidiaAICapabilities()


def _sse_event(event: str, payload: dict) -> str:
    """Format a server-sent event payload."""

    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _timeline_payload(
    *,
    seq: int,
    stage: str,
    status: str,
    label: str,
    detail: str | None = None,
    output_chunk_count: int | None = None,
    output_char_count: int | None = None,
) -> dict:
    event = AITimelineEvent(
        seq=seq,
        stage=stage,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        label=label,
        detail=detail,
        mode="direct",
        counts={
            "output_chunk_count": output_chunk_count,
            "output_char_count": output_char_count,
        }
        if output_chunk_count is not None or output_char_count is not None
        else None,
        ts=datetime.now(UTC),
    )
    return event.model_dump(mode="json", exclude_none=True)


def _extract_model_name(model) -> str | None:
    if isinstance(model, str) and model:
        return model
    for attr in ("id", "model", "name"):
        value = getattr(model, attr, None)
        if isinstance(value, str) and value:
            return value
    if isinstance(model, dict):
        for key in ("id", "model", "name"):
            value = model.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _get_nvidia_client() -> AsyncOpenAI:
    global _NVIDIA_CLIENT
    if not settings.NVIDIA_AI_API_KEY.strip():
        raise ValueError(_API_KEY_MISSING_DETAIL)
    if _NVIDIA_CLIENT is None:
        _NVIDIA_CLIENT = AsyncOpenAI(
            base_url=settings.NVIDIA_AI_BASE_URL,
            api_key=settings.NVIDIA_AI_API_KEY,
            timeout=settings.NVIDIA_AI_TIMEOUT_SECONDS,
            max_retries=0,
        )
    return _NVIDIA_CLIENT


async def _close_nvidia_client() -> None:
    global _NVIDIA_CLIENT
    if _NVIDIA_CLIENT is None:
        return
    close_method = getattr(_NVIDIA_CLIENT, "close", None)
    _NVIDIA_CLIENT = None
    if close_method is None:
        return
    maybe_awaitable = close_method()
    if hasattr(maybe_awaitable, "__await__"):
        await maybe_awaitable


async def _probe_nvidia_provider() -> dict:
    if not settings.NVIDIA_AI_API_KEY.strip():
        return {
            "reachable": False,
            "models": set(),
            "detail": _API_KEY_MISSING_DETAIL,
        }
    client = _get_nvidia_client()
    try:
        models_response = await client.models.list()
        model_names = {
            name
            for item in getattr(models_response, "data", [])
            if (name := _extract_model_name(item)) is not None
        }
        return {
            "reachable": True,
            "models": model_names,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "reachable": False,
            "models": set(),
            "detail": str(exc),
        }


async def get_nvidia_ai_health() -> NvidiaAIHealthResponse:
    provider = await _probe_nvidia_provider()
    available_models = provider.get("models", set())
    detail = provider.get("detail")
    model_installed = settings.NVIDIA_AI_CHAT_MODEL in available_models if provider["reachable"] else False
    status = "ok" if provider["reachable"] and model_installed else "degraded"
    return NvidiaAIHealthResponse(
        status=status,
        provider_reachable=provider["reachable"],
        base_url=settings.NVIDIA_AI_BASE_URL,
        chat_model=settings.NVIDIA_AI_CHAT_MODEL,
        chat_model_installed=model_installed,
        timeout_seconds=settings.NVIDIA_AI_TIMEOUT_SECONDS,
        capabilities=_capabilities(),
        detail=detail,
    )


async def chat_with_nvidia_ai_stream(request: NvidiaAIChatRequest) -> AsyncGenerator[str, None]:
    async def generator() -> AsyncGenerator[str, None]:
        seq = 1
        output_chunk_count = 0
        answer_so_far = ""
        first_chunk_seen = False
        meta = NvidiaAIStreamMeta(model=settings.NVIDIA_AI_CHAT_MODEL, capabilities=_capabilities())

        yield _sse_event(
            "timeline",
            _timeline_payload(
                seq=seq,
                stage="request",
                status="started",
                label="NVIDIA 요청 시작",
                detail="NVIDIA 호환 채팅 런타임에 연결을 시작합니다.",
            ),
        )
        seq += 1
        yield _sse_event("meta", meta.model_dump(mode="json"))

        if not settings.NVIDIA_AI_API_KEY.strip():
            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="error",
                    status="failed",
                    label="NVIDIA 요청 실패",
                    detail="NVIDIA_AI_API_KEY가 설정되지 않았습니다.",
                    output_chunk_count=output_chunk_count,
                    output_char_count=len(answer_so_far),
                ),
            )
            yield _sse_event(
                "error",
                {
                    "code": _API_KEY_MISSING_DETAIL,
                    "message": "NVIDIA_AI_API_KEY가 설정되지 않았습니다.",
                    "provider": "nvidia",
                },
            )
            return

        client = _get_nvidia_client()
        try:
            stream = await client.chat.completions.create(
                model=settings.NVIDIA_AI_CHAT_MODEL,
                messages=[{"role": "user", "content": request.question}],
                stream=True,
            )

            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="generation",
                    status="started",
                    label="응답 생성 시작",
                    detail="NVIDIA 모델이 답변을 생성하고 있습니다.",
                ),
            )
            seq += 1

            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                delta = getattr(choices[0], "delta", None)
                content = getattr(delta, "content", None) if delta is not None else None
                if not content:
                    continue

                output_chunk_count += 1
                answer_so_far += content

                if not first_chunk_seen:
                    first_chunk_seen = True
                    yield _sse_event(
                        "timeline",
                        _timeline_payload(
                            seq=seq,
                            stage="generation",
                            status="streaming",
                            label="응답 스트리밍 시작",
                            detail="첫 번째 응답 청크를 수신했습니다.",
                            output_chunk_count=output_chunk_count,
                            output_char_count=len(answer_so_far),
                        ),
                    )
                    seq += 1

                yield _sse_event(
                    "chunk",
                    {
                        "answer": content,
                        "answer_so_far": answer_so_far,
                        "grounded": False,
                        "model": settings.NVIDIA_AI_CHAT_MODEL,
                        "provider": "nvidia",
                    },
                )

            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="complete",
                    status="completed",
                    label="응답 완료",
                    detail="NVIDIA 응답 스트리밍이 완료되었습니다.",
                    output_chunk_count=output_chunk_count,
                    output_char_count=len(answer_so_far),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="error",
                    status="failed",
                    label="NVIDIA 요청 실패",
                    detail=str(exc),
                    output_chunk_count=output_chunk_count,
                    output_char_count=len(answer_so_far),
                ),
            )
            yield _sse_event(
                "error",
                {
                    "code": "nvidia_request_failed",
                    "message": str(exc),
                    "provider": "nvidia",
                },
            )

    return generator()
