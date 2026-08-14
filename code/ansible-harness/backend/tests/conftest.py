"""Pytest fixtures for backend AI contract tests."""

import importlib
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio  # type: ignore[reportMissingImports]
from httpx import ASGITransport, AsyncClient  # type: ignore[reportMissingImports]


@pytest.fixture
def ai_test_env(monkeypatch, tmp_path):
    """Prepare isolated AI test settings and reload affected modules."""

    kb_dir = tmp_path / "knowledge_base"
    index_dir = tmp_path / "faiss_index"
    kb_dir.mkdir(parents=True, exist_ok=True)
    index_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("AI_BASE_URL", "http://test-ollama/v1")
    monkeypatch.setenv("AI_CHAT_MODEL", "test-chat-model")
    monkeypatch.setenv("AI_EMBEDDING_MODEL", "test-embedding-model")
    monkeypatch.setenv("AI_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("AI_KNOWLEDGE_BASE_DIR", str(kb_dir))
    monkeypatch.setenv("AI_INDEX_DIR", str(index_dir))
    monkeypatch.setenv("AI_RETRIEVAL_K", "1")
    monkeypatch.setenv("AI_RETRIEVAL_FETCH_K", "2")
    monkeypatch.setenv("NVIDIA_AI_BASE_URL", "https://integrate.api.nvidia.com/v1")
    monkeypatch.setenv("NVIDIA_AI_API_KEY", "test-nvidia-key")
    monkeypatch.setenv("NVIDIA_AI_CHAT_MODEL", "nvidia/test-model")
    monkeypatch.setenv("NVIDIA_AI_TIMEOUT_SECONDS", "7")

    import app.config as config  # type: ignore[reportMissingImports]
    import app.schemas.ai as ai_schemas  # type: ignore[reportMissingImports]
    import app.schemas.nvidia_ai as nvidia_ai_schemas  # type: ignore[reportMissingImports]
    import app.services.ai_service as ai_service  # type: ignore[reportMissingImports]
    import app.services.nvidia_ai_service as nvidia_ai_service  # type: ignore[reportMissingImports]
    import app.api.ai as ai_api  # type: ignore[reportMissingImports]
    import app.api.nvidia_ai as nvidia_ai_api  # type: ignore[reportMissingImports]
    import app.main as main  # type: ignore[reportMissingImports]

    importlib.reload(config)
    importlib.reload(ai_schemas)
    importlib.reload(nvidia_ai_schemas)
    importlib.reload(ai_service)
    importlib.reload(nvidia_ai_service)
    importlib.reload(ai_api)
    importlib.reload(nvidia_ai_api)
    importlib.reload(main)

    return {
        "kb_dir": kb_dir,
        "index_dir": index_dir,
        "config": config,
        "ai_service": ai_service,
        "nvidia_ai_service": nvidia_ai_service,
        "ai_api": ai_api,
        "nvidia_ai_api": nvidia_ai_api,
        "main": main,
    }


@pytest.fixture
def sample_knowledge_base(ai_test_env):
    """Create a representative knowledge base tree for indexing tests."""

    kb_dir = ai_test_env["kb_dir"]
    (kb_dir / "python").mkdir(parents=True, exist_ok=True)
    (kb_dir / "ansible").mkdir(parents=True, exist_ok=True)

    (kb_dir / "python" / "python-style.md").write_text(
        "# Python Style\n\n함수는 짧고 명확하게 유지합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "python" / "README.md").write_text(
        "# Python README\n\n이 파일은 nested 문서라 인덱싱 대상에 남아야 합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "ansible" / "sample.py").write_text(
        "def greet(name: str) -> str:\n    return f'hello {name}'\n",
        encoding="utf-8",
    )
    (kb_dir / "ansible" / "deploy.yml").write_text(
        "- name: Deploy service\n  hosts: all\n  tasks:\n    - name: Restart api\n      ansible.builtin.service:\n        name: api\n        state: restarted\n",
        encoding="utf-8",
    )
    (kb_dir / "python" / "reference.txt").write_text(
        "모든 변경은 작업 로그와 함께 남겨야 합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "ansible" / "operators.html").write_text(
        "<html><body><h1>Operators</h1><p>운영 절차는 단계별로 검증합니다.</p></body></html>",
        encoding="utf-8",
    )
    (kb_dir / "ansible" / "WRITING_RULES.md").write_text(
        "# Ansible Writing Rules\n\n이 파일은 nested 문서라 인덱싱 대상에 남아야 합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "README.md").write_text(
        "# KB 운영 가이드\n\n이 파일은 인덱싱 대상에서 제외되어야 합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "WRITING_RULES.md").write_text(
        "# KB 작성 규칙\n\n이 파일도 인덱싱 대상에서 제외되어야 합니다.\n",
        encoding="utf-8",
    )
    (kb_dir / "ansible" / "ignored.json").write_text('{"skip": true}', encoding="utf-8")
    return kb_dir


@pytest_asyncio.fixture
async def async_client(ai_test_env) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client bound to the FastAPI app."""

    transport = ASGITransport(app=ai_test_env["main"].app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    import app.database as database  # type: ignore[reportMissingImports]

    await database.engine.dispose()
