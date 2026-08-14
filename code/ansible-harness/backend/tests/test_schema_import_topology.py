import ast
import importlib
from pathlib import Path

from app.schemas.connection_checks import ManagedInventoryV2BulkConnectionCheckResult as DirectConnectionCheckResult
from app.schemas.credentials import ProjectCredentialCreate as DirectProjectCredentialCreate
from app.schemas.inventories import ManagedInventoryV2Detail as DirectManagedInventoryV2Detail
from app.schemas.job import (
    ManagedInventoryV2BulkConnectionCheckResult,
    ManagedInventoryV2Detail,
    ProjectCredentialCreate,
)


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _imported_names(relative_path: str, source_module: str) -> set[str]:
    module = ast.parse((BACKEND_ROOT / relative_path).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(module):
        if isinstance(node, ast.ImportFrom) and node.module == source_module:
            imported.update(alias.name for alias in node.names)
    return imported


def test_runtime_consumers_import_feature_schema_modules_directly() -> None:
    expected_imports = {
        "app/services/credential_service.py": {
            "app.schemas.credentials": {
                "ProjectCredentialCreate",
                "ProjectCredentialSummary",
                "ProjectCredentialUpdate",
            }
        },
        "app/services/connection_check_service.py": {
            "app.schemas.connection_checks": {
                "ManagedInventoryV2BulkConnectionCheckResult",
                "ManagedInventoryV2BulkConnectionCheckSummary",
                "ManagedInventoryV2BulkConnectionCheckTarget",
                "ManagedInventoryV2HostConnectionCheckResult",
            }
        },
        "app/services/managed_inventory_service.py": {
            "app.schemas.inventories": {
                "ManagedInventoryCreate",
                "ManagedInventoryDetail",
                "ManagedInventoryGroup",
                "ManagedInventoryGroupCreate",
                "ManagedInventoryHost",
                "ManagedInventoryListItem",
                "ManagedInventoryUpdate",
            }
        },
        "app/services/inventory_v2_service.py": {
            "app.schemas.credentials": {
                "InventoryCredentialCreate",
                "InventoryCredentialSummary",
                "InventoryCredentialUpdate",
            },
            "app.schemas.inventories": {
                "InventoryMigrationResult",
                "ManagedInventoryV2Create",
                "ManagedInventoryV2Detail",
                "ManagedInventoryV2Group",
                "ManagedInventoryV2GroupCreate",
                "ManagedInventoryV2Host",
                "ManagedInventoryV2HostAssetCreate",
                "ManagedInventoryV2HostAssetDetail",
                "ManagedInventoryV2HostAssetMembership",
                "ManagedInventoryV2HostAssetUpdate",
                "ManagedInventoryV2HostAttach",
                "ManagedInventoryV2HostCreate",
                "ManagedInventoryV2ListItem",
                "ManagedInventoryV2Membership",
                "ManagedInventoryV2Update",
            },
        },
        "app/api/jobs.py": {
            "app.schemas.connection_checks": {
                "ManagedInventoryV2BulkConnectionCheckResult",
                "ManagedInventoryV2HostConnectionCheckResult",
            },
            "app.schemas.credentials": {
                "InventoryCredentialCreate",
                "InventoryCredentialSummary",
                "InventoryCredentialUpdate",
                "ProjectCredentialCreate",
                "ProjectCredentialSummary",
                "ProjectCredentialUpdate",
            },
            "app.schemas.inventories": {
                "InventoryMigrationResult",
                "ManagedInventoryGroupCreate",
                "ManagedInventoryV2Create",
                "ManagedInventoryV2Detail",
                "ManagedInventoryV2HostAssetDetail",
                "ManagedInventoryV2HostAssetUpdate",
                "ManagedInventoryV2HostAttach",
                "ManagedInventoryV2ListItem",
                "ManagedInventoryV2Update",
            },
            "app.schemas.jobs": {
                "JobCreate",
                "JobListResponse",
                "JobLogResponse",
                "JobResponse",
            },
        },
        "app/api/project_managed_inventories.py": {
            "app.schemas.connection_checks": {
                "ManagedInventoryBulkConnectionTestResult",
                "ManagedInventoryHostConnectionTestResult",
            },
            "app.schemas.inventories": {
                "ManagedInventoryCreate",
                "ManagedInventoryDetail",
                "ManagedInventoryGroup",
                "ManagedInventoryHost",
                "ManagedInventoryListItem",
                "ManagedInventoryUpdate",
            },
        },
        "app/api/projects.py": {
            "app.schemas.projects": {
                "InventoryItem",
                "PlaybookItem",
                "ProjectItem",
            },
        },
    }

    for relative_path, modules in expected_imports.items():
        assert not _imported_names(relative_path, "app.schemas.job")
        for source_module, expected_names in modules.items():
            assert expected_names.issubset(_imported_names(relative_path, source_module))


def test_import_smoke_and_legacy_adapter_reexports() -> None:
    importlib.import_module("app.api.jobs")
    importlib.import_module("app.api.project_managed_inventories")
    importlib.import_module("app.api.projects")
    importlib.import_module("app.services.credential_service")
    importlib.import_module("app.services.connection_check_service")
    importlib.import_module("app.services.managed_inventory_service")
    importlib.import_module("app.services.inventory_v2_service")

    assert ProjectCredentialCreate is DirectProjectCredentialCreate
    assert ManagedInventoryV2BulkConnectionCheckResult is DirectConnectionCheckResult
    assert ManagedInventoryV2Detail is DirectManagedInventoryV2Detail
