"""AI indexing, health, and grounded chat service."""

# pyright: reportMissingImports=false

from __future__ import annotations

import asyncio
import json
import math
import shutil
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from collections.abc import AsyncGenerator
from typing import Any, Literal
from uuid import uuid4

import faiss
import numpy as np
from bs4 import BeautifulSoup
from fastapi import HTTPException
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter
from openai import APIConnectionError, APIStatusError, AsyncOpenAI

from app.config import settings
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIHealthResponse,
    AIIndexRebuildResponse,
    AIIndexState,
    AISourceItem,
    AITimelineCounts,
    AITimelineEvent,
)

_SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".yml", ".yaml", ".py"}
_EXCLUDED_KB_FILENAMES = {"README.md", "WRITING_RULES.md"}
_LANGUAGE_BY_EXTENSION = {
    ".txt": "text",
    ".md": "markdown",
    ".html": "html",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".py": "python",
}
_INDEX_FILENAME = "index.faiss"
_MANIFEST_FILENAME = "metadata.json"
_OLLAMA_API_KEY = "ollama"
_EMBED_BATCH_SIZE = 16
_SOURCE_EXCERPT_LENGTH = 220
_MMR_LAMBDA = 0.75
_NO_HIT_DISTANCE_THRESHOLD = 1.15
_CHAT_SYSTEM_PROMPT = """너는 내부 개발 문서 기반 도우미다.

규칙:
- 반드시 CONTEXT에 있는 내용만 근거로 답변해라.
- 근거가 부족하면 모른다고 말해라.
- 가능하면 규칙/예제/가이드 중 어떤 문서군에서 가져왔는지 설명해라.
- 마지막에 참고 파일(source)을 목록으로 정리해라.
- CONTEXT 밖의 내용은 추정하지 마라.
"""
_DIRECT_CHAT_SYSTEM_PROMPT = """너는 친절하고 정확한 개발 도우미다.

규칙:
- 질문 의도를 먼저 정확히 파악하고 답변해라.
- 불확실한 내용은 단정하지 말고 한계를 명확히 밝혀라.
- 필요한 경우 단계별로 간결하게 안내해라.
"""
_NO_HIT_ANSWER = "지식베이스에서 관련 근거를 찾지 못했습니다. 현재 인덱싱된 문서 범위 안에서는 답변할 수 없습니다."

_REBUILD_LOCK = asyncio.Lock()
_INDEX_STATE_LOCK = threading.Lock()
_INDEX_STATE = AIIndexState(
    status="missing",
    document_count=0,
    chunk_count=0,
    last_rebuilt_at=None,
    detail="AI 인덱스가 아직 생성되지 않았습니다.",
)


@dataclass(frozen=True)
class IndexedChunk:
    text: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class RetrievedChunk:
    text: str
    metadata: dict[str, str]
    distance: float
    vector: np.ndarray[Any, np.dtype[np.float32]]


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sse_event(event_name: str, payload: Any) -> str:
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _timeline_payload(
    *,
    seq: int,
    stage: Literal["request", "retrieval", "sources", "generation", "complete", "error"],
    status: Literal["started", "completed", "streaming", "no_hit", "failed"],
    label: str,
    mode: Literal["knowledge_base", "direct"],
    detail: str | None = None,
    counts: AITimelineCounts | None = None,
) -> dict[str, Any]:
    return AITimelineEvent(
        seq=seq,
        stage=stage,
        status=status,
        label=label,
        detail=detail,
        mode=mode,
        counts=counts,
        ts=_utc_now(),
    ).model_dump(mode="json")


def _clone_index_state() -> AIIndexState:
    with _INDEX_STATE_LOCK:
        return AIIndexState.model_validate(_INDEX_STATE.model_dump(mode="json"))


def _set_index_state(index_state: AIIndexState) -> None:
    global _INDEX_STATE

    with _INDEX_STATE_LOCK:
        _INDEX_STATE = index_state


def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.AI_BASE_URL,
        api_key=_OLLAMA_API_KEY,
        timeout=settings.AI_TIMEOUT_SECONDS,
        max_retries=0,
    )


