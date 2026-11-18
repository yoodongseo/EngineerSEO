"""DB-backed managed inventory models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class ManagedInventory(Base):
    """Structured inventory owned by the application."""

    __tablename__ = "managed_inventories"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    groups = relationship(
        "ManagedInventoryGroup",
        back_populates="inventory",
        cascade="all, delete-orphan",
        order_by="ManagedInventoryGroup.position",
    )

    __table_args__ = (
        Index("uq_managed_inventories_project_filename", "project_name", "filename", unique=True),
        Index("idx_managed_inventories_project", "project_name"),
    )


class ManagedInventoryGroup(Base):
    """A group inside a managed inventory."""

    __tablename__ = "managed_inventory_groups"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    group_vars = Column(JSON, nullable=False, default=dict)

    inventory = relationship("ManagedInventory", back_populates="groups")
    hosts = relationship(
        "ManagedInventoryHost",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="ManagedInventoryHost.position",
    )

    __table_args__ = (Index("idx_managed_inventory_groups_inventory", "inventory_id"),)


class ManagedInventoryHost(Base):
    """A host row inside a managed inventory group."""

    __tablename__ = "managed_inventory_hosts"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventory_groups.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    connection_type = Column(String(40), nullable=False, default="ssh")
    port = Column(Integer, nullable=False, default=22)
    remote_user = Column(String(255), nullable=True)
    become_enabled = Column(Boolean, nullable=False, default=False)
    become_user = Column(String(255), nullable=True)
    ansibleharness_login_credential_ref = Column(String(80), nullable=True)
    ansibleharness_become_credential_ref = Column(String(80), nullable=True)
    host_vars = Column(JSON, nullable=False, default=dict)
    position = Column(Integer, nullable=False, default=0)
    connection_status = Column(String(20), nullable=False, default="unknown")
    checked_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(80), nullable=True)
    failure_message = Column(String(500), nullable=True)

    group = relationship("ManagedInventoryGroup", back_populates="hosts")

    __table_args__ = (Index("idx_managed_inventory_hosts_group", "group_id"),)
