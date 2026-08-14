"""Job SQLAlchemy model."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, JSON, String, Text, Uuid

from app.database import Base


class Job(Base):
    """Represents an Ansible playbook execution job."""

    __tablename__ = "jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project = Column(String(255), nullable=False)  # 프로젝트명
    playbook = Column(String(255), nullable=False)
    inventory = Column(Text, nullable=True)
    inventory_file = Column(String(255), nullable=True)
    inventory_source_type = Column(String(40), nullable=True)
    managed_inventory_id = Column(Uuid(as_uuid=True), nullable=True)
    managed_inventory_revision = Column(Integer, nullable=True)
    extra_vars = Column(JSON, nullable=True)
    target_scope = Column(String(20), nullable=False, default="inventory")
    target_group_name = Column(String(255), nullable=True)
    target_host_name = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    rc = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    artifact_dir = Column(String(500), nullable=True)

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created_at", "created_at"),
        Index("idx_jobs_project", "project"),
    )

    def __repr__(self):
        return f"<Job {self.id} [{self.status}] {self.project}/{self.playbook}>"


class JobTemplate(Base):
    __tablename__ = "job_templates"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    project = Column(String(255), nullable=False)
    playbook = Column(String(255), nullable=False)
    inventory_id = Column(Uuid(as_uuid=True), nullable=True)
    extra_vars = Column(JSON, nullable=True)
    target_scope = Column(String(20), nullable=False, default="inventory")
    target_group_name = Column(String(255), nullable=True)
    target_host_name = Column(String(255), nullable=True)
    cron_expression = Column(String(100), nullable=True)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