async def _close_openai_client(client: AsyncOpenAI) -> None:
    close = getattr(client, "close", None)
    if close is None:
        return
    maybe_awaitable = close()
    if asyncio.iscoroutine(maybe_awaitable):
        await maybe_awaitable


def _resolve_kb_root() -> Path:
    kb_root = Path(settings.AI_KNOWLEDGE_BASE_DIR).resolve()
    if not kb_root.exists() or not kb_root.is_dir():
        raise HTTPException(status_code=500, detail="knowledge_base_not_found")
    return kb_root


def _resolve_index_dir() -> Path:
    return Path(settings.AI_INDEX_DIR).resolve()


def _manifest_path(index_dir: Path) -> Path:
    return index_dir / _MANIFEST_FILENAME


def _index_file_path(index_dir: Path) -> Path:
    return index_dir / _INDEX_FILENAME


def _ensure_within_kb_root(path: Path, kb_root: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(kb_root)
    except ValueError as exc:
        raise ValueError(f"knowledge base root 밖 경로는 허용되지 않습니다: {path}") from exc
    return resolved


def _iter_supported_kb_files(kb_root: Path) -> list[Path]:
    supported_files: list[Path] = []
    for path in sorted(kb_root.rglob("*")):
        if not path.is_file():
            continue
        if path.parent == kb_root and path.name in _EXCLUDED_KB_FILENAMES:
            continue
        if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            continue
        try:
            resolved = _ensure_within_kb_root(path, kb_root)
        except ValueError:
            continue
        supported_files.append(resolved)
    return supported_files


def _relative_source(path: Path, kb_root: Path) -> str:
    relative_path = path.relative_to(kb_root).as_posix()
    return f"knowledge_base/{relative_path}"


def _doc_group_for_path(path: Path, kb_root: Path) -> str:
    relative_parts = path.relative_to(kb_root).parts
    if len(relative_parts) >= 2:
        return relative_parts[0]
    return "default"


def _metadata_for_path(path: Path, kb_root: Path) -> dict[str, str]:
    extension = path.suffix.lower()
    return {
        "source": _relative_source(path, kb_root),
        "filename": path.name,
        "ext": extension,
        "doc_group": _doc_group_for_path(path, kb_root),
        "language": _LANGUAGE_BY_EXTENSION[extension],
    }


def _read_file_text(path: Path) -> str:
    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if path.suffix.lower() == ".html":
        soup = BeautifulSoup(raw_text, "html.parser")
        return soup.get_text("\n", strip=True)
    return raw_text


def _splitter_for_extension(extension: str) -> RecursiveCharacterTextSplitter:
    if extension == ".py":
        return RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=1200,
            chunk_overlap=150,
        )
    if extension == ".md":
        return RecursiveCharacterTextSplitter.from_language(
            language=Language.MARKDOWN,
            chunk_size=1400,
            chunk_overlap=180,
        )
    if extension == ".html":
        return RecursiveCharacterTextSplitter.from_language(
            language=Language.HTML,
            chunk_size=1400,
            chunk_overlap=180,
        )
    if extension in {".yml", ".yaml"}:
        return RecursiveCharacterTextSplitter(
            chunk_size=1100,
            chunk_overlap=120,
            separators=["\n\n- name:", "\n- name:", "\n\n", "\n", " ", ""],
        )
    return RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=150)


def _collect_index_chunks(kb_root: Path) -> tuple[int, list[IndexedChunk]]:
    chunk_records: list[IndexedChunk] = []
    document_count = 0

    for path in _iter_supported_kb_files(kb_root):
        text = _read_file_text(path).strip()
        if not text:
            continue

        document_count += 1
        base_metadata = _metadata_for_path(path, kb_root)
        splitter = _splitter_for_extension(base_metadata["ext"])
        segments = [segment.strip() for segment in splitter.split_text(text) if segment.strip()]

        for index, segment in enumerate(segments):
            chunk_metadata = dict(base_metadata)
            chunk_metadata["chunk_id"] = str(index)
            chunk_records.append(IndexedChunk(text=segment, metadata=chunk_metadata))

    return document_count, chunk_records


