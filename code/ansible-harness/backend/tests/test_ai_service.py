"""Service-level tests for AI indexing workflow."""

import json

import pytest  # type: ignore[reportMissingImports]
from fastapi import HTTPException  # type: ignore[reportMissingImports]


pytestmark = pytest.mark.asyncio


async def _fake_embed_texts(ai_service, texts: list[str]):
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "재무" in text or "finance" in lowered:
            vectors.append([5.0, 5.0, 5.0])
        elif "playwright_sentinel" in lowered:
            vectors.append([10.0, 10.0, 10.0])
        elif "deploy" in lowered or "restart api" in lowered or "배포" in text or "운영 절차" in text:
            vectors.append([1.0, 0.0, 0.0])
        elif "python" in lowered or "함수" in text or "style" in lowered:
            vectors.append([0.0, 1.0, 0.0])
        else:
            vectors.append([0.0, 0.0, 1.0])
    return ai_service.np.asarray(vectors, dtype="float32")


async def _consume_stream(generator, ai_service=None):
    sources_payload = None
    text = ""
    async for chunk in generator:
        if chunk.startswith("event: sources\ndata: "):
            data = chunk.split("\ndata: ", 1)[1].strip()
            sources_payload = json.loads(data) if not ai_service else ai_service.json.loads(data)
        elif chunk.startswith("event: chunk\ndata: "):
            data = chunk.split("\ndata: ", 1)[1].strip()
            text += json.loads(data) if not ai_service else ai_service.json.loads(data)
    
    class MockState:
        def __init__(self, s):
            self.status = s.get("status")
            self.detail = s.get("detail")
            
    class MockSource:
        def __init__(self, s):
            self.source = s.get("source")
            self.filename = s.get("filename")
            self.doc_group = s.get("doc_group")
            
    class MockResponse:
        def __init__(self):
            payload = sources_payload or {
                "grounded": False,
                "sources": [],
                "model": "",
                "retrieval_count": 0,
                "index_state": {"status": None, "detail": None},
            }
            self.answer = text
            self.grounded = payload["grounded"]
            self.sources = [MockSource(s) for s in payload["sources"]]
            self.model = payload["model"]
            self.retrieval_count = payload["retrieval_count"]
            self.index_state = MockState(payload["index_state"])
            
    return MockResponse()


async def _collect_stream_events(generator, ai_service=None):
    loads = ai_service.json.loads if ai_service else json.loads
    events = []
    async for chunk in generator:
        payload = chunk.strip()
        if not payload:
            continue
        event_name = "message"
        event_data = None
        for line in payload.splitlines():
            if line.startswith("event: "):
                event_name = line.replace("event: ", "", 1)
            elif line.startswith("data: "):
                event_data = loads(line.replace("data: ", "", 1))
        events.append((event_name, event_data))
    return events

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


async def test_collect_index_chunks_filters_extensions_and_adds_metadata(ai_test_env, sample_knowledge_base):
    ai_service = ai_test_env["ai_service"]

    document_count, chunks = ai_service._collect_index_chunks(sample_knowledge_base.resolve())
    sources = {chunk.metadata["source"] for chunk in chunks}
    filenames = {chunk.metadata["filename"] for chunk in chunks}

    assert document_count == 7
    assert chunks
    assert all(chunk.metadata["ext"] in {".txt", ".md", ".html", ".yml", ".py"} for chunk in chunks)
    assert all(chunk.metadata["source"].startswith("knowledge_base/") for chunk in chunks)
    assert all(chunk.metadata["chunk_id"].isdigit() for chunk in chunks)
    assert "knowledge_base/README.md" not in sources
    assert "knowledge_base/WRITING_RULES.md" not in sources
    assert "knowledge_base/python/README.md" in sources
    assert "knowledge_base/ansible/WRITING_RULES.md" in sources
    assert {"README.md", "WRITING_RULES.md"}.issubset(filenames)
    assert {chunk.metadata["doc_group"] for chunk in chunks} == {"python", "ansible"}


async def test_ensure_within_kb_root_rejects_outside_path(ai_test_env, tmp_path):
    ai_service = ai_test_env["ai_service"]
    kb_root = ai_test_env["kb_dir"].resolve()
    outside_file = tmp_path / "outside.md"
    outside_file.write_text("outside", encoding="utf-8")

    with pytest.raises(ValueError):
        ai_service._ensure_within_kb_root(outside_file, kb_root)


