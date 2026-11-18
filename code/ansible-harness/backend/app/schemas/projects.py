"""Project, playbook, and inventory listing schemas."""

from pydantic import BaseModel


class ProjectItem(BaseModel):
    """Schema for a project listing."""

    name: str
    playbook_count: int
    inventory_count: int


class PlaybookItem(BaseModel):
    """Schema for a playbook file listing."""

    name: str
    path: str
    size: int


class InventoryItem(BaseModel):
    """Schema for an inventory file listing."""

    name: str
    path: str
