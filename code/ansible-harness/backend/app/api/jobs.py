"""Job API routes with multi-project and SSE streaming support."""

import asyncio
import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncGenerator, Optional
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, get_db
from app.models.job import Job
from app.schemas.connection_checks import (
    ManagedInventoryV2BulkConnectionCheckResult,
    ManagedInventoryV2HostConnectionCheckResult,
)
from app.schemas.credentials import (
    InventoryCredentialCreate,
    InventoryCredentialSummary,
    InventoryCredentialUpdate,
    ProjectCredentialCreate,
    ProjectCredentialSummary,
    ProjectCredentialUpdate,
)
from app.schemas.inventories import (
    InventoryMigrationResult,
    ManagedInventoryGroupCreate,
    ManagedInventoryV2Create,
    ManagedInventoryV2Detail,
    ManagedInventoryV2HostAttach,
    ManagedInventoryV2HostAssetDetail,
    ManagedInventoryV2HostAssetUpdate,
    ManagedInventoryV2ListItem,
    ManagedInventoryV2Update,
)
from app.schemas.jobs import (
    JobCreate,
    JobListResponse,
    JobLogResponse,
    JobResponse,
    DashboardStatsResponse,
    DashboardStatTrendItem,
    DashboardStatTopPlaybook,
    DashboardStatFailureReason,
    ProjectFileNode,
    ProjectFileContent,
    ProjectFileUpdate,
    ProjectFileCreate,
)
from app.services.credential_service import (
    CredentialConfigurationError,
    create_project_credential as create_project_credential_record,
    delete_project_credential as delete_project_credential_record,
    get_project_credential as get_project_credential_record,
    list_project_credentials as list_project_credential_records,
    update_project_credential as update_project_credential_record,
)
from app.services.managed_inventory_service import (
    get_project_inventory_dir,
    is_invalid_managed_inventory_filename,
)
from app.services.ansible_service import (
    build_ansible_limit,
    execute_job,
    get_live_log_snapshot,
    get_playbooks,
    get_projects,
    _get_project_dir,
)
from app.services.connection_check_service import (
    check_inventory_all,
    check_inventory_group,
    check_inventory_host,
)
from app.services.inventory_v2_service import (
    HostAssetConflictError,
    attach_host_to_inventory_group,
    create_inventory,
    create_global_credential,
    create_inventory_credential,
    delete_host_asset,
    delete_global_credential,
    delete_inventory,
    delete_inventory_credential,
    delete_inventory_host,
    get_global_credential,
    get_host_asset,
    get_inventory_credential,
    get_inventory_detail,
    list_global_credentials,
    list_host_assets,
    list_inventory_credentials,
    list_inventories,
    migrate_legacy_managed_inventories,
    update_host_asset,
    update_global_credential,
    update_inventory,
    update_inventory_credential,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])

MANAGED_INVENTORY_STATUS_UNKNOWN = "unknown"


def _split_stdout_lines(stdout: str | None) -> list[str]:
    if not stdout:
        return []
    normalized = stdout.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _is_invalid_managed_inventory_filename(filename: str) -> bool:
    return is_invalid_managed_inventory_filename(filename)


def _get_project_inventory_dir(project_name: str) -> Path:
    return get_project_inventory_dir(project_name)


def _save_managed_inventory_groups(project_name: str, filename: str, groups: list[ManagedInventoryGroupCreate]) -> None:
    inventory_dir = _get_project_inventory_dir(project_name)
    metadata_path = inventory_dir.parent / ".managed_inventory_metadata" / f"{filename}.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps({"groups": [group.model_dump(mode="json") for group in groups]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _delete_managed_inventory_groups(project_name: str, filename: str) -> None:
    inventory_dir = _get_project_inventory_dir(project_name)
    metadata_path = inventory_dir.parent / ".managed_inventory_metadata" / f"{filename}.json"
    if metadata_path.exists():
        metadata_path.unlink()