async def test_rebuild_ai_index_persists_manifest_and_updates_health(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    index_dir = ai_test_env["index_dir"]

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)

    rebuild_response = await ai_service.rebuild_ai_index()
    health_response = await ai_service.get_ai_health()

    assert rebuild_response.status == "ready"
    assert rebuild_response.document_count == 7
    assert rebuild_response.chunk_count > 0
    assert rebuild_response.index_path.endswith("faiss_index")
    assert rebuild_response.index_state.status == "ready"
    assert (index_dir / "index.faiss").exists()

    manifest = json.loads((index_dir / "metadata.json").read_text(encoding="utf-8"))
    assert manifest["document_count"] == 7
    assert manifest["chunk_count"] == rebuild_response.chunk_count
    assert manifest["embedding_model"] == "test-embedding-model"
    assert health_response.provider_reachable is True
    assert health_response.chat_model_installed is True
    assert health_response.embedding_model_installed is True
    assert health_response.status == "ok"
    assert health_response.index_state.status == "ready"


async def test_ai_index_rebuild_detects_kb_changes(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    kb_dir = ai_test_env["kb_dir"]
    request = ai_test_env["ai_api"].AIChatRequest(question="playwright_sentinel_test_12345")

    async def _probe_provider():
        return {"reachable": True, "models": {"test-chat-model", "test-embedding-model"}}

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("Generated with context"))

    await ai_service.rebuild_ai_index()

    response_before = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)
    assert response_before.grounded is False

    target_file = kb_dir / "python" / "파이선가이드.md"
    target_file.write_text("playwright_sentinel_test_12345", encoding="utf-8")

    await ai_service.rebuild_ai_index()

    response_after = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)
    assert response_after.grounded is True
    assert "Generated with context" in response_after.answer
    assert any("파이선가이드.md" in source.filename for source in response_after.sources)


async def test_get_ai_health_is_degraded_when_provider_unreachable(ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider():
        return {
            "reachable": False,
            "models": set(),
            "detail": "connection refused",
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)

    health_response = await ai_service.get_ai_health()

    assert health_response.status == "degraded"
    assert health_response.provider_reachable is False
    assert health_response.chat_model_installed is False
    assert health_response.embedding_model_installed is False


async def test_get_ai_health_is_degraded_when_required_model_missing(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]

    async def _probe_provider_ready():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    async def _probe_provider_missing_embedding():
        return {
            "reachable": True,
            "models": {"test-chat-model"},
        }

    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider_ready)
    await ai_service.rebuild_ai_index()

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider_missing_embedding)

    health_response = await ai_service.get_ai_health()

    assert health_response.status == "degraded"
    assert health_response.provider_reachable is True
    assert health_response.chat_model_installed is True
    assert health_response.embedding_model_installed is False


async def test_chat_with_ai_returns_grounded_answer(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="배포 절차를 알려줘")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("배포 가이드는 Restart api 작업을 포함합니다."))

    await ai_service.rebuild_ai_index()

    response = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)

    assert response.grounded is True
    assert response.answer.startswith("배포 가이드")
    assert response.model == "test-chat-model"
    assert response.retrieval_count >= 1
    assert response.sources
    assert response.sources[0].source.startswith("knowledge_base/")


async def test_chat_with_ai_returns_no_hit_without_model_call(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="재무 보고서 규칙을 알려줘")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("No hit"))

    await ai_service.rebuild_ai_index()

    response = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)

    assert response.grounded is False
    assert response.sources == []
    assert response.retrieval_count == 0
    assert response.model == "test-chat-model"
    assert "관련 근거" in response.answer


async def test_chat_with_ai_no_hit_emits_observable_timeline(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="재무 보고서 규칙을 알려줘")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("No hit"))

    await ai_service.rebuild_ai_index()

    events = await _collect_stream_events(await ai_service.chat_with_ai_stream(request), ai_service)
    timeline_events = [payload for name, payload in events if name == "timeline"]

    assert [event["stage"] for event in timeline_events] == ["request", "retrieval", "complete"]
    assert timeline_events[-1]["status"] == "no_hit"
    assert timeline_events[-1]["counts"]["selected_count"] == 0
    assert any(name == "chunk" for name, _payload in events)


async def test_chat_with_ai_raises_409_when_index_missing(ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="인덱스 없음")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)

    assert request.use_knowledge_base is True

    with pytest.raises(HTTPException) as exc_info:
        await ai_service.chat_with_ai_stream(request)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "index_missing"


