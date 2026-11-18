"""Managed inventory schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ManagedInventoryHostCreate(BaseModel):
    """Schema for a managed inventory host create row."""

    name: str = Field(..., description="호스트 표시 이름")
    address: str = Field(..., description="호스트 주소 또는 IP")
    connection_type: str = Field("ssh", description="예: ssh, winrm")
    port: int = Field(22, description="연결 포트")
    remote_user: Optional[str] = Field(None, description="원격 로그인 사용자")
    become_enabled: bool = Field(False, description="become 사용 여부")
    become_user: Optional[str] = Field(None, description="become 사용자")
    ansibleharness_login_credential_ref: Optional[str] = Field(None, description="로그인 credential ref")
    ansibleharness_become_credential_ref: Optional[str] = Field(None, description="become credential ref")
    host_vars: Dict[str, Any] = Field(default_factory=dict, description="비밀이 아닌 host vars")

    model_config = {"extra": "forbid"}


class ManagedInventoryGroupCreate(BaseModel):
    """Schema for a managed inventory group create payload."""

    name: str = Field(..., description="그룹 이름")
    hosts: list[ManagedInventoryHostCreate] = Field(default_factory=list, description="그룹 내 host 목록")

    model_config = {"extra": "forbid"}


class ManagedInventoryCreate(BaseModel):
    """Schema for creating a structured managed inventory."""

    filename: str = Field(..., description="생성할 inventory 파일명")
    groups: list[ManagedInventoryGroupCreate] = Field(default_factory=list, description="group-first inventory 구조")

    model_config = {"extra": "forbid"}


class ManagedInventoryUpdate(BaseModel):
    """Schema for updating a structured managed inventory."""

    filename: str = Field(..., description="변경할 inventory 파일명")
    groups: list[ManagedInventoryGroupCreate] = Field(default_factory=list, description="group-first inventory 구조")

    model_config = {"extra": "forbid"}


class ManagedInventoryConnectionStatus(BaseModel):
    """Server-owned host connection status read model."""

    status: Literal["success", "failed", "unknown", "stale"] = "unknown"
    checked_at: Optional[datetime] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None


class ManagedInventoryHost(BaseModel):
    """Schema for a managed inventory host detail row."""

    name: str
    address: str
    connection_type: str
    port: int
    remote_user: Optional[str] = None
    become_enabled: bool = False
    become_user: Optional[str] = None
    ansibleharness_login_credential_ref: Optional[str] = None
    ansibleharness_become_credential_ref: Optional[str] = None
    host_vars: Dict[str, Any] = Field(default_factory=dict)
    connection_status: ManagedInventoryConnectionStatus = Field(default_factory=ManagedInventoryConnectionStatus)


class ManagedInventoryGroup(BaseModel):
    """Schema for a managed inventory group."""

    name: str = Field(..., description="그룹 이름")
    hosts: list[ManagedInventoryHost] = Field(default_factory=list, description="그룹 내 host 목록")


class ManagedInventoryDetail(BaseModel):
    """Schema for managed inventory detail response."""

    name: str
    path: str
    status_summary: str
    rendered_content: str
    groups: list[ManagedInventoryGroup]


class ManagedInventoryListItem(BaseModel):
    """Schema for managed inventory list response item."""

    name: str
    path: str
    status_summary: str


class ManagedInventoryV2HostCreate(BaseModel):
    key: Optional[str] = None
    name: str
    address: str
    connection_type: str = "ssh"
    port: int = 22
    remote_user: Optional[str] = None
    become_enabled: bool = False
    become_user: Optional[str] = None
    login_credential_ref: Optional[str] = None
    become_credential_ref: Optional[str] = None
    host_vars: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class ManagedInventoryV2GroupCreate(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)
    group_vars: Dict[str, Any] = Field(default_factory=dict)
    hosts: list[ManagedInventoryV2HostCreate] = Field(default_factory=list)
    host_keys: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_preview_zone(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "tags" in value:
            return value
        group_vars = value.get("group_vars")
        if not isinstance(group_vars, dict):
            return value
        preview_zone = group_vars.get("_preview_zone")
        if not isinstance(preview_zone, str):
            return value
        stripped = preview_zone.strip()
        if not stripped:
            return value
        return {**value, "tags": [stripped]}


class ManagedInventoryV2HostAssetCreate(BaseModel):
    key: str
    name: str
    address: str
    connection_type: str = "ssh"
    port: int = 22
    remote_user: Optional[str] = None
    become_enabled: bool = False
    become_user: Optional[str] = None
    login_credential_ref: Optional[str] = None
    become_credential_ref: Optional[str] = None
    host_vars: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


class ManagedInventoryV2Membership(BaseModel):
    group_name: str
    host_key: str

    model_config = {"extra": "forbid"}


def _apply_legacy_badges(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    legacy_badges = value.get("badges")
    if "tags" in value:
        return {key: item for key, item in value.items() if key != "badges"}
    if legacy_badges is None:
        return value
    normalized = {key: item for key, item in value.items() if key != "badges"}
    normalized["tags"] = legacy_badges
    return normalized


class ManagedInventoryV2Create(BaseModel):
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    groups: list[ManagedInventoryV2GroupCreate] = Field(default_factory=list)
    hosts: list[ManagedInventoryV2HostAssetCreate] = Field(default_factory=list)
    memberships: list[ManagedInventoryV2Membership] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_badges(cls, value: Any) -> Any:
        return _apply_legacy_badges(value)


class ManagedInventoryV2Update(BaseModel):
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    groups: list[ManagedInventoryV2GroupCreate] = Field(default_factory=list)
    hosts: list[ManagedInventoryV2HostAssetCreate] = Field(default_factory=list)
    memberships: list[ManagedInventoryV2Membership] = Field(default_factory=list)

    model_config = {"extra": "forbid"}

    @model_validator(mode="before")
    @classmethod
    def _apply_legacy_badges(cls, value: Any) -> Any:
        return _apply_legacy_badges(value)


class ManagedInventoryV2Host(BaseModel):
    key: Optional[str] = None
    name: str
    address: str
    connection_type: str
    port: int
    remote_user: Optional[str] = None
    become_enabled: bool = False
    become_user: Optional[str] = None
    login_credential_ref: Optional[str] = None
    become_credential_ref: Optional[str] = None
    host_vars: Dict[str, Any] = Field(default_factory=dict)
    connection_status: ManagedInventoryConnectionStatus = Field(default_factory=ManagedInventoryConnectionStatus)


class ManagedInventoryV2HostAssetMembership(BaseModel):
    inventory_id: UUID
    inventory_name: str
    group_name: str


class ManagedInventoryV2HostAssetDetail(ManagedInventoryV2Host):
    id: UUID
    memberships: list[ManagedInventoryV2HostAssetMembership] = Field(default_factory=list)


class ManagedInventoryV2HostAssetUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    connection_type: Optional[str] = None
    port: Optional[int] = None
    remote_user: Optional[str] = None
    become_enabled: Optional[bool] = None
    become_user: Optional[str] = None
    login_credential_ref: Optional[str] = None
    become_credential_ref: Optional[str] = None
    host_vars: Optional[Dict[str, Any]] = None

    model_config = {"extra": "forbid"}


class ManagedInventoryV2HostAttach(BaseModel):
    host_id: UUID
    group_name: str

    model_config = {"extra": "forbid"}


class ManagedInventoryV2Group(BaseModel):
    name: str
    tags: list[str] = Field(default_factory=list)
    group_vars: Dict[str, Any] = Field(default_factory=dict)
    host_keys: list[str] = Field(default_factory=list)
    hosts: list[ManagedInventoryV2Host] = Field(default_factory=list)


class ManagedInventoryV2ListItem(BaseModel):
    id: UUID
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    revision: int
    source_type: str
    group_count: int = 0
    host_count: int = 0


class ManagedInventoryV2Detail(BaseModel):
    id: UUID
    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    revision: int
    source_type: str
    rendered_content: str
    groups: list[ManagedInventoryV2Group]
    hosts: list[ManagedInventoryV2Host]
    memberships: list[ManagedInventoryV2Membership]


class InventoryMigrationResult(BaseModel):
    migrated: int
    skipped_existing: int
    errors: list[str] = Field(default_factory=list)
