"""Top-level inventory v2 domain models."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import relationship

from app.database import Base


class ManagedInventoryV2(Base):
    __tablename__ = "managed_inventories_v2"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False, default="")
    tags = Column(JSON, nullable=False, default=list)
    badges = Column(JSON, nullable=False, default=list)
    revision = Column(Integer, nullable=False, default=1)
    source_type = Column(String(40), nullable=False, default="native")
    source_legacy_project = Column(String(255), nullable=True)
    source_legacy_filename = Column(String(255), nullable=True)
    source_legacy_inventory_id = Column(Uuid(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    groups = relationship(
        "ManagedInventoryV2Group",
        back_populates="inventory",
        cascade="all, delete-orphan",
        order_by="ManagedInventoryV2Group.position",
    )
    host_memberships = relationship(
        "ManagedInventoryV2HostMembership",
        back_populates="inventory",
        cascade="all, delete-orphan",
        order_by="ManagedInventoryV2HostMembership.position",
    )
    credentials = relationship(
        "InventoryCredential",
        back_populates="inventory",
        cascade="all, delete-orphan",
        order_by="InventoryCredential.name",
    )


class ManagedInventoryV2Group(Base):
    __tablename__ = "managed_inventory_v2_groups"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventories_v2.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    tags = Column(JSON, nullable=False, default=list)
    group_vars = Column(JSON, nullable=False, default=dict)

    inventory = relationship("ManagedInventoryV2", back_populates="groups")
    host_memberships = relationship(
        "ManagedInventoryV2HostMembership",
        back_populates="group",
        cascade="all, delete-orphan",
        order_by="ManagedInventoryV2HostMembership.position",
    )

    __table_args__ = (Index("idx_managed_inventory_v2_groups_inventory", "inventory_id"),)


class ManagedInventoryV2Host(Base):
    __tablename__ = "managed_inventory_v2_hosts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventory_v2_groups.id", ondelete="SET NULL"), nullable=True)
    host_key = Column(String(120), nullable=True)
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    connection_type = Column(String(40), nullable=False, default="ssh")
    port = Column(Integer, nullable=False, default=22)
    remote_user = Column(String(255), nullable=True)
    become_enabled = Column(Boolean, nullable=False, default=False)
    become_user = Column(String(255), nullable=True)
    login_credential_ref = Column(String(80), nullable=True)
    become_credential_ref = Column(String(80), nullable=True)
    host_vars = Column(JSON, nullable=False, default=dict)
    position = Column(Integer, nullable=False, default=0)
    connection_status = Column(String(20), nullable=False, default="unknown")
    checked_at = Column(DateTime(timezone=True), nullable=True)
    failure_code = Column(String(80), nullable=True)
    failure_message = Column(String(500), nullable=True)

    group = relationship("ManagedInventoryV2Group")
    memberships = relationship(
        "ManagedInventoryV2HostMembership",
        back_populates="host",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_managed_inventory_v2_hosts_group", "group_id"),
        Index("idx_managed_inventory_v2_hosts_host_key", "host_key"),
    )


class ManagedInventoryV2HostMembership(Base):
    __tablename__ = "managed_inventory_v2_host_memberships"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventories_v2.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventory_v2_groups.id", ondelete="CASCADE"), nullable=False)
    host_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventory_v2_hosts.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    inventory = relationship("ManagedInventoryV2", back_populates="host_memberships")
    group = relationship("ManagedInventoryV2Group", back_populates="host_memberships")
    host = relationship("ManagedInventoryV2Host", back_populates="memberships")

    __table_args__ = (
        Index("idx_managed_inventory_v2_host_memberships_inventory", "inventory_id"),
        Index("idx_managed_inventory_v2_host_memberships_group", "group_id"),
        Index("idx_managed_inventory_v2_host_memberships_host", "host_id"),
    )


class InventoryCredential(Base):
    __tablename__ = "inventory_credentials"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    inventory_id = Column(Uuid(as_uuid=True), ForeignKey("managed_inventories_v2.id", ondelete="CASCADE"), nullable=False)
    ref = Column(String(80), nullable=False)
    name = Column(String(255), nullable=False)
    credential_type = Column(String(40), nullable=False)
    username = Column(String(255), nullable=False)
    become_username = Column(String(255), nullable=True)
    encrypted_secret = Column(Text, nullable=False)
    nonce = Column(String(128), nullable=False)
    encrypted_become_secret = Column(Text, nullable=True)
    become_nonce = Column(String(128), nullable=True)
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

    inventory = relationship("ManagedInventoryV2", back_populates="credentials")

    __table_args__ = (
        Index("uq_inventory_credentials_inventory_ref", "inventory_id", "ref", unique=True),
        Index("idx_inventory_credentials_inventory", "inventory_id"),
    )


class GlobalCredential(Base):
    """Application-wide credential shared by every inventory, group, and host."""

    __tablename__ = "global_credentials"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ref = Column(String(80), nullable=False)
    name = Column(String(255), nullable=False)
    credential_type = Column(String(40), nullable=False)
    username = Column(String(255), nullable=False)
    become_username = Column(String(255), nullable=True)
    encrypted_secret = Column(Text, nullable=False)
    nonce = Column(String(128), nullable=False)
    encrypted_become_secret = Column(Text, nullable=True)
    become_nonce = Column(String(128), nullable=True)
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
        Index("uq_global_credentials_ref", "ref", unique=True),
        Index("idx_global_credentials_active_name", "is_active", "name"),
    )