def _render_managed_inventory_groups(groups: list[ManagedInventoryGroupCreate]) -> str:
    rendered_lines: list[str] = []
    for group in groups:
        rendered_lines.append(f"[{group.name}]")
        for host in group.hosts:
            host_parts = [host.name, f"ansible_host={host.address}"]
            if host.connection_type:
                host_parts.append(f"ansible_connection={host.connection_type}")
            host_parts.append(f"ansible_port={host.port}")
            for key, value in host.host_vars.items():
                host_parts.append(f"{key}={value}")
            rendered_lines.append(" ".join(host_parts))
        rendered_lines.append("")
    return "\n".join(rendered_lines).rstrip("\n") + "\n" if rendered_lines else ""


def _validate_managed_inventory_credential_refs(project_name: str, groups: list[ManagedInventoryGroupCreate]) -> None:
    valid_refs = {credential.ref for credential in _load_project_credential_summaries(project_name)}

    for group in groups:
        for host in group.hosts:
            for credential_ref in (
                host.ansibleharness_login_credential_ref,
                host.ansibleharness_become_credential_ref,
            ):
                if credential_ref is not None and credential_ref not in valid_refs:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Credential ref '{credential_ref}' does not belong to project '{project_name}'",
                    )


def _get_project_credential_store_path(project_name: str) -> Path:
    inventory_dir = _get_project_inventory_dir(project_name)
    credential_dir = inventory_dir.parent / ".credential_metadata"
    return credential_dir / "credentials.json"


def _load_project_credential_summaries(project_name: str) -> list[ProjectCredentialSummary]:
    store_path = _get_project_credential_store_path(project_name)
    if not store_path.is_file():
        return []

    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="Credential store is malformed") from exc

    try:
        credentials = payload.get("credentials", [])
    except AttributeError as exc:
        raise HTTPException(status_code=500, detail="Credential store is malformed") from exc

    try:
        return [ProjectCredentialSummary.model_validate(item) for item in credentials]
    except ValidationError as exc:
        raise HTTPException(status_code=500, detail="Credential store is malformed") from exc


