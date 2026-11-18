import pytest
import json
import app.api.ai as ai_api

pytestmark = pytest.mark.asyncio

async def test_inspect(async_client, ai_test_env, sample_knowledge_base, monkeypatch):
    ai_service = ai_test_env["ai_service"]
    
    async def _probe_provider():
        return {
            "reachable": True,
            "models": {"test-chat-model", "test-embedding-model"},
        }
        
    from tests.test_ai_api import _fake_embed_texts, _mock_get_openai_client_factory

    monkeypatch.setattr(ai_service, "_probe_provider", _probe_provider)
    monkeypatch.setattr(ai_service, "_embed_texts", lambda texts: _fake_embed_texts(ai_service, texts))
    monkeypatch.setattr(ai_service, "_get_openai_client", _mock_get_openai_client_factory("배포 가이드는 Restart api 작업을 포함합니다."))

    await async_client.post("/api/ai/index/rebuild")

    response = await async_client.post("/api/ai/chat", json={"question": "배포 절차를 알려줘"})
    print("CONTENT:", repr(response.content.decode("utf-8")))