async def test_chat_with_ai_without_kb_streams_empty_sources_then_chunks_without_index(ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(
        question="일반 질문",
        use_knowledge_base=False,
    )

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("KB 없이 직접 응답"))

    events = await _collect_stream_events(await ai_service.chat_with_ai_stream(request), ai_service)

    assert events
    source_events = [payload for event_name, payload in events if event_name == "sources"]
    chunk_events = [payload for event_name, payload in events if event_name == "chunk"]

    assert source_events
    first_payload = source_events[0]
    assert first_payload["sources"] == []
    assert first_payload["grounded"] is False
    assert first_payload["retrieval_count"] == 0
    assert first_payload["model"] == "test-chat-model"
    assert first_payload["index_state"]["status"] == "missing"

    assert chunk_events
    assert any("KB 없이 직접 응답" in chunk for chunk in chunk_events)


async def test_chat_with_ai_without_kb_emits_timeline_events(ai_test_env, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(
        question="일반 질문",
        use_knowledge_base=False,
    )

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("KB 없이 직접 응답"))

    events = await _collect_stream_events(await ai_service.chat_with_ai_stream(request), ai_service)
    timeline_events = [payload for name, payload in events if name == "timeline"]

    assert [event["stage"] for event in timeline_events] == ["request", "generation", "generation", "complete"]
    assert [event["status"] for event in timeline_events] == ["started", "started", "streaming", "completed"]
    assert all(event["mode"] == "direct" for event in timeline_events)
    assert timeline_events[-1]["counts"]["output_char_count"] >= len("KB 없이 직접 응답")