def _save_project_credential_summaries(project_name: str, credentials: list[ProjectCredentialSummary]) -> None:
    store_path = _get_project_credential_store_path(project_name)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(
        json.dumps({"credentials": [credential.model_dump(mode="json") for credential in credentials]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _group_exists_in_v2_inventory(detail: ManagedInventoryV2Detail, group_name: str) -> bool:
    return any(group.name == group_name for group in detail.groups)


def _host_exists_in_v2_inventory(detail: ManagedInventoryV2Detail, host_name: str) -> bool:
    return any(host.name == host_name for host in detail.hosts)


def _host_exists_in_v2_group(detail: ManagedInventoryV2Detail, group_name: str, host_name: str) -> bool:
    for group in detail.groups:
        if group.name == group_name:
            return any(host.name == host_name for host in group.hosts)
    return False


def _validate_v2_job_target(detail: ManagedInventoryV2Detail, job_data: JobCreate) -> None:
    if job_data.target_scope == "inventory":
        return

    if job_data.target_scope == "group":
        for group_name in (job_data.target_group_names or []):
            if not _group_exists_in_v2_inventory(detail, group_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Target group '{group_name}' not found in managed inventory '{detail.name}'",
                )
        return

    if job_data.target_group_names:
        for group_name in job_data.target_group_names:
            if not _group_exists_in_v2_inventory(detail, group_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Target group '{group_name}' not found in managed inventory '{detail.name}'",
                )
            for host_name in (job_data.target_host_names or []):
                if not _host_exists_in_v2_group(detail, group_name, host_name):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"Target host '{host_name}' not found in group '{group_name}' "
                            f"for managed inventory '{detail.name}'"
                        ),
                    )
        return

    for host_name in (job_data.target_host_names or []):
        if not _host_exists_in_v2_inventory(detail, host_name):
            raise HTTPException(
                status_code=400,
                detail=f"Target host '{host_name}' not found in managed inventory '{detail.name}'",
            )


@router.post("/projects/{project_name}/credentials", response_model=ProjectCredentialSummary, status_code=201)
async def create_project_credential(
    project_name: str,
    payload: ProjectCredentialCreate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 로컬 credential entity를 생성합니다.

    Issue 1의 첫 credential tracer bullet에서는 secret 비노출 create-summary contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    try:
        return await create_project_credential_record(db, project_name, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/projects/{project_name}/credentials", response_model=list[ProjectCredentialSummary])
async def list_project_credentials(project_name: str, db: AsyncSession = Depends(get_db)):
    """프로젝트 로컬 credential summary 목록을 조회합니다.

    Issue 1의 다음 credential tracer bullet에서는 non-secret summary read contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    return await list_project_credential_records(db, project_name)


@router.get("/projects/{project_name}/credentials/{ref}", response_model=ProjectCredentialSummary)
async def get_project_credential(project_name: str, ref: str, db: AsyncSession = Depends(get_db)):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    summary = await get_project_credential_record(db, project_name, ref)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return summary


@router.put("/projects/{project_name}/credentials/{ref}", response_model=ProjectCredentialSummary)
async def update_project_credential(
    project_name: str,
    ref: str,
    payload: ProjectCredentialUpdate,
    db: AsyncSession = Depends(get_db),
):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    try:
        summary = await update_project_credential_record(db, project_name, ref, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return summary


@router.delete("/projects/{project_name}/credentials/{ref}", status_code=204)
async def delete_project_credential(
    project_name: str,
    ref: str,
    db: AsyncSession = Depends(get_db),
):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")
    deleted = await delete_project_credential_record(db, project_name, ref)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")


@router.get("/credentials", response_model=list[InventoryCredentialSummary])
async def list_global_credential_records(db: AsyncSession = Depends(get_db)):
    """List application-wide credentials shared by every inventory."""

    return await list_global_credentials(db)


@router.post("/credentials", response_model=InventoryCredentialSummary, status_code=201)
async def create_global_credential_record(payload: InventoryCredentialCreate, db: AsyncSession = Depends(get_db)):
    """Create an application-wide credential shared by every inventory."""

    try:
        return await create_global_credential(db, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/credentials/{ref}", response_model=InventoryCredentialSummary)
async def get_global_credential_record(ref: str, db: AsyncSession = Depends(get_db)):
    credential = await get_global_credential(db, ref)
    if credential is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return InventoryCredentialSummary(
        ref=str(credential.ref),
        name=str(credential.name),
        credential_type=credential.credential_type,
        username=str(credential.username),
        become_username=str(credential.become_username) if credential.become_username else None,
        has_secret=bool(credential.encrypted_secret),
        has_become_secret=bool(credential.encrypted_become_secret and credential.become_nonce),
        last_rotated_at=credential.last_rotated_at,
    )


@router.put("/credentials/{ref}", response_model=InventoryCredentialSummary)
async def update_global_credential_record(
    ref: str,
    payload: InventoryCredentialUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        summary = await update_global_credential(db, ref, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return summary


@router.delete("/credentials/{ref}", status_code=204)
async def delete_global_credential_record(ref: str, db: AsyncSession = Depends(get_db)):
    try:
        deleted = await delete_global_credential(db, ref)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")


@router.get("/inventories", response_model=list[ManagedInventoryV2ListItem])
async def list_top_level_inventories(db: AsyncSession = Depends(get_db)):
    return await list_inventories(db)


@router.get("/hosts", response_model=list[ManagedInventoryV2HostAssetDetail])
async def list_top_level_host_assets(db: AsyncSession = Depends(get_db)):
    return await list_host_assets(db)


@router.get("/hosts/{host_id}", response_model=ManagedInventoryV2HostAssetDetail)
async def get_top_level_host_asset(host_id: UUID, db: AsyncSession = Depends(get_db)):
    detail = await get_host_asset(db, host_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Host asset '{host_id}' not found")
    return detail


@router.patch("/hosts/{host_id}", response_model=ManagedInventoryV2HostAssetDetail)
async def update_top_level_host_asset(
    host_id: UUID,
    payload: ManagedInventoryV2HostAssetUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        detail = await update_host_asset(db, host_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Host asset '{host_id}' not found")
    return detail


@router.delete("/hosts/{host_id}", status_code=204)
async def delete_top_level_host_asset(host_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await delete_host_asset(db, host_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Host asset '{host_id}' not found")


@router.post("/inventories", response_model=ManagedInventoryV2Detail, status_code=201)
async def create_top_level_inventory(payload: ManagedInventoryV2Create, db: AsyncSession = Depends(get_db)):
    try:
        return await create_inventory(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Inventory '{payload.name}' already exists") from exc


@router.get("/inventories/{inventory_id}", response_model=ManagedInventoryV2Detail)
async def get_top_level_inventory(inventory_id: UUID, db: AsyncSession = Depends(get_db)):
    detail = await get_inventory_detail(db, inventory_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")
    return detail


@router.put("/inventories/{inventory_id}", response_model=ManagedInventoryV2Detail)
async def update_top_level_inventory(inventory_id: UUID, payload: ManagedInventoryV2Update, db: AsyncSession = Depends(get_db)):
    try:
        detail = await update_inventory(db, inventory_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Inventory '{payload.name}' already exists") from exc
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")
    return detail


@router.delete("/inventories/{inventory_id}", status_code=204)
async def delete_top_level_inventory(inventory_id: UUID, db: AsyncSession = Depends(get_db)):
    deleted = await delete_inventory(db, inventory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")


@router.post("/inventories/{inventory_id}/hosts", response_model=ManagedInventoryV2Detail)
async def attach_top_level_inventory_host(
    inventory_id: UUID,
    payload: ManagedInventoryV2HostAttach,
    db: AsyncSession = Depends(get_db),
):
    try:
        detail = await attach_host_to_inventory_group(db, inventory_id, payload)
    except HostAssetConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")
    return detail


@router.delete("/inventories/{inventory_id}/hosts/{host_key}", status_code=204)
async def delete_top_level_inventory_host(inventory_id: UUID, host_key: str, db: AsyncSession = Depends(get_db)):
    try:
        deleted = await delete_inventory_host(db, inventory_id, host_key)
    except HostAssetConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Host '{host_key}' not found in inventory '{inventory_id}'")


@router.get("/inventories/{inventory_id}/credentials", response_model=list[InventoryCredentialSummary])
async def list_top_level_inventory_credentials(inventory_id: UUID, db: AsyncSession = Depends(get_db)):
    return await list_inventory_credentials(db, inventory_id)


@router.post("/inventories/{inventory_id}/credentials", response_model=InventoryCredentialSummary, status_code=201)
async def create_top_level_inventory_credential(
    inventory_id: UUID,
    payload: InventoryCredentialCreate,
    db: AsyncSession = Depends(get_db),
):
    inventory = await get_inventory_detail(db, inventory_id)
    if inventory is None:
        raise HTTPException(status_code=404, detail=f"Inventory '{inventory_id}' not found")
    try:
        return await create_inventory_credential(db, inventory_id, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/inventories/{inventory_id}/credentials/{ref}", response_model=InventoryCredentialSummary)
async def get_top_level_inventory_credential(inventory_id: UUID, ref: str, db: AsyncSession = Depends(get_db)):
    credential = await get_inventory_credential(db, inventory_id, ref)
    if credential is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return InventoryCredentialSummary(
        ref=str(credential.ref),
        name=str(credential.name),
        credential_type=credential.credential_type,
        username=str(credential.username),
        become_username=str(credential.become_username) if credential.become_username else None,
        has_secret=bool(credential.encrypted_secret),
        has_become_secret=bool(credential.encrypted_become_secret and credential.become_nonce),
        last_rotated_at=credential.last_rotated_at,
    )


@router.put("/inventories/{inventory_id}/credentials/{ref}", response_model=InventoryCredentialSummary)
async def update_top_level_inventory_credential(
    inventory_id: UUID,
    ref: str,
    payload: InventoryCredentialUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        summary = await update_inventory_credential(db, inventory_id, ref, payload)
    except CredentialConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if summary is None:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")
    return summary


@router.delete("/inventories/{inventory_id}/credentials/{ref}", status_code=204)
async def delete_top_level_inventory_credential(inventory_id: UUID, ref: str, db: AsyncSession = Depends(get_db)):
    try:
        deleted = await delete_inventory_credential(db, inventory_id, ref)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Credential '{ref}' not found")


@router.post("/inventories/migrate-from-legacy", response_model=InventoryMigrationResult)
async def migrate_top_level_inventories_from_legacy(db: AsyncSession = Depends(get_db)):
    return await migrate_legacy_managed_inventories(db)


# --- V2 Connection Check Endpoints ---


@router.post(
    "/inventories/{inventory_id}/groups/{group_name}/hosts/{host_name}/connection-check",
    response_model=ManagedInventoryV2HostConnectionCheckResult,
)
async def check_v2_inventory_host(
    inventory_id: UUID,
    group_name: str,
    host_name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await check_inventory_host(db, inventory_id, group_name, host_name)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Host '{host_name}' in group '{group_name}' not found in inventory '{inventory_id}'",
        )
    return result


@router.post(
    "/inventories/{inventory_id}/groups/{group_name}/connection-check",
    response_model=ManagedInventoryV2BulkConnectionCheckResult,
)
async def check_v2_inventory_group(
    inventory_id: UUID,
    group_name: str,
    db: AsyncSession = Depends(get_db),
):
    result = await check_inventory_group(db, inventory_id, group_name)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Group '{group_name}' not found in inventory '{inventory_id}'",
        )
    return result


@router.post(
    "/inventories/{inventory_id}/connection-check",
    response_model=ManagedInventoryV2BulkConnectionCheckResult,
)
async def check_v2_inventory_all(
    inventory_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await check_inventory_all(db, inventory_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Inventory '{inventory_id}' not found",
        )
    return result


# --- Job endpoints ---

@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(job_data: JobCreate, db: AsyncSession = Depends(get_db)):
    """새로운 Job을 생성하고 비동기 실행을 시작합니다."""
    # Validate project exists
    projects = [p["name"] for p in get_projects()]
    if job_data.project not in projects:
        raise HTTPException(
            status_code=400,
            detail=f"Project '{job_data.project}' not found. Available: {projects}",
        )

    # Validate playbook exists in project
    available_playbooks = [p["path"] for p in get_playbooks(job_data.project)]
    if job_data.playbook not in available_playbooks:
        raise HTTPException(
            status_code=400,
            detail=f"Playbook '{job_data.playbook}' not found in project '{job_data.project}'. Available: {available_playbooks}",
        )

    chosen_inventory_count = sum(
        1
        for v in (job_data.inventory, job_data.inventory_file, job_data.managed_inventory_id)
        if v is not None
    )
    if job_data.inventory is not None and job_data.inventory_file is not None:
        raise HTTPException(
            status_code=400,
            detail="Use either direct inventory content or inventory_file, not both",
        )
    if chosen_inventory_count > 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one of inventory, inventory_file, managed_inventory_id must be provided",
        )

    if job_data.managed_inventory_id is None:
        try:
            build_ansible_limit(job_data.target_scope, job_data.target_group_names, job_data.target_host_names)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if job_data.inventory_file:
        if _is_invalid_managed_inventory_filename(job_data.inventory_file):
            raise HTTPException(status_code=400, detail="Invalid managed inventory filename")
        inventory_file = _get_project_inventory_dir(job_data.project) / job_data.inventory_file
        if not inventory_file.is_file():
            raise HTTPException(
                status_code=400,
                detail=f"Inventory file '{job_data.inventory_file}' not found in project '{job_data.project}'",
            )

    managed_inventory_revision = None
    if job_data.managed_inventory_id is not None:
        managed_detail = await get_inventory_detail(db, job_data.managed_inventory_id)
        if managed_detail is None:
            raise HTTPException(status_code=400, detail=f"Managed inventory '{job_data.managed_inventory_id}' not found")
        _validate_v2_job_target(managed_detail, job_data)
        managed_inventory_revision = managed_detail.revision

    merged_extra_vars = dict(job_data.extra_vars) if job_data.extra_vars else {}
    if job_data.inventory_vars:
        merged_extra_vars["__inventory_vars__"] = job_data.inventory_vars
    if job_data.group_vars:
        merged_extra_vars["__group_vars__"] = job_data.group_vars
    if job_data.host_vars:
        merged_extra_vars["__host_vars__"] = job_data.host_vars

    job = Job(
        project=job_data.project,
        playbook=job_data.playbook,
        inventory=job_data.inventory,
        inventory_file=job_data.inventory_file,
        inventory_source_type=(
            "direct"
            if job_data.inventory is not None
            else "managed_v2"
            if job_data.managed_inventory_id is not None
            else "file"
            if job_data.inventory_file is not None
            else None
        ),
        managed_inventory_id=job_data.managed_inventory_id,
        managed_inventory_revision=managed_inventory_revision,
        extra_vars=merged_extra_vars if merged_extra_vars else None,
        target_scope=job_data.target_scope,
        target_group_name=",".join(job_data.target_group_names) if job_data.target_group_names else None,
        target_host_name=",".join(job_data.target_host_names) if job_data.target_host_names else None,
        status="pending",
    )
    db.add(job)
    await db.flush()
    await db.commit()
    await db.refresh(job)

    asyncio.create_task(execute_job(job.id))

    logger.info(f"Job {job.id} created for {job_data.project}/{job_data.playbook}")
    return job


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Job 목록을 페이지네이션으로 조회합니다."""
    query = select(Job)
    count_query = select(func.count(Job.id))

    if status:
        query = query.where(Job.status == status)
        count_query = count_query.where(Job.status == status)
    if project:
        query = query.where(Job.project == project)
        count_query = count_query.where(Job.project == project)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.order_by(Job.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total, page=page, size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """특정 Job의 상세 정보를 조회합니다."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/jobs/{job_id}/logs", response_model=JobLogResponse)
async def get_job_logs(
    job_id: UUID,
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Job의 실행 로그를 조회합니다."""
    snapshot = get_live_log_snapshot(str(job_id), offset)
    if snapshot is not None:
        log_text = "\n".join(snapshot["lines"])
        return JobLogResponse(
            job_id=job_id,
            status=snapshot["status"] if snapshot["finished"] else "running",
            stdout=log_text,
            offset=snapshot["total"],
            has_more=not snapshot["finished"],
        )

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    stdout_lines = _split_stdout_lines(job.stdout)
    remaining_lines = stdout_lines[offset:]
    return JobLogResponse(
        job_id=job.id, status=job.status,
        stdout="\n".join(remaining_lines), offset=len(stdout_lines),
        has_more=job.status in ("running", "pending"),
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_logs(job_id: UUID, request: Request):
    """SSE 엔드포인트: Job 로그를 실시간으로 스트리밍합니다."""

    async def event_generator() -> AsyncGenerator[str, None]:
        offset = 0
        yield "retry: 1000\n\n"

        while True:
            if await request.is_disconnected():
                break

            snapshot = get_live_log_snapshot(str(job_id), offset)
            
            if snapshot is None:
                async with async_session() as session:
                    result = await session.execute(select(Job).where(Job.id == job_id))
                    job = result.scalar_one_or_none()
                    persisted_lines = _split_stdout_lines(job.stdout if job else None)
                    remaining_lines = persisted_lines[offset:]
                    if remaining_lines:
                        for line in remaining_lines:
                            yield f"data: {line}\n\n"
                        offset = len(persisted_lines)

                    if job and job.status in ("pending", "running"):
                        yield f"event: heartbeat\ndata: {json.dumps({'status': job.status, 'offset': offset})}\n\n"
                        await asyncio.sleep(1.0)
                        continue
                    else:
                        status = job.status if job else "unknown"
                        rc = job.rc if job else None
                        yield f"event: done\ndata: {json.dumps({'status': status, 'rc': rc})}\n\n"
                        break

            # 버퍼 데이터 전송
            if snapshot["lines"]:
                for line in snapshot["lines"]:
                    yield f"data: {line}\n\n"
                offset = snapshot["total"]
            else:
                heartbeat_status = snapshot["status"] if snapshot["finished"] else "running"
                yield f"event: heartbeat\ndata: {json.dumps({'status': heartbeat_status, 'offset': snapshot['total']})}\n\n"

            if snapshot["finished"]:
                yield f"event: done\ndata: {json.dumps({'status': snapshot['status'], 'rc': snapshot['rc']})}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def delete_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    """완료된 Job을 삭제합니다."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if job.status in ("pending", "running"):
        raise HTTPException(status_code=409, detail=f"Cannot delete job in '{job.status}' status")
    await db.delete(job)


@router.get("/stats/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """대시보드 통계를 조회합니다."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    fourteen_days_ago = now - timedelta(days=14)

    # 1. 활성 작업 수 (pending, running)
    active_result = await db.execute(select(func.count(Job.id)).where(Job.status.in_(("pending", "running"))))
    active_jobs = active_result.scalar() or 0

    # 2. 최근 7일 작업 수 및 성공률
    jobs_7d_result = await db.execute(select(Job.status).where(Job.created_at >= seven_days_ago))
    jobs_7d = jobs_7d_result.scalars().all()
    total_7d = len(jobs_7d)
    success_7d = sum(1 for status in jobs_7d if status == "success")
    success_rate_7d = round((success_7d / total_7d * 100), 1) if total_7d > 0 else 0.0

    # 3. 이전 7일 성공률 (트렌드 비교용)
    jobs_prev_7d_result = await db.execute(
        select(Job.status).where(Job.created_at >= fourteen_days_ago, Job.created_at < seven_days_ago)
    )
    jobs_prev_7d = jobs_prev_7d_result.scalars().all()
    total_prev_7d = len(jobs_prev_7d)
    success_prev_7d = sum(1 for status in jobs_prev_7d if status == "success")
    success_rate_prev_7d = round((success_prev_7d / total_prev_7d * 100), 1) if total_prev_7d > 0 else 0.0
    success_rate_trend_7d = round(success_rate_7d - success_rate_prev_7d, 1)

    # 4. 일자별 트렌드 (최근 14일)
    trend_dict = {}
    for i in range(14):
        d = (now - timedelta(days=13 - i)).strftime("%Y-%m-%d")
        trend_dict[d] = {"success": 0, "failed": 0}
    
    recent_14d_jobs_result = await db.execute(
        select(Job.created_at, Job.status).where(Job.created_at >= fourteen_days_ago)
    )
    for created_at, status in recent_14d_jobs_result.all():
        d_str = created_at.strftime("%Y-%m-%d")
        if d_str in trend_dict:
            if status == "success":
                trend_dict[d_str]["success"] += 1
            elif status in ("failed", "error"):
                trend_dict[d_str]["failed"] += 1
                
    trends = [
        DashboardStatTrendItem(date=d, success=v["success"], failed=v["failed"])
        for d, v in trend_dict.items()
    ]

    # 5. Top 5 플레이북 (최근 30일 기준)
    thirty_days_ago = now - timedelta(days=30)
    top_playbooks_result = await db.execute(
        select(Job.project, Job.playbook, func.count(Job.id))
        .where(Job.created_at >= thirty_days_ago)
        .group_by(Job.project, Job.playbook)
        .order_by(func.count(Job.id).desc())
        .limit(5)
    )
    top_playbooks = [
        DashboardStatTopPlaybook(name=f"{project} - {playbook}", count=count)
        for project, playbook, count in top_playbooks_result.all()
    ]

    # 6. 주요 실패 원인 (간단 파싱)
    failed_jobs_result = await db.execute(
        select(Job.project, Job.playbook, Job.error_message, Job.stdout)
        .where(Job.status == "failed", Job.created_at >= fourteen_days_ago)
        .order_by(Job.created_at.desc())
        .limit(50)
    )
    
    reasons_count = {}
    task_for_reason = {}
    for project, playbook, err_msg, stdout in failed_jobs_result.all():
        reason = "Unknown Error"
        if err_msg and err_msg.strip():
            reason = err_msg.strip().split("\n")[0][:150]
        elif stdout:
            import json
            for line in stdout.split("\n"):
                if "fatal:" in line or "FAILED!" in line or "error" in line.lower():
                    # Try to parse JSON from the fatal line
                    try:
                        if "=>" in line:
                            json_str = line.split("=>", 1)[1].strip()
                            data = json.loads(json_str)
                            if "msg" in data:
                                reason = str(data["msg"])[:150]
                                break
                            elif "stderr" in data and data["stderr"]:
                                reason = str(data["stderr"]).strip().split("\n")[-1][:150]
                                break
                    except Exception:
                        pass
                    
                    reason = line.strip()[:150]
                    break
        
        if reason not in reasons_count:
            reasons_count[reason] = 0
            task_for_reason[reason] = f"{project} - {playbook}"
        reasons_count[reason] += 1

    sorted_reasons = sorted(reasons_count.items(), key=lambda x: x[1], reverse=True)[:5]
    failure_reasons = [
        DashboardStatFailureReason(reason=r, count=c, most_frequent_task=task_for_reason[r])
        for r, c in sorted_reasons
    ]

    return DashboardStatsResponse(
        active_jobs=active_jobs,
        total_jobs_7d=total_7d,
        success_rate_7d=success_rate_7d,
        success_rate_trend_7d=success_rate_trend_7d,
        trends=trends,
        top_playbooks=top_playbooks,
        failure_reasons=failure_reasons,
    )


def _build_file_tree(dir_path: Path, relative_to: Path) -> list[ProjectFileNode]:
    items = []
    if not dir_path.exists():
        return items
    for p in sorted(dir_path.iterdir()):
        if p.name.startswith(".") or p.name == "__pycache__":
            continue
        item = ProjectFileNode(
            name=p.name,
            path=str(p.relative_to(relative_to)).replace("\\\\", "/"),
            is_dir=p.is_dir()
        )
        if p.is_dir():
            item.children = _build_file_tree(p, relative_to)
        items.append(item)
    return items


@router.get("/projects/{project_name}/files", response_model=list[ProjectFileNode])
async def list_project_files(project_name: str):
    """프로젝트 파일 구조를 반환합니다."""
    try:
        project_dir = _get_project_dir(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    return _build_file_tree(project_dir, project_dir)


@router.get("/projects/{project_name}/files/{file_path:path}", response_model=ProjectFileContent)
async def get_project_file_content(project_name: str, file_path: str):
    """특정 파일의 내용을 반환합니다."""
    try:
        project_dir = _get_project_dir(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    target_path = (project_dir / file_path).resolve()
    
    # Path traversal 방지
    if not str(target_path).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        content = target_path.read_text(encoding="utf-8")
        return ProjectFileContent(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {str(e)}")

@router.post("/projects/{project_name}/files", response_model=ProjectFileNode)
async def create_project_file_or_dir(project_name: str, payload: ProjectFileCreate):
    """새로운 파일 또는 폴더를 생성합니다."""
    try:
        project_dir = _get_project_dir(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    target_path = (project_dir / payload.path).resolve()

    # Path traversal 방지
    if not str(target_path).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    if target_path.exists():
        raise HTTPException(status_code=400, detail="File or directory already exists")
        
    try:
        if payload.is_dir:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(payload.content, encoding="utf-8")
            
        return ProjectFileNode(
            name=target_path.name,
            path=payload.path,
            is_dir=payload.is_dir
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot create file/dir: {str(e)}")


@router.put("/projects/{project_name}/files/{file_path:path}", response_model=ProjectFileNode)
async def update_project_file_content(project_name: str, file_path: str, payload: ProjectFileUpdate):
    """특정 파일의 내용을 수정합니다."""
    try:
        project_dir = _get_project_dir(project_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    target_path = (project_dir / file_path).resolve()
    
    # Path traversal 방지
    if not str(target_path).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    if not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        target_path.write_text(payload.content, encoding="utf-8")
        return ProjectFileNode(
            name=target_path.name,
            path=file_path,
            is_dir=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot write file: {str(e)}")

@router.delete("/projects/{project_name}/files/{file_path:path}")
async def delete_project_file_or_dir(project_name: str, file_path: str):
    from app.config import settings
    import shutil
    project_dir = Path(settings.ANSIBLE_DATA_DIR) / "projects" / project_name
    target_path = project_dir / file_path
    
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File or directory not found")
    
    try:
        if target_path.is_file():
            target_path.unlink()
        elif target_path.is_dir():
            shutil.rmtree(target_path)
        return {"success": True, "message": f"{file_path} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete {file_path}: {str(e)}")

