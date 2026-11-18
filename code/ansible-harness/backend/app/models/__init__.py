"""SQLAlchemy model imports for metadata registration."""

from app.models.job import Job
from app.models.managed_inventory import ManagedInventory, ManagedInventoryGroup, ManagedInventoryHost
from app.models.managed_inventory_v2 import (
    GlobalCredential,
    InventoryCredential,
    ManagedInventoryV2,
    ManagedInventoryV2Group,
    ManagedInventoryV2Host,
    ManagedInventoryV2HostMembership,
)
from app.models.project_credential import ProjectCredential

__all__ = [
    "Job",
    "ManagedInventory",
    "ManagedInventoryGroup",
    "ManagedInventoryHost",
    "ManagedInventoryV2",
    "ManagedInventoryV2Group",
    "ManagedInventoryV2Host",
    "ManagedInventoryV2HostMembership",
    "InventoryCredential",
    "GlobalCredential",
    "ProjectCredential",
]
