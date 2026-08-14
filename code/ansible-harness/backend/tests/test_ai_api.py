"""AI API contract tests (offline, mocked)."""

import json

import pytest  # type: ignore[reportMissingImports]


pytestmark = pytest.mark.asyncio


async def _fake_embed_texts(ai_service, texts: list[str]):
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "재무" in text or "finance" in lowered:
            vectors.append([5.0, 5.0, 5.0])
        elif "deploy" in lowered or "restart api" in lowered or "배포" in text or "운영 절차" in text:
            vectors.append([1.0, 0.0, 0.0])
        elif "python" in lowered or "함수" in text or "style" in lowered:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return ai_service.np.asarray(vectors, dtype="float32")


class MockStream:
    def __init__(self, text):
        self.text = text
    async def __aiter__(self):
        class Delta:
            content = self.text
        class Choice:
            delta = Delta()
        class Chunk:
            choices = [Choice()]
        yield Chunk()

class MockCompletions:
    def __init__(self, text):
        self.text = text
    async def create(self, **kwargs):
        return MockStream(self.text)

class MockChat:
    def __init__(self, text):
        self.completions = MockCompletions(text)

class MockOpenAIClient:
    def __init__(self, text):
        self.chat = MockChat(text)
    async def close(self):
        pass
        
def _mock_get_openai_client_factory(answer_text="Mocked answer"):
    def _get():
        return MockOpenAIClient(answer_text)
    return _get


def _parse_sse_events(content: str):
    events = []
    for block in content.split("\n\n"):
        payload = block.strip()
        if not payload:
            continue
        event_name = "message"
        event_data = None
        for line in payload.splitlines():
            if line.startswith("event: "):
                event_name = line.replace("event: ", "", 1)
            elif line.startswith("data: "):
                event_data = json.loads(line.replace("data: ", "", 1))
        events.append((event_name, event_data))
    return events


async def test_ai_health_is_degraded_when_index_missing(async_client, ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)

    response = await async_client.get("/api/ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    for field in (
        "provider",
        "provider_reachable",
        "base_url",
        "chat_model",
        "chat_model_installed",
        "embedding_model",
        "embedding_model_installed",
        "timeout_seconds",
    ):
        assert field in payload
    assert payload["provider_reachable"] is True
    assert payload["chat_model_installed"] is True
    assert payload["embedding_model_installed"] is True
    assert payload["index_state"]["status"] == "missing"
    for field in ("status", "document_count", "chunk_count", "last_rebuilt_at", "detail"):
        assert field in payload["index_state"]


