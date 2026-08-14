"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://harness:CHANGE_ME_DB_PASSWORD@localhost:5432/ansible_harness"

    # Ansible
    ANSIBLE_DATA_DIR: str = "/ansible"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Worker 동시 실행 수
    MAX_WORKERS: int = 4

    # Credential encryption
    # Secret write APIs fail if this is empty. Set a stable value in deployment.
    CREDENTIAL_ENCRYPTION_KEY: str = ""
    CREDENTIAL_ENCRYPTION_KEY_ID: str = "default"

    # AI / RAG
    # NOTE: 배포 환경에서는 반드시 env(예: docker compose --env-file)로 주입하세요.
    # 기본값은 배포 특정 IP가 아닌, 로컬 개발에 안전한 값으로 둡니다.
    AI_BASE_URL: str = "http://localhost:11434/v1"
    AI_CHAT_MODEL: str = "gemma4:e4b"
    AI_EMBEDDING_MODEL: str = "ibm/granite-embedding:278m"
    AI_TIMEOUT_SECONDS: int = 120
    AI_KNOWLEDGE_BASE_DIR: str = "/app/knowledge_base"
    AI_INDEX_DIR: str = "/app/data/faiss_index"
    AI_RETRIEVAL_K: int = 3
    AI_RETRIEVAL_FETCH_K: int = 20

    # NVIDIA hosted chat (phase 1: chat only)
    NVIDIA_AI_BASE_URL: str = "https://integrate.api.nvidia.com/v1"
    NVIDIA_AI_API_KEY: str = ""
    NVIDIA_AI_CHAT_MODEL: str = "nvidia/minimaxai/minimax-m2.7"
    NVIDIA_AI_TIMEOUT_SECONDS: int = 120

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
