
from pydantic import BaseModel, ConfigDict
from typing import Any, Dict, Optional
from uuid import UUID
from datetime import datetime

class JobTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project: str
    playbook: str
    inventory_id: Optional[UUID] = None
    extra_vars: Optional[Dict[str, Any]] = None
    target_scope: str = "inventory"
    target_group_name: Optional[str] = None
    target_host_name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: bool = True

class JobTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project: Optional[str] = None
    playbook: Optional[str] = None
    inventory_id: Optional[UUID] = None
    extra_vars: Optional[Dict[str, Any]] = None
    target_scope: Optional[str] = None
    target_group_name: Optional[str] = None
    target_host_name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None

class JobTemplateResponse(JobTemplateCreate):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