async def _embed_texts(texts: list[str]) -> np.ndarray[Any, np.dtype[np.float32]]:
    if not texts:
        raise ValueError("임베딩할 텍스트가 없습니다.")

    client = _get_openai_client()
    try:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), _EMBED_BATCH_SIZE):
            batch = texts[start : start + _EMBED_BATCH_SIZE]
            response = await client.embeddings.create(
                model=settings.AI_EMBEDDING_MODEL,
                input=batch,
            )
            for item in sorted(response.data, key=lambda current: current.index):
                embeddings.append(item.embedding)
        return np.asarray(embeddings, dtype="float32")
    finally:
        await _close_openai_client(client)


def _build_faiss_index(embeddings: np.ndarray[Any, np.dtype[np.float32]]) -> faiss.IndexFlatL2:
    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise ValueError("유효한 임베딩이 생성되지 않았습니다.")
    index = faiss.IndexFlatL2(int(embeddings.shape[1]))
    faiss_index: Any = index
    faiss_index.add(embeddings)
    return index


def _write_index_atomically(
    index_dir: Path,
    index: faiss.Index,
    chunks: list[IndexedChunk],
    document_count: int,
    rebuilt_at: datetime,
) -> None:
    temp_dir = index_dir.with_name(f"{index_dir.name}.tmp-{uuid4().hex}")
    rollback_dir = index_dir.with_name(f"{index_dir.name}.old-{uuid4().hex}")

    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        faiss.write_index(index, str(_index_file_path(temp_dir)))
        manifest = {
            "version": 1,
            "document_count": document_count,
            "chunk_count": len(chunks),
            "rebuilt_at": rebuilt_at.isoformat(),
            "embedding_model": settings.AI_EMBEDDING_MODEL,
            "chat_model": settings.AI_CHAT_MODEL,
            "chunks": [
                {
                    "text": chunk.text,
                    "metadata": chunk.metadata,
                }
                for chunk in chunks
            ],
        }
        _manifest_path(temp_dir).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        index_dir.parent.mkdir(parents=True, exist_ok=True)
        if index_dir.exists():
            index_dir.replace(rollback_dir)

        temp_dir.replace(index_dir)
        if rollback_dir.exists():
            shutil.rmtree(rollback_dir)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        if rollback_dir.exists() and not index_dir.exists():
            rollback_dir.replace(index_dir)
        raise


def _read_manifest(index_dir: Path) -> dict[str, Any] | None:
    manifest_path = _manifest_path(index_dir)
    index_path = _index_file_path(index_dir)
    if not manifest_path.exists() or not index_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _index_state_from_storage(prefer_runtime_error: bool = True) -> AIIndexState:
    current_state = _clone_index_state()
    if _REBUILD_LOCK.locked():
        return AIIndexState(
            status="building",
            document_count=current_state.document_count,
            chunk_count=current_state.chunk_count,
            last_rebuilt_at=current_state.last_rebuilt_at,
            detail="AI 인덱스를 재빌드하는 중입니다.",
        )

    if prefer_runtime_error and current_state.status == "error":
        return current_state

    manifest = _read_manifest(_resolve_index_dir())
    if manifest is not None:
        rebuilt_at = manifest.get("rebuilt_at")
        return AIIndexState(
            status="ready",
            document_count=int(manifest.get("document_count", 0)),
            chunk_count=int(manifest.get("chunk_count", 0)),
            last_rebuilt_at=datetime.fromisoformat(rebuilt_at) if rebuilt_at else None,
            detail="AI 인덱스가 준비되었습니다.",
        )

    if current_state.status == "error":
        return current_state

    return AIIndexState(
        status="missing",
        document_count=0,
        chunk_count=0,
        last_rebuilt_at=None,
        detail="AI 인덱스가 아직 생성되지 않았습니다.",
    )


def _extract_model_name(raw_model: Any) -> str | None:
    if isinstance(raw_model, str):
        return raw_model
    if isinstance(raw_model, dict):
        return raw_model.get("id") or raw_model.get("name")
    model_id = getattr(raw_model, "id", None)
    if isinstance(model_id, str):
        return model_id
    name = getattr(raw_model, "name", None)
    if isinstance(name, str):
        return name
    return None


