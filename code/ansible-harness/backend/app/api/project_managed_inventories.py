"""Legacy project-scoped managed inventory API routes."""

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.connection_checks import (
    ManagedInventoryBulkConnectionTestResult,
    ManagedInventoryHostConnectionTestResult,
)
from app.schemas.inventories import (
    ManagedInventoryCreate,
    ManagedInventoryDetail,
    ManagedInventoryGroup,
    ManagedInventoryHost,
    ManagedInventoryListItem,
    ManagedInventoryUpdate,
)
from app.services.ansible_service import get_projects
from app.services.managed_inventory_service import (
    create_managed_inventory,
    delete_managed_inventory,
    get_managed_inventory_detail,
    get_project_inventory_dir,
    is_invalid_managed_inventory_filename,
    list_managed_inventories,
    update_managed_inventory,
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _get_managed_inventory_metadata_path(project_name: str, filename: str) -> Path:
    inventory_dir = get_project_inventory_dir(project_name)
    metadata_dir = inventory_dir.parent / ".managed_inventory_metadata"
    return metadata_dir / f"{filename}.json"


async def _load_managed_inventory_groups(
    db: AsyncSession,
    project_name: str,
    filename: str,
) -> list[ManagedInventoryGroup]:
    detail = await get_managed_inventory_detail(db, project_name, filename)
    if detail is not None:
        return detail.groups

    metadata_path = _get_managed_inventory_metadata_path(project_name, filename)
    if not metadata_path.is_file():
        return []

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    groups = payload.get("groups", [])
    return [ManagedInventoryGroup.model_validate(group) for group in groups]


async def _find_managed_inventory_host(
    db: AsyncSession,
    project_name: str,
    filename: str,
    group_name: str,
    host_name: str,
) -> ManagedInventoryHost:
    groups = await _load_managed_inventory_groups(db, project_name, filename)

    for group in groups:
        if group.name != group_name:
            continue
        for host in group.hosts:
            if host.name == host_name:
                return host
        raise HTTPException(
            status_code=404,
            detail=f"Host '{host_name}' not found in group '{group_name}' for managed inventory '{filename}'",
        )

    raise HTTPException(
        status_code=404,
        detail=f"Managed inventory group '{group_name}' not found in '{filename}'",
    )


async def _find_managed_inventory_group(
    db: AsyncSession,
    project_name: str,
    filename: str,
    group_name: str,
) -> ManagedInventoryGroup:
    groups = await _load_managed_inventory_groups(db, project_name, filename)

    for group in groups:
        if group.name == group_name:
            return group

    raise HTTPException(
        status_code=404,
        detail=f"Managed inventory group '{group_name}' not found in '{filename}'",
    )


async def _run_managed_inventory_host_connection_test(
    project_name: str,
    filename: str,
    group_name: str,
    host_name: str,
    host: ManagedInventoryHost,
) -> ManagedInventoryHostConnectionTestResult:
    raise HTTPException(status_code=501, detail="Managed inventory host connection test engine is not implemented")


async def _run_managed_inventory_group_connection_test(
    project_name: str,
    filename: str,
    group_name: str,
    group: ManagedInventoryGroup,
) -> ManagedInventoryBulkConnectionTestResult:
    raise HTTPException(status_code=501, detail="Managed inventory group connection test engine is not implemented")


async def _run_managed_inventory_inventory_connection_test(
    project_name: str,
    filename: str,
    groups: list[ManagedInventoryGroup],
) -> ManagedInventoryBulkConnectionTestResult:
    raise HTTPException(status_code=501, detail="Managed inventory bulk connection test engine is not implemented")


@router.get("/{project_name}/managed-inventories", response_model=list[ManagedInventoryListItem])
async def list_project_managed_inventories(project_name: str, db: AsyncSession = Depends(get_db)):
    """프로젝트 내 managed inventory 목록을 조회합니다.

    Issue 1의 list tracer bullet에서는 managed inventory 파일 목록의
    최소 public contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    return await list_managed_inventories(db, project_name)


@router.get("/{project_name}/managed-inventories/{filename}", response_model=ManagedInventoryDetail)
async def get_project_managed_inventory(project_name: str, filename: str, db: AsyncSession = Depends(get_db)):
    """프로젝트 내 managed inventory 파일 상세를 조회합니다.

    Issue 1의 detail-read tracer bullet에서는 filename 기반의 최소 public contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    detail = await get_managed_inventory_detail(db, project_name, filename)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")
    return detail


@router.post("/{project_name}/managed-inventories", response_model=ManagedInventoryDetail, status_code=201)
async def create_project_managed_inventory(
    project_name: str,
    payload: ManagedInventoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 내 managed inventory 파일을 생성합니다.

    Issue 1의 create tracer bullet에서는 filename 기반의 최소 public contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(payload.filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    if await get_managed_inventory_detail(db, project_name, payload.filename) is not None:
        raise HTTPException(status_code=409, detail=f"Managed inventory '{payload.filename}' already exists")

    try:
        return await create_managed_inventory(db, project_name, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Managed inventory '{payload.filename}' already exists") from exc


@router.put("/{project_name}/managed-inventories/{filename}", response_model=ManagedInventoryDetail)
async def update_project_managed_inventory(
    project_name: str,
    filename: str,
    payload: ManagedInventoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """프로젝트 내 managed inventory 파일명을 변경합니다.

    Issue 1의 update tracer bullet에서는 rename-only 최소 public contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    if is_invalid_managed_inventory_filename(payload.filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    is_rename = filename != payload.filename
    if is_rename and await get_managed_inventory_detail(db, project_name, payload.filename) is not None:
        raise HTTPException(status_code=409, detail=f"Managed inventory '{payload.filename}' already exists")

    try:
        detail = await update_managed_inventory(db, project_name, filename, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Managed inventory '{payload.filename}' already exists") from exc
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")
    return detail


@router.delete("/{project_name}/managed-inventories/{filename}", status_code=204)
async def delete_project_managed_inventory(project_name: str, filename: str, db: AsyncSession = Depends(get_db)):
    """프로젝트 내 managed inventory 파일을 삭제합니다.

    Issue 1의 delete tracer bullet에서는 filename 기반의 최소 public contract만 고정합니다.
    """
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    deleted = await delete_managed_inventory(db, project_name, filename)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")


@router.post(
    "/{project_name}/managed-inventories/{filename}/groups/{group_name}/hosts/{host_name}/connection-test",
    response_model=ManagedInventoryHostConnectionTestResult,
)
async def trigger_managed_inventory_host_connection_test(
    project_name: str,
    filename: str,
    group_name: str,
    host_name: str,
    db: AsyncSession = Depends(get_db),
):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    inventory_dir = get_project_inventory_dir(project_name)
    inventory_file = inventory_dir / filename
    if not inventory_file.is_file():
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")

    host = await _find_managed_inventory_host(db, project_name, filename, group_name, host_name)
    return await _run_managed_inventory_host_connection_test(project_name, filename, group_name, host_name, host)


@router.post(
    "/{project_name}/managed-inventories/{filename}/groups/{group_name}/connection-test",
    response_model=ManagedInventoryBulkConnectionTestResult,
)
async def trigger_managed_inventory_group_connection_test(
    project_name: str,
    filename: str,
    group_name: str,
    db: AsyncSession = Depends(get_db),
):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    inventory_dir = get_project_inventory_dir(project_name)
    inventory_file = inventory_dir / filename
    if not inventory_file.is_file():
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")

    group = await _find_managed_inventory_group(db, project_name, filename, group_name)
    return await _run_managed_inventory_group_connection_test(project_name, filename, group_name, group)


@router.post(
    "/{project_name}/managed-inventories/{filename}/connection-test",
    response_model=ManagedInventoryBulkConnectionTestResult,
)
async def trigger_managed_inventory_inventory_connection_test(
    project_name: str,
    filename: str,
    db: AsyncSession = Depends(get_db),
):
    if not any(p["name"] == project_name for p in get_projects()):
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if is_invalid_managed_inventory_filename(filename):
        raise HTTPException(status_code=400, detail="Invalid managed inventory filename")

    inventory_dir = get_project_inventory_dir(project_name)
    inventory_file = inventory_dir / filename
    if not inventory_file.is_file():
        raise HTTPException(status_code=404, detail=f"Managed inventory '{filename}' not found")

    groups = await _load_managed_inventory_groups(db, project_name, filename)
    return await _run_managed_inventory_inventory_connection_test(project_name, filename, groups)