async def test_search_candidate_chunks_prefers_ansible_group_when_query_matches(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    chunk_payloads = [
        {
            "text": "python closest",
            "metadata": {
                "source": "knowledge_base/python/a.md",
                "filename": "a.md",
                "doc_group": "python",
                "ext": ".md",
                "chunk_id": "0",
            },
        },
        {
            "text": "python second",
            "metadata": {
                "source": "knowledge_base/python/b.md",
                "filename": "b.md",
                "doc_group": "python",
                "ext": ".md",
                "chunk_id": "0",
            },
        },
        {
            "text": "ansible farther but preferred",
            "metadata": {
                "source": "knowledge_base/ansible/deploy.yml",
                "filename": "deploy.yml",
                "doc_group": "ansible",
                "ext": ".yml",
                "chunk_id": "0",
            },
        },
    ]

    embeddings = ai_service.np.asarray(
        [[0.1, 0.0], [0.2, 0.0], [0.3, 0.0]],
        dtype="float32",
    )
    index = ai_service._build_faiss_index(embeddings)
    query_embedding = ai_service.np.asarray([0.0, 0.0], dtype="float32")

    preferred_groups = ai_service._preferred_doc_groups_for_query("앤서블 배포 절차")
    candidates = ai_service._search_candidate_chunks(
        index=index,
        chunk_payloads=chunk_payloads,
        query_embedding=query_embedding,
        fetch_k=1,
        preferred_groups=preferred_groups,
    )

    assert preferred_groups == ("ansible",)
    assert len(candidates) == 1
    assert candidates[0].metadata["doc_group"] == "ansible"
    assert candidates[0].metadata["filename"] == "deploy.yml"


async def test_preferred_doc_groups_for_python_query_only_include_python(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    preferred_groups = ai_service._preferred_doc_groups_for_query("파이썬 함수 스타일 예제를 보여줘")

    assert preferred_groups == ("python",)


async def test_preferred_doc_groups_for_mixed_query_return_ansible_and_python(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    preferred_groups = ai_service._preferred_doc_groups_for_query("앤서블과 파이선 규칙을 알려줘")

    assert preferred_groups == ("ansible", "python")


async def test_filter_candidates_for_python_query_removes_ansible_thematic_chunks(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    candidates = [
        ai_service.RetrievedChunk(
            text="# Ansible Playbook 구조\nroles/common/tasks/main.yml 에서 playbook 실행",
            metadata={
                "source": "knowledge_base/python/ansible-mixed.md",
                "filename": "ansible-mixed.md",
                "doc_group": "python",
                "ext": ".md",
                "chunk_id": "0",
            },
            distance=0.1,
            vector=ai_service.np.asarray([0.0, 1.0, 0.0], dtype="float32"),
        ),
        ai_service.RetrievedChunk(
            text="# Python Style\n함수는 짧고 명확하게 유지하며 type hint 를 사용합니다.",
            metadata={
                "source": "knowledge_base/python/python-style.md",
                "filename": "python-style.md",
                "doc_group": "python",
                "ext": ".md",
                "chunk_id": "1",
            },
            distance=0.2,
            vector=ai_service.np.asarray([0.0, 1.0, 0.0], dtype="float32"),
        ),
    ]

    filtered = ai_service._filter_candidates_for_query_domain(
        "파이썬 함수 스타일 예제를 보여줘",
        ("python",),
        candidates,
    )

    assert len(filtered) == 1
    assert filtered[0].metadata["filename"] == "python-style.md"


async def test_filter_candidates_for_mixed_query_keeps_both_domains(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    candidates = [
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

    filtered = ai_service._filter_candidates_for_query_domain(
        "앤서블과 파이선 규칙을 알려줘",
        ("ansible", "python"),
        candidates,
    )

    assert filtered == candidates


async def test_chat_with_ai_prefers_python_related_doc_groups_and_caps_sources(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="파이썬 함수 스타일 예제를 보여줘")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("파이썬 함수 예제는 스타일 가이드를 따르세요."))

    await ai_service.rebuild_ai_index()

    response = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)

    assert response.grounded is True
    assert 1 <= response.retrieval_count <= 3
    assert response.sources
    assert all(source.doc_group == "python" for source in response.sources)
    assert all(source.doc_group != "ansible" for source in response.sources)


async def test_chat_with_ai_mixed_query_can_return_ansible_and_python_sources(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="앤서블과 파이선 규칙을 알려줘")

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

    await ai_service.rebuild_ai_index()

    response = await _consume_stream(await ai_service.chat_with_ai_stream(request), ai_service)

    assert response.grounded is True
    assert response.retrieval_count == 2
    assert {source.doc_group for source in response.sources} == {"ansible", "python"}


async def test_chat_with_ai_grounded_stream_emits_rich_timeline(ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    request = ai_test_env["ai_api"].AIChatRequest(question="배포 절차를 알려줘")

    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("배포 가이드는 Restart api 작업을 포함합니다."))

    await ai_service.rebuild_ai_index()

    events = await _collect_stream_events(await ai_service.chat_with_ai_stream(request), ai_service)
    timeline_events = [payload for name, payload in events if name == "timeline"]

    assert [event["stage"] for event in timeline_events] == [
        "request",
        "retrieval",
        "sources",
        "generation",
        "generation",
        "complete",
    ]
    assert [event["status"] for event in timeline_events] == [
        "started",
        "completed",
        "completed",
        "started",
        "streaming",
        "completed",
    ]
    assert all(event["mode"] == "knowledge_base" for event in timeline_events)
    assert timeline_events[1]["counts"]["candidate_count"] >= timeline_events[1]["counts"]["selected_count"]
    assert timeline_events[-1]["counts"]["output_chunk_count"] >= 1


async def test_select_relevant_chunks_enforces_distance_threshold_strictly(ai_test_env):
    ai_service = ai_test_env["ai_service"]

    query_embedding = ai_service.np.asarray([1.0, 0.0, 0.0], dtype="float32")
    vector = ai_service.np.asarray([1.0, 0.0, 0.0], dtype="float32")

    threshold_edge_candidate = ai_service.RetrievedChunk(
        text="edge",
        metadata={
            "source": "knowledge_base/ansible/edge.md",
            "filename": "edge.md",
            "doc_group": "ansible",
            "ext": ".md",
            "chunk_id": "0",
        },
        distance=ai_service._NO_HIT_DISTANCE_THRESHOLD,
        vector=vector,
    )
    over_threshold_candidate = ai_service.RetrievedChunk(
        text="too far",
        metadata={
            "source": "knowledge_base/ansible/far.md",
            "filename": "far.md",
            "doc_group": "ansible",
            "ext": ".md",
            "chunk_id": "0",
        },
        distance=ai_service._NO_HIT_DISTANCE_THRESHOLD + 0.0001,
        vector=vector,
    )

    selected_at_threshold = ai_service._select_relevant_chunks(
        [threshold_edge_candidate],
        query_embedding,
        top_k=1,
    )
    selected_over_threshold = ai_service._select_relevant_chunks(
        [over_threshold_candidate],
        query_embedding,
        top_k=1,
    )

    assert len(selected_at_threshold) == 1
    assert selected_over_threshold == []