async def _probe_provider() -> dict[str, Any]:
    client = _get_openai_client()
    try:
        response = await client.models.list()
        models = {_extract_model_name(model) for model in getattr(response, "data", [])}
        available_models = {model for model in models if model}
        return {
            "reachable": True,
            "models": available_models,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "models": set(),
            "detail": str(exc),
        }
    finally:
        await _close_openai_client(client)


def _derive_health_status(
    provider_probe: dict[str, Any],
    index_state: AIIndexState,
) -> Literal["ok", "degraded"]:
    required_models_ready = (
        settings.AI_CHAT_MODEL in provider_probe["models"]
        and settings.AI_EMBEDDING_MODEL in provider_probe["models"]
    )
    if provider_probe["reachable"] and required_models_ready and index_state.status == "ready":
        return "ok"
    return "degraded"


def _load_index_assets() -> tuple[faiss.Index, list[dict[str, Any]], AIIndexState]:
    index_dir = _resolve_index_dir()
    manifest = _read_manifest(index_dir)
    if manifest is None:
        raise HTTPException(status_code=409, detail="index_missing")

    index_path = _index_file_path(index_dir)
    chunks = manifest.get("chunks")
    if not isinstance(chunks, list) or not chunks:
        raise HTTPException(status_code=409, detail="index_missing")

    index = faiss.read_index(str(index_path))
    ready_state = _index_state_from_storage(prefer_runtime_error=False)
    return index, chunks, ready_state


async def _embed_query(question: str) -> np.ndarray[Any, np.dtype[np.float32]]:
    embedding = await _embed_texts([question])
    return embedding[0]


def _preferred_doc_groups_for_query(query: str) -> tuple[str, ...]:
    lowered_query = query.casefold()
    ansible_keywords = ("앤서블", "ansible", "playbook", "플레이북", "inventory", "role", "yaml", ".yml")
    python_keywords = ("파이썬", "파이선", "python", "함수", "클래스", "type hint", "pep8", "스타일")

    has_ansible = any(keyword in query or keyword in lowered_query for keyword in ansible_keywords)
    has_python = any(keyword in query or keyword in lowered_query for keyword in python_keywords)

    if has_ansible and has_python:
        return ("ansible", "python")
    if has_ansible:
        return ("ansible",)
    if has_python:
        return ("python",)
    return ()


