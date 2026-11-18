"""NVIDIA AI API contract tests (offline, mocked)."""

import json

import pytest  # type: ignore[reportMissingImports]


pytestmark = pytest.mark.asyncio


class MockStream:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks

    async def __aiter__(self):
        for text in self.chunks:
            class Delta:
                content = text

            class Choice:
                delta = Delta()

            class Chunk:
                choices = [Choice()]

            yield Chunk()


class MockCompletions:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks

    async def create(self, **kwargs):
        return MockStream(self.chunks)


class MockChat:
    def __init__(self, chunks: list[str]):
        self.completions = MockCompletions(chunks)


class MockModels:
    def __init__(self, model_ids: list[str]):
        self.model_ids = model_ids

    async def list(self):
        class Model:
            def __init__(self, model_id: str):
                self.id = model_id

        class Response:
            data = [Model(model_id) for model_id in self.model_ids]

        return Response()


class MockOpenAIClient:
    def __init__(self, chunks: list[str], model_ids: list[str] | None = None):
        self.chat = MockChat(chunks)
        self.models = MockModels(model_ids or ["nvidia/test-model"])

    async def close(self):
        pass


def _mock_get_nvidia_client_factory(chunks: list[str]):
    def _get():
        return MockOpenAIClient(chunks)

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


async def test_nvidia_ai_health_is_ok_when_provider_and_model_are_available(async_client, ai_test_env, monkeypatch):
    nvidia_ai_service = ai_test_env["nvidia_ai_service"]

    async def _probe_nvidia_provider():
        return {
            "reachable": True,
            "models": {"nvidia/test-model"},
        }

    monkeypatch.setattr(nvidia_ai_service, "_probe_nvidia_provider", _probe_nvidia_provider)

    response = await async_client.get("/api/nvidia-ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["provider"] == "nvidia"
    assert payload["provider_reachable"] is True
    assert payload["chat_model"] == "nvidia/test-model"
    assert payload["chat_model_installed"] is True
    assert payload["capabilities"] == {
        "chat": True,
        "streaming": True,
        "knowledge_base": False,
        "index_rebuild": False,
        "sources": False,
        "timeline": True,
    }


async def test_nvidia_ai_health_is_degraded_when_provider_is_unreachable(async_client, ai_test_env, monkeypatch):
    nvidia_ai_service = ai_test_env["nvidia_ai_service"]

    async def _probe_nvidia_provider():
        return {
            "reachable": False,
            "models": set(),
            "detail": "connection refused",
        }

    monkeypatch.setattr(nvidia_ai_service, "_probe_nvidia_provider", _probe_nvidia_provider)

    response = await async_client.get("/api/nvidia-ai/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["provider"] == "nvidia"
    assert payload["provider_reachable"] is False
    assert payload["chat_model_installed"] is False
    assert payload["detail"] == "connection refused"


async def test_nvidia_ai_chat_streams_meta_timeline_and_chunks(async_client, ai_test_env, monkeypatch):
    nvidia_ai_service = ai_test_env["nvidia_ai_service"]

    monkeypatch.setattr(
        nvidia_ai_service,
        "_get_nvidia_client",
        _mock_get_nvidia_client_factory(["안녕하세요", " NVIDIA 입니다."]),
    )

    response = await async_client.post("/api/nvidia-ai/chat", json={"question": "인사해줘"})

    assert response.status_code == 200
    events = _parse_sse_events(response.text)
    names = [name for name, _ in events]
    assert names[0] == "timeline"
    assert names[1] == "meta"
    assert "chunk" in names
    assert names[-1] == "timeline"

    meta_payload = next(payload for name, payload in events if name == "meta")
    assert meta_payload["provider"] == "nvidia"
    assert meta_payload["grounded"] is False
    assert meta_payload["model"] == "nvidia/test-model"

    chunk_payloads = [payload for name, payload in events if name == "chunk"]
    assert chunk_payloads[-1]["answer_so_far"] == "안녕하세요 NVIDIA 입니다."
    assert all(payload["provider"] == "nvidia" for payload in chunk_payloads)
