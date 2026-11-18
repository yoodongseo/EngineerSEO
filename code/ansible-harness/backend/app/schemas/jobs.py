"""Job execution and log schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    project: str = Field(..., description="프로젝트명 (예: infra-deploy)")
    playbook: str = Field(..., description="플레이북 경로 (예: playbooks/site.yml)")
    inventory: Optional[str] = Field(None, description="직접 입력한 인벤토리 내용")
    inventory_file: Optional[str] = Field(None, description="선택한 인벤토리 파일명")
    managed_inventory_id: Optional[UUID] = Field(None, description="v2 managed inventory ID")
    extra_vars: Optional[Dict[str, Any]] = Field(None, description="추가 변수 (JSON)")
    target_scope: Literal["inventory", "group", "host"] = Field("inventory", description="실행 대상 범위")
    
    # Updated for multi-select
    target_group_names: Optional[List[str]] = Field(None, description="선택한 그룹명들")
    target_host_names: Optional[List[str]] = Field(None, description="선택한 호스트명들")
    
    # Added for scoped variables
    inventory_vars: Optional[Dict[str, Any]] = Field(None, description="인벤토리 전역 변수")
    group_vars: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="그룹별 변수")
    host_vars: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="호스트별 변수")

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_target_scope(self) -> JobCreate:
        # Normalize empty lists to None
        if self.target_group_names is not None and len(self.target_group_names) == 0:
            self.target_group_names = None
        if self.target_host_names is not None and len(self.target_host_names) == 0:
            self.target_host_names = None

        if self.target_scope == "inventory":
            if self.target_group_names or self.target_host_names:
                raise ValueError("target_group_names and target_host_names are not allowed for inventory scope")
        elif self.target_scope == "group":
            if not self.target_group_names:
                raise ValueError("target_group_names is required for group scope")
            if self.target_host_names:
                raise ValueError("target_host_names is not allowed for group scope")
        elif self.target_scope == "host":
            if not self.target_host_names:
                raise ValueError("target_host_names is required for host scope")

        return self


class JobResponse(BaseModel):
    """Schema for job response."""

    id: UUID
    project: str
    playbook: str
    inventory: Optional[str] = None
    inventory_file: Optional[str] = None
    inventory_source_type: Optional[str] = None
    managed_inventory_id: Optional[UUID] = None
    managed_inventory_revision: Optional[int] = None
    extra_vars: Optional[Dict[str, Any]] = None
    target_scope: Literal["inventory", "group", "host"] = "inventory"
    target_group_name: Optional[str] = None
    target_host_name: Optional[str] = None
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    rc: Optional[int] = None
    error_message: Optional[str] = None

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    """Schema for paginated job list response."""

    items: list[JobResponse]
    total: int
    page: int
    size: int
    pages: int


class JobLogResponse(BaseModel):
    """Schema for job log response."""

    job_id: UUID
    status: str
    stdout: Optional[str] = None
    offset: int = 0
    has_more: bool = False


class DashboardStatTrendItem(BaseModel):
    date: str
    success: int
    failed: int


class DashboardStatTopPlaybook(BaseModel):
    name: str
    count: int


class DashboardStatFailureReason(BaseModel):
    reason: str
    count: int
    most_frequent_task: str


class DashboardStatsResponse(BaseModel):
    active_jobs: int
    total_jobs_7d: int
    success_rate_7d: float
    success_rate_trend_7d: float
    trends: list[DashboardStatTrendItem]
    top_playbooks: list[DashboardStatTopPlaybook]
    failure_reasons: list[DashboardStatFailureReason]


class ProjectFileNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    children: Optional[list['ProjectFileNode']] = None


class ProjectFileContent(BaseModel):
    content: str


class ProjectFileUpdate(BaseModel):
    content: str

class ProjectFileCreate(BaseModel):
    path: str
    is_dir: bool = False
    content: str = ""