def _filter_candidates_for_query_domain(
    query: str,
    preferred_groups: tuple[str, ...],
    candidates: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    lowered_query = query.casefold()
    if preferred_groups != ("python",) or "ansible" in lowered_query or "앤서블" in query:
        return candidates

    ansible_terms = ("ansible", "앤서블", "playbook", "플레이북", "inventory", "role", "roles", "hosts:")
    python_terms = ("python", "파이썬", "파이선", "pep 8", "pep8", "type hint", "타입", "함수", "클래스", "스타일")
    filtered_candidates = []
    for candidate in candidates:
        source_text = candidate.metadata.get("source", "").casefold()
        preview_text = candidate.text[:200].casefold()
        if any(term in source_text or term in preview_text for term in ansible_terms):
            continue
        if not any(term in source_text or term in preview_text for term in python_terms):
            continue
        filtered_candidates.append(candidate)
    return filtered_candidates


def _search_candidate_chunks(
    index: faiss.Index,
    chunk_payloads: list[dict[str, Any]],
    query_embedding: np.ndarray[Any, np.dtype[np.float32]],
    fetch_k: int,
    preferred_groups: tuple[str, ...] | None = None,
) -> list[RetrievedChunk]:
    if index.ntotal == 0:
        return []

    base_k = min(max(fetch_k, 1), index.ntotal)
    search_k = base_k
    if preferred_groups:
        search_k = min(max(fetch_k * 3, 1), index.ntotal)

    query_vector = np.asarray(query_embedding, dtype="float32").reshape(1, -1)
    faiss_index: Any = index
    distances, indices = faiss_index.search(query_vector, search_k)

    candidates: list[RetrievedChunk] = []
    for raw_distance, raw_index in zip(distances[0].tolist(), indices[0].tolist(), strict=False):
        if raw_index < 0 or raw_index >= len(chunk_payloads):
            continue
        payload = chunk_payloads[raw_index]
        text = payload.get("text")
        metadata = payload.get("metadata")
        if not isinstance(text, str) or not isinstance(metadata, dict):
            continue
        vector = np.asarray(faiss_index.reconstruct(int(raw_index)), dtype="float32")
        candidates.append(
            RetrievedChunk(
                text=text,
                metadata={str(key): str(value) for key, value in metadata.items()},
                distance=float(raw_distance),
                vector=vector,
            )
        )

    if preferred_groups:
        filtered_candidates = [
            candidate
            for candidate in candidates
            if candidate.metadata.get("doc_group") in preferred_groups
        ]
        if filtered_candidates:
            return filtered_candidates[:base_k]
        return candidates[:base_k]

    return candidates


def _cosine_similarity(
    left: np.ndarray[Any, np.dtype[np.float32]],
    right: np.ndarray[Any, np.dtype[np.float32]],
) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if math.isclose(left_norm, 0.0) or math.isclose(right_norm, 0.0):
        return 0.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def _select_relevant_chunks(
    candidates: list[RetrievedChunk],
    query_embedding: np.ndarray[Any, np.dtype[np.float32]],
    top_k: int,
) -> list[RetrievedChunk]:
    if not candidates:
        return []
    if candidates[0].distance > _NO_HIT_DISTANCE_THRESHOLD:
        return []

    remaining = list(candidates)
    selected: list[RetrievedChunk] = []
    query_similarity = {
        id(candidate): _cosine_similarity(query_embedding, candidate.vector)
        for candidate in candidates
    }

    while remaining and len(selected) < top_k:
        best_candidate: RetrievedChunk | None = None
        best_score = -float("inf")
        for candidate in remaining:
            if not selected:
                score = query_similarity[id(candidate)]
            else:
                diversity_penalty = max(
                    _cosine_similarity(candidate.vector, chosen.vector)
                    for chosen in selected
                )
                score = (
                    _MMR_LAMBDA * query_similarity[id(candidate)]
                    - (1.0 - _MMR_LAMBDA) * diversity_penalty
                )
            if score > best_score:
                best_score = score
                best_candidate = candidate
        if best_candidate is None:
            break
        selected.append(best_candidate)
        remaining.remove(best_candidate)
    return selected


def _build_source_items(chunks: list[RetrievedChunk]) -> list[AISourceItem]:
    sources: list[AISourceItem] = []
    for chunk in chunks:
        excerpt = " ".join(chunk.text.split())[:_SOURCE_EXCERPT_LENGTH]
        sources.append(
            AISourceItem(
                source=chunk.metadata["source"],
                filename=chunk.metadata["filename"],
                doc_group=chunk.metadata["doc_group"],
                ext=chunk.metadata["ext"],
                chunk_id=chunk.metadata["chunk_id"],
                excerpt=excerpt,
            )
        )
    return sources


def _build_chat_context(chunks: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        header = (
            f"[{index}] source={chunk.metadata['source']} | "
            f"group={chunk.metadata['doc_group']} | "
            f"ext={chunk.metadata['ext']} | "
            f"chunk_id={chunk.metadata['chunk_id']}"
        )
        blocks.append(f"{header}\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)


def _extract_chat_content(message_content: Any) -> str:
    if isinstance(message_content, str):
        return message_content.strip()
    if isinstance(message_content, list):
        parts: list[str] = []
        for item in message_content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            else:
                text = getattr(item, "text", None)
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n".join(parts).strip()
    return ""





async def _ensure_chat_runtime_ready(*, require_embedding_model: bool = True) -> None:
    provider_probe = await _probe_provider()
    if not provider_probe["reachable"]:
        raise HTTPException(status_code=503, detail="ollama_unreachable")
    installed_models = provider_probe["models"]
    embedding_model_missing = (
        require_embedding_model and settings.AI_EMBEDDING_MODEL not in installed_models
    )
    if settings.AI_CHAT_MODEL not in installed_models or embedding_model_missing:
        raise HTTPException(status_code=503, detail="model_not_installed")


async def get_ai_health() -> AIHealthResponse:
    """Return AI runtime configuration, provider reachability, and index status."""

    provider_probe = await _probe_provider()
    installed_models = provider_probe["models"]
    index_state = _index_state_from_storage(prefer_runtime_error=True)
    status = _derive_health_status(provider_probe, index_state)
    return AIHealthResponse(
        status=status,
        provider="ollama",
        provider_reachable=provider_probe["reachable"],
        base_url=settings.AI_BASE_URL,
        chat_model=settings.AI_CHAT_MODEL,
        chat_model_installed=settings.AI_CHAT_MODEL in installed_models,
        embedding_model=settings.AI_EMBEDDING_MODEL,
        embedding_model_installed=settings.AI_EMBEDDING_MODEL in installed_models,
        timeout_seconds=settings.AI_TIMEOUT_SECONDS,
        index_state=index_state,
    )


async def rebuild_ai_index() -> AIIndexRebuildResponse:
    """Perform a manual full AI index rebuild."""

    if _REBUILD_LOCK.locked():
        raise HTTPException(status_code=409, detail="rebuild_already_in_progress")

    async with _REBUILD_LOCK:
        current_state = _index_state_from_storage(prefer_runtime_error=False)
        building_state = AIIndexState(
            status="building",
            document_count=current_state.document_count,
            chunk_count=current_state.chunk_count,
            last_rebuilt_at=current_state.last_rebuilt_at,
            detail="AI 인덱스를 재빌드하는 중입니다.",
        )
        _set_index_state(building_state)

        try:
            kb_root = _resolve_kb_root()
            index_dir = _resolve_index_dir()
            document_count, chunks = _collect_index_chunks(kb_root)
            if document_count == 0 or not chunks:
                raise RuntimeError("knowledge_base_empty")

            embeddings = await _embed_texts([chunk.text for chunk in chunks])
            index = _build_faiss_index(embeddings)
            rebuilt_at = _utc_now()
            _write_index_atomically(index_dir, index, chunks, document_count, rebuilt_at)

            ready_state = AIIndexState(
                status="ready",
                document_count=document_count,
                chunk_count=len(chunks),
                last_rebuilt_at=rebuilt_at,
                detail="AI 인덱스 재빌드가 완료되었습니다.",
            )
            _set_index_state(ready_state)
            return AIIndexRebuildResponse(
                status="ready",
                message="AI 인덱스 재빌드가 완료되었습니다.",
                document_count=document_count,
                chunk_count=len(chunks),
                index_path=str(index_dir),
                index_state=ready_state,
            )
        except HTTPException:
            raise
        except Exception as exc:
            error_state = AIIndexState(
                status="error",
                document_count=0,
                chunk_count=0,
                last_rebuilt_at=None,
                detail=f"AI 인덱스 재빌드 실패: {exc}",
            )
            _set_index_state(error_state)
            raise HTTPException(status_code=500, detail="ai_index_rebuild_failed") from exc




async def chat_with_ai_stream(request: AIChatRequest) -> AsyncGenerator[str, None]:
    """Answer questions strictly from indexed knowledge-base context (Streaming)."""

    if not request.use_knowledge_base:
        current_index_state = _index_state_from_storage(prefer_runtime_error=True)
        await _ensure_chat_runtime_ready(require_embedding_model=False)

        async def _direct_stream_generator() -> AsyncGenerator[str, None]:
            seq = 1
            output_chunk_count = 0
            output_char_count = 0

            sources_payload = {
                "sources": [],
                "model": settings.AI_CHAT_MODEL,
                "retrieval_count": 0,
                "grounded": False,
                "index_state": current_index_state.model_dump(mode="json"),
            }
            yield _sse_event("sources", sources_payload)

            client = _get_openai_client()
            try:
                stream = await client.chat.completions.create(
                    model=settings.AI_CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": _DIRECT_CHAT_SYSTEM_PROMPT},
                        {"role": "user", "content": request.question},
                    ],
                    stream=True,
                )
                timeline_started = False
                async for chunk in stream:
                    text = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
                    if text:
                        output_chunk_count += 1
                        output_char_count += len(text)
                        yield _sse_event("chunk", text)
                        if not timeline_started:
                            yield _sse_event(
                                "timeline",
                                _timeline_payload(
                                    seq=seq,
                                    stage="request",
                                    status="started",
                                    label="질문 접수 완료",
                                    detail="검색 없이 일반 답변 모드로 바로 처리합니다.",
                                    mode="direct",
                                    counts=AITimelineCounts(
                                        index_document_count=current_index_state.document_count,
                                        index_chunk_count=current_index_state.chunk_count,
                                    ),
                                ),
                            )
                            seq += 1
                            yield _sse_event(
                                "timeline",
                                _timeline_payload(
                                    seq=seq,
                                    stage="generation",
                                    status="started",
                                    label="답변 생성 준비 완료",
                                    detail="모델에 질문을 전달하고 응답 스트리밍을 시작합니다.",
                                    mode="direct",
                                ),
                            )
                            seq += 1
                            yield _sse_event(
                                "timeline",
                                _timeline_payload(
                                    seq=seq,
                                    stage="generation",
                                    status="streaming",
                                    label="첫 답변 스트리밍 시작",
                                    detail="실제 답변 토큰이 도착하기 시작했습니다.",
                                    mode="direct",
                                    counts=AITimelineCounts(
                                        index_document_count=current_index_state.document_count,
                                        index_chunk_count=current_index_state.chunk_count,
                                        output_chunk_count=output_chunk_count,
                                        output_char_count=output_char_count,
                                    ),
                                ),
                            )
                            seq += 1
                            timeline_started = True
                yield _sse_event(
                    "timeline",
                    _timeline_payload(
                        seq=seq,
                        stage="complete",
                        status="completed",
                        label="응답 생성 완료",
                        detail="일반 답변 스트리밍을 마쳤습니다.",
                        mode="direct",
                        counts=AITimelineCounts(
                            output_chunk_count=output_chunk_count,
                            output_char_count=output_char_count,
                        ),
                    ),
                )
            except Exception as exc:
                yield _sse_event(
                    "timeline",
                    _timeline_payload(
                        seq=seq,
                        stage="error",
                        status="failed",
                        label="답변 생성 실패",
                        detail="모델 응답 생성 중 오류가 발생했습니다.",
                        mode="direct",
                        counts=AITimelineCounts(
                            output_chunk_count=output_chunk_count,
                            output_char_count=output_char_count,
                        ),
                    ),
                )
                yield _sse_event("error", str(exc))
            finally:
                await _close_openai_client(client)

        return _direct_stream_generator()

    index, chunk_payloads, ready_index_state = _load_index_assets()
    await _ensure_chat_runtime_ready(require_embedding_model=True)
    query_embedding = await _embed_query(request.question)
    preferred_groups = _preferred_doc_groups_for_query(request.question)
    candidates = _search_candidate_chunks(
        index=index,
        chunk_payloads=chunk_payloads,
        query_embedding=query_embedding,
        fetch_k=settings.AI_RETRIEVAL_FETCH_K,
        preferred_groups=preferred_groups,
    )
    candidates = _filter_candidates_for_query_domain(request.question, preferred_groups, candidates)
    selected_chunks = _select_relevant_chunks(
        candidates=candidates,
        query_embedding=query_embedding,
        top_k=min(settings.AI_RETRIEVAL_K, 3),
    )

    async def _stream_generator() -> AsyncGenerator[str, None]:
        seq = 1
        output_chunk_count = 0
        output_char_count = 0
        base_counts = AITimelineCounts(
            index_document_count=ready_index_state.document_count,
            index_chunk_count=ready_index_state.chunk_count,
            candidate_count=len(candidates),
            selected_count=len(selected_chunks),
            retrieval_count=len(selected_chunks),
        )

        if not selected_chunks:
            sources_payload = {
                "sources": [],
                "model": settings.AI_CHAT_MODEL,
                "retrieval_count": 0,
                "grounded": False,
                "index_state": ready_index_state.model_dump(mode="json"),
            }
            yield _sse_event("sources", sources_payload)
        else:
            sources = _build_source_items(selected_chunks)
            sources_payload = {
                "sources": [s.model_dump(mode="json") for s in sources],
                "model": settings.AI_CHAT_MODEL,
                "retrieval_count": len(selected_chunks),
                "grounded": True,
                "index_state": ready_index_state.model_dump(mode="json"),
            }
            yield _sse_event("sources", sources_payload)

        yield _sse_event(
            "timeline",
            _timeline_payload(
                seq=seq,
                stage="request",
                status="started",
                label="질문 접수 완료",
                detail="지식베이스 기반으로 관련 근거를 찾는 중입니다.",
                mode="knowledge_base",
                counts=base_counts,
            ),
        )
        seq += 1
        yield _sse_event(
            "timeline",
            _timeline_payload(
                seq=seq,
                stage="retrieval",
                status="completed",
                label="문서 탐색 완료",
                detail=f"후보 문서 {len(candidates)}개를 검토하고 근거 청크 {len(selected_chunks)}개를 추렸습니다.",
                mode="knowledge_base",
                counts=base_counts,
            ),
        )
        seq += 1

        if not selected_chunks:
            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="complete",
                    status="no_hit",
                    label="관련 근거를 찾지 못했습니다",
                    detail="현재 인덱싱된 문서 범위 안에서는 충분한 근거를 찾지 못해 고정 안내문을 반환합니다.",
                    mode="knowledge_base",
                    counts=AITimelineCounts(
                        index_document_count=ready_index_state.document_count,
                        index_chunk_count=ready_index_state.chunk_count,
                        candidate_count=len(candidates),
                        selected_count=0,
                        retrieval_count=0,
                    ),
                ),
            )
            yield _sse_event("chunk", _NO_HIT_ANSWER)
            return

        yield _sse_event(
            "timeline",
            _timeline_payload(
                seq=seq,
                stage="sources",
                status="completed",
                label="근거 문서 확보 완료",
                detail=f"응답에 사용할 근거 문서 {len(selected_chunks)}개를 화면에 표시했습니다.",
                mode="knowledge_base",
                counts=base_counts,
            ),
        )
        seq += 1

        context = _build_chat_context(selected_chunks)
        client = _get_openai_client()
        try:
            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="generation",
                    status="started",
                    label="답변 생성 준비 완료",
                    detail="질문과 근거 문서를 모델에 전달하고 있습니다.",
                    mode="knowledge_base",
                    counts=base_counts,
                ),
            )
            seq += 1

            stream = await client.chat.completions.create(
                model=settings.AI_CHAT_MODEL,
                messages=[
                    {"role": "system", "content": _CHAT_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"QUESTION:\n{request.question}\n\nCONTEXT:\n{context}",
                    },
                ],
                stream=True,
            )
            first_chunk_emitted = False
            async for chunk in stream:
                text = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else ""
                if text:
                    output_chunk_count += 1
                    output_char_count += len(text)
                    if not first_chunk_emitted:
                        yield _sse_event(
                            "timeline",
                            _timeline_payload(
                                seq=seq,
                                stage="generation",
                                status="streaming",
                                label="답변 스트리밍 시작",
                                detail="첫 답변 토큰이 도착하여 화면에 표시되기 시작했습니다.",
                                mode="knowledge_base",
                                counts=AITimelineCounts(
                                    **{k: v for k, v in base_counts.model_dump().items() if v is not None},
                                    output_chunk_count=output_chunk_count,
                                    output_char_count=output_char_count,
                                ),
                            ),
                        )
                        seq += 1
                        first_chunk_emitted = True
                    yield _sse_event("chunk", text)

            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="complete",
                    status="completed",
                    label="응답 생성 완료",
                    detail="근거 기반 답변 스트리밍을 모두 마쳤습니다.",
                    mode="knowledge_base",
                    counts=AITimelineCounts(
                        **{k: v for k, v in base_counts.model_dump().items() if v is not None},
                        output_chunk_count=output_chunk_count,
                        output_char_count=output_char_count,
                    ),
                ),
            )
        except Exception as exc:
            yield _sse_event(
                "timeline",
                _timeline_payload(
                    seq=seq,
                    stage="error",
                    status="failed",
                    label="답변 생성 실패",
                    detail="근거 문서를 찾았지만 모델 응답 생성 중 오류가 발생했습니다.",
                    mode="knowledge_base",
                    counts=AITimelineCounts(
                        **{k: v for k, v in base_counts.model_dump().items() if v is not None},
                        output_chunk_count=output_chunk_count,
                        output_char_count=output_char_count,
                    ),
                ),
            )
            yield _sse_event("error", str(exc))
        finally:
            await _close_openai_client(client)

    return _stream_generator()
