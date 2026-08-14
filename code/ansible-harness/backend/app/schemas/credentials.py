"""Credential-related schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProjectCredentialCreate(BaseModel):
    """Schema for creating a project-local credential entity."""

    name: str = Field(..., min_length=1, description="credential 표시 이름")
    credential_type: Literal["ssh_password", "ssh_key", "winrm_password", "become_password"] = Field(
        ...,
        description="phase 1 지원 credential 타입",
    )
    username: str = Field(..., min_length=1, description="로그인 사용자명 또는 식별자")
    secret: str = Field(..., min_length=1, description="비밀 원문. contract 단계에서는 응답에 포함하지 않음")


class ProjectCredentialUpdate(BaseModel):
    """Schema for updating project-local credential metadata and optionally rotating the secret."""

    name: str = Field(..., min_length=1, description="credential 표시 이름")
    username: str = Field(..., min_length=1, description="로그인 사용자명 또는 식별자")
    secret: Optional[str] = Field(None, min_length=1, description="새 비밀 원문. 미입력 시 기존 secret 유지")

    model_config = {"extra": "forbid"}


class ProjectCredentialSummary(BaseModel):
    """Schema for non-secret project credential response."""

    ref: str
    name: str
    credential_type: Literal["ssh_password", "ssh_key", "winrm_password", "become_password"]
    username: str
    has_secret: bool = True
    last_rotated_at: Optional[datetime] = None


class InventoryCredentialCreate(BaseModel):
    name: str = Field(..., min_length=1)
    credential_type: Literal["ssh_password", "ssh_key", "winrm_password"]
    username: str = Field(..., min_length=1)
    secret: str = Field(..., min_length=1)
    become_username: Optional[str] = Field(None, min_length=1)
    become_secret: Optional[str] = Field(None, min_length=1)


class InventoryCredentialUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    username: str = Field(..., min_length=1)
    become_username: Optional[str] = Field(None, min_length=1)
    secret: Optional[str] = Field(None, min_length=1)
    become_secret: Optional[str] = Field(None, min_length=1)
    clear_become_secret: bool = False

    model_config = {"extra": "forbid"}


class InventoryCredentialSummary(BaseModel):
    ref: str
    name: str
    credential_type: Literal["ssh_password", "ssh_key", "winrm_password", "become_password"]
    username: str
    become_username: Optional[str] = None
    has_secret: bool = True
    has_become_secret: bool = False
    last_rotated_at: Optional[datetime] = None
