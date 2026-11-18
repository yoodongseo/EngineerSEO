"""Connection check schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class ManagedInventoryHostConnectionTestResult(BaseModel):
    """Schema for a host-level manual connection test result."""

    project_name: str
    inventory_filename: str
    group_name: str
    host_name: str
    status: Literal["success", "failed", "unknown", "stale"]
    checked_at: Optional[datetime] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None


class ManagedInventoryBulkConnectionTestTarget(BaseModel):
    """Schema for bulk connection-test target identity."""

    scope: Literal["group", "inventory"]
    project_name: str
    inventory_filename: str
    group_name: Optional[str] = None


class ManagedInventoryBulkConnectionTestSummary(BaseModel):
    """Schema for bulk connection-test result summary."""

    total_hosts: int
    success: int
    failed: int
    unknown: int
    stale: int


class ManagedInventoryBulkConnectionTestResult(BaseModel):
    """Schema for bulk connection-test result envelope."""

    target: ManagedInventoryBulkConnectionTestTarget
    summary: ManagedInventoryBulkConnectionTestSummary
    results: list[ManagedInventoryHostConnectionTestResult]


class ManagedInventoryV2HostConnectionCheckResult(BaseModel):
    """Schema for a v2 host-level manual connection check result (no project fields)."""

    host_name: str
    group_name: str
    status: Literal["success", "failed", "unknown", "stale"]
    checked_at: Optional[datetime] = None
    failure_code: Optional[str] = None
    failure_message: Optional[str] = None


class ManagedInventoryV2BulkConnectionCheckTarget(BaseModel):
    """Schema for v2 bulk connection-check target identity."""

    inventory_id: UUID
    scope: Literal["group", "inventory"]
    group_name: Optional[str] = None


class ManagedInventoryV2BulkConnectionCheckSummary(BaseModel):
    total_hosts: int
    success: int
    failed: int
    unknown: int
    stale: int


class ManagedInventoryV2BulkConnectionCheckResult(BaseModel):
    """Schema for v2 bulk connection-check result envelope (no project fields)."""

    target: ManagedInventoryV2BulkConnectionCheckTarget
    summary: ManagedInventoryV2BulkConnectionCheckSummary
    results: list[ManagedInventoryV2HostConnectionCheckResult]
