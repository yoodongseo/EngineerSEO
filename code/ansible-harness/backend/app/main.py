"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.jobs import router as jobs_router
from app.api.nvidia_ai import router as nvidia_ai_router
from app.api.project_managed_inventories import router as project_managed_inventories_router
from app.api.projects import router as projects_router
from app.api.job_templates import router as job_templates_router
from app.config import settings
from app.database import init_db
from app.scheduler import start_scheduler
from app import models as _models  # noqa: F401 - registers SQLAlchemy metadata

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    logger.info("🚀 Ansible Harness starting up...")
    await init_db()
    logger.info("✅ Database initialized")
    logger.info(f"📁 Ansible data dir: {settings.ANSIBLE_DATA_DIR}")
    
    await start_scheduler()

    yield

    # Shutdown
    logger.info("👋 Ansible Harness shutting down...")


app = FastAPI(
    title="Ansible Harness",
    description="Ansible 플레이북 실행 및 관리 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(projects_router)
app.include_router(project_managed_inventories_router)
app.include_router(jobs_router)
app.include_router(job_templates_router)
app.include_router(ai_router)
app.include_router(nvidia_ai_router)


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "ansible-harness"}