async def test_ai_health_is_degraded_when_provider_unreachable(async_client, ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": False,
            "models": set(),
            "detail": "connection refused",
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)

    response = await async_client.get("/api/ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["provider_reachable"] is False
    assert payload["chat_model_installed"] is False
    assert payload["embedding_model_installed"] is False


async def test_ai_health_is_ok_when_provider_models_and_index_ready(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.get("/api/ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["index_state"]["status"] == "ready"


async def test_ai_index_rebuild_contract(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    index_dir = ai_test_env["index_dir"]

    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))

    response = await async_client.post("/api/ai/index/rebuild")

    assert response.status_code == 200
    payload = response.json()
    for field in ("status", "message", "document_count", "chunk_count", "index_path", "index_state"):
        assert field in payload
    assert payload["status"] == "ready"
    assert payload["document_count"] > 0
    assert payload["chunk_count"] > 0
    assert payload["index_path"].endswith("faiss_index")
    assert payload["index_state"]["status"] == "ready"
    assert (index_dir / "index.faiss").exists()
    manifest = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    assert manifest["document_count"] == payload["document_count"]
    assert manifest["chunk_count"] == payload["chunk_count"]
    assert manifest["chunks"]
    first_chunk = manifest["chunks"][0]
    assert first_chunk["metadata"]["source"].startswith("knowledge_base/")
    for field in ("source", "filename", "ext", "doc_group", "chunk_id", "language"):
        assert field in first_chunk["metadata"]


async def test_ai_index_rebuild_returns_409_on_concurrent_lock(async_client, ai_test_env):
    ai_service = ai_test_env["ai_service"]

    await ai_service._REBUILD_LOCK.acquire()
    try:
        response = await async_client.post("/api/ai/index/rebuild")
    finally:
        ai_service._REBUILD_LOCK.release()

    assert response.status_code == 409
    assert response.json()["detail"] == "rebuild_already_in_progress"


async def test_ai_chat_returns_grounded_answer(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("배포 가이드는 Restart api 작업을 포함합니다."))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.post("/api/ai/chat", json={"question": "배포 절차를 알려줘"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    source_line = [line for line in content.split("\n") if line.startswith("data: ")][0]
    payload = json.loads(source_line.replace("data: ", ""))

    assert payload["grounded"] is True
    assert payload["retrieval_count"] >= 1
    assert payload["model"] == "test-chat-model"
    assert payload["index_state"]["status"] == "ready"
    assert payload["sources"]
    assert payload["sources"][0]["source"].startswith("knowledge_base/")
    assert payload["sources"][0]["excerpt"]


async def test_ai_chat_python_query_prefers_python_doc_groups_and_caps_sources(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("파이썬 예제는 타입과 스타일을 맞춰 작성합니다."))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.post("/api/ai/chat", json={"question": "파이썬 함수 스타일 예제를 보여줘"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    source_line = [line for line in content.split("\n") if line.startswith("data: ")][0]
    payload = json.loads(source_line.replace("data: ", ""))

    assert payload["grounded"] is True
    assert 1 <= payload["retrieval_count"] <= 3
    assert payload["sources"]
    assert all(source["doc_group"] == "python" for source in payload["sources"])
    assert all(source["doc_group"] != "ansible" for source in payload["sources"])
    assert all("ansible" not in source["excerpt"].casefold() for source in payload["sources"])


async def test_ai_chat_mixed_query_can_return_ansible_and_python_sources(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    def _search_candidate_chunks(*args, **kwargs):
        return [
            ai_service.RetrievedChunk(
                text="# Ansible Rule\n플레이북 변수 규칙입니다.",
                metadata={
                    "source": "knowledge_base/ansible/ansible-rule.md",
                    "filename": "ansible-rule.md",
                    "doc_group": "ansible",
                    "ext": ".md",
                    "chunk_id": "0",
                },
                distance=0.1,
                vector=ai_service.np.asarray([1.0, 0.0, 0.0], dtype="float32"),
            ),
            ai_service.RetrievedChunk(
                text="# Python Rule\n함수 스타일 규칙입니다.",
                metadata={
                    "source": "knowledge_base/python/python-rule.md",
                    "filename": "python-rule.md",
                    "doc_group": "python",
                    "ext": ".md",
                    "chunk_id": "1",
                },
                distance=0.2,
                vector=ai_service.np.asarray([0.0, 1.0, 0.0], dtype="float32"),
            ),
        ]

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_search_candidate_chunks", _search_candidate_chunks)
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("두 규칙을 함께 설명합니다."))
    monkeypatch.setattr(ai_service.settings, "AI_RETRIEVAL_K", 2)

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.post("/api/ai/chat", json={"question": "앤서블과 파이선 규칙을 알려줘"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    source_line = [line for line in content.split("\n") if line.startswith("data: ")][0]
    payload = json.loads(source_line.replace("data: ", ""))

    assert payload["grounded"] is True
    assert payload["retrieval_count"] == 2
    assert {source["doc_group"] for source in payload["sources"]} == {"ansible", "python"}


async def test_ai_chat_no_hit_returns_empty_sources(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("No hit"))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.post("/api/ai/chat", json={"question": "재무 보고서 규칙을 알려줘"})

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    source_line = [line for line in content.split("\n") if line.startswith("data: ")][0]
    payload = json.loads(source_line.replace("data: ", ""))

    assert payload["grounded"] is False
    assert payload["sources"] == []
    assert payload["retrieval_count"] == 0
    assert payload["model"] == "test-chat-model"
    assert "관련 근거" in content


async def test_ai_chat_missing_index_returns_409(async_client):
    response = await async_client.post("/api/ai/chat", json={"question": "인덱스 없음"})

    assert response.status_code == 409
    assert response.json()["detail"] == "index_missing"


async def test_ai_chat_without_kb_streams_sources_then_chunks_without_index(async_client, ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("KB 없이 직접 응답"))

    response = await async_client.post(
        "/api/ai/chat",
        json={"question": "일반 질문", "use_knowledge_base": False},
    )

    assert response.status_code == 200
    events = _parse_sse_events(response.content.decode("utf-8"))
    assert events
    assert events[0][0] == "sources"
    sources_payload = events[0][1]
    assert sources_payload["sources"] == []
    assert sources_payload["grounded"] is False
    assert sources_payload["retrieval_count"] == 0
    assert sources_payload["model"] == "test-chat-model"
    assert "status" in sources_payload["index_state"]
    assert len(events) >= 2
    assert events[1][0] == "chunk"
    assert "KB 없이 직접 응답" in events[1][1]


async def test_ai_chat_provider_unreachable_returns_503(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": False,
            "models": set(),
            "detail": "connection refused",
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    response = await async_client.post("/api/ai/chat", json={"question": "연결 실패"})

    assert response.status_code == 503
    assert response.json()["detail"] == "ollama_unreachable"


async def test_ai_chat_missing_model_returns_503(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider_ready():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    async def _probe_provider_missing_model():
        return {
            "reachable": True,
            "models": {"test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider_ready)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))

    rebuild_response = await async_client.post("/api/ai/index/rebuild")
    assert rebuild_response.status_code == 200

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider_missing_model)

    response = await async_client.post("/api/ai/chat", json={"question": "모델 누락"})

    assert response.status_code == 503
    assert response.json()["detail"] == "model_not_installed"
