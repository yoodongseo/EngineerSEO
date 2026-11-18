"""Project-scoped credential models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text, Uuid

from app.database import Base


class ProjectCredential(Base):
    """Encrypted credential metadata and secret for one project."""

    __tablename__ = "project_credentials"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name = Column(String(255), nullable=False)
    ref = Column(String(80), nullable=False)
    name = Column(String(255), nullable=False)
    credential_type = Column(String(40), nullable=False)
    username = Column(String(255), nullable=False)
    encrypted_secret = Column(Text, nullable=False)
    nonce = Column(String(128), nullable=False)
    key_id = Column(String(80), nullable=False, default="default")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_rotated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("uq_project_credentials_project_ref", "project_name", "ref", unique=True),
        Index("idx_project_credentials_project", "project_name"),
    )
