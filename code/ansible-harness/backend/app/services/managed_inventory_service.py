"""DB-backed managed inventory service."""

import os
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.managed_inventory import ManagedInventory, ManagedInventoryGroup, ManagedInventoryHost
from app.schemas.inventories import (
    ManagedInventoryCreate,
    ManagedInventoryDetail,
    ManagedInventoryGroup as ManagedInventoryGroupSchema,
    ManagedInventoryGroupCreate,
    ManagedInventoryHost as ManagedInventoryHostSchema,
    ManagedInventoryListItem,
    ManagedInventoryUpdate,
)
from app.services.credential_service import decrypt_secret, get_project_credential
from app.services.inventory_renderer import RenderGroup, RenderHost, render_public_inventory, render_runtime_inventory


MANAGED_INVENTORY_STATUS_UNKNOWN = "unknown"


def get_project_inventory_dir(project_name: str) -> Path:
    from app.services import ansible_service

    return Path(ansible_service.settings.ANSIBLE_DATA_DIR) / "projects" / project_name / "inventory"


def is_invalid_managed_inventory_filename(filename: str) -> bool:
    return (
        not filename
        or filename in {".", ".."}
        or "/" in filename
        or "\\" in filename
        or ".." in Path(filename).parts
    )


async def get_managed_inventory_model(
    db: AsyncSession,
    project_name: str,
    filename: str,
) -> ManagedInventory | None:
    result = await db.execute(
        select(ManagedInventory)
        .options(selectinload(ManagedInventory.groups).selectinload(ManagedInventoryGroup.hosts))
        .where(ManagedInventory.project_name == project_name, ManagedInventory.filename == filename)
    )
    return result.scalar_one_or_none()


def _to_render_groups(inventory: ManagedInventory) -> list[RenderGroup]:
    groups: list[RenderGroup] = []
    for group in inventory.groups:
        hosts: list[RenderHost] = []
        for host in group.hosts:
            hosts.append(
                RenderHost(
                    name=str(host.name),
                    address=str(host.address),
                    connection_type=str(host.connection_type),
                    port=int(host.port),
                    remote_user=host.remote_user,
                    become_enabled=bool(host.become_enabled),
                    become_user=host.become_user,
                    login_credential_ref=host.ansibleharness_login_credential_ref,
                    become_credential_ref=host.ansibleharness_become_credential_ref,
                    login_credential_type=None,
                    become_credential_type=None,
                    login_credential_username=None,
                    become_credential_username=None,
                    host_vars=host.host_vars or {},
                )
            )
        groups.append(RenderGroup(name=str(group.name), group_vars=group.group_vars or {}, hosts=hosts))
    return groups


def _to_detail(inventory: ManagedInventory) -> ManagedInventoryDetail:
    groups = [
        ManagedInventoryGroupSchema(
            name=str(group.name),
            hosts=[
                ManagedInventoryHostSchema(
                    name=str(host.name),
                    address=str(host.address),
                    connection_type=str(host.connection_type),
                    port=int(host.port),
                    remote_user=host.remote_user,
                    become_enabled=bool(host.become_enabled),
                    become_user=host.become_user,
                    ansibleharness_login_credential_ref=host.ansibleharness_login_credential_ref,
                    ansibleharness_become_credential_ref=host.ansibleharness_become_credential_ref,
                    host_vars=host.host_vars or {},
                    connection_status={
                        "status": host.connection_status,
                        "checked_at": host.checked_at,
                        "failure_code": host.failure_code,
                        "failure_message": host.failure_message,
                    },
                )
                for host in group.hosts
            ],
        )
        for group in inventory.groups
    ]
    return ManagedInventoryDetail(
        name=str(inventory.filename),
        path=str(inventory.filename),
        status_summary=MANAGED_INVENTORY_STATUS_UNKNOWN,
        rendered_content=render_public_inventory(_to_render_groups(inventory)),
        groups=groups,
    )


async def list_managed_inventories(db: AsyncSession, project_name: str) -> list[ManagedInventoryListItem]:
    result = await db.execute(
        select(ManagedInventory)
        .where(ManagedInventory.project_name == project_name)
        .order_by(ManagedInventory.filename.asc())
    )
    return [
        ManagedInventoryListItem(
            name=str(inventory.filename),
            path=str(inventory.filename),
            status_summary=MANAGED_INVENTORY_STATUS_UNKNOWN,
        )
        for inventory in result.scalars().all()
    ]


async def validate_credential_refs(
    db: AsyncSession,
    project_name: str,
    groups: list[ManagedInventoryGroupCreate],
) -> None:
    for group in groups:
        for host in group.hosts:
            for credential_ref in (
                host.ansibleharness_login_credential_ref,
                host.ansibleharness_become_credential_ref,
            ):
                if credential_ref is not None and await get_project_credential(db, project_name, credential_ref) is None:
                    raise ValueError(f"Credential ref '{credential_ref}' does not belong to project '{project_name}'")


def _replace_groups(inventory: ManagedInventory, groups: list[ManagedInventoryGroupCreate]) -> None:
    inventory.groups.clear()
    for group_index, group_payload in enumerate(groups):
        group = ManagedInventoryGroup(
            name=group_payload.name,
            position=group_index,
            group_vars={},
        )
        for host_index, host_payload in enumerate(group_payload.hosts):
            group.hosts.append(
                ManagedInventoryHost(
                    name=host_payload.name,
                    address=host_payload.address,
                    connection_type=host_payload.connection_type,
                    port=host_payload.port,
                    remote_user=host_payload.remote_user,
                    become_enabled=host_payload.become_enabled,
                    become_user=host_payload.become_user,
                    ansibleharness_login_credential_ref=host_payload.ansibleharness_login_credential_ref,
                    ansibleharness_become_credential_ref=host_payload.ansibleharness_become_credential_ref,
                    host_vars=host_payload.host_vars,
                    position=host_index,
                )
            )
        inventory.groups.append(group)


def write_public_inventory_file(project_name: str, inventory: ManagedInventory) -> None:
    inventory_dir = get_project_inventory_dir(project_name)
    inventory_dir.mkdir(parents=True, exist_ok=True)
    target = inventory_dir / str(inventory.filename)
    target.write_text(render_public_inventory(_to_render_groups(inventory)), encoding="utf-8")


async def create_managed_inventory(
    db: AsyncSession,
    project_name: str,
    payload: ManagedInventoryCreate,
) -> ManagedInventoryDetail:
    await validate_credential_refs(db, project_name, payload.groups)
    inventory = ManagedInventory(project_name=project_name, filename=payload.filename)
    _replace_groups(inventory, payload.groups)
    db.add(inventory)
    await db.flush()
    write_public_inventory_file(project_name, inventory)
    return _to_detail(inventory)


async def update_managed_inventory(
    db: AsyncSession,
    project_name: str,
    filename: str,
    payload: ManagedInventoryUpdate,
) -> ManagedInventoryDetail | None:
    inventory = await get_managed_inventory_model(db, project_name, filename)
    if inventory is None:
        return None
    await validate_credential_refs(db, project_name, payload.groups)
    old_filename = str(inventory.filename)
    inventory.filename = payload.filename
    inventory.revision = int(inventory.revision) + 1
    _replace_groups(inventory, payload.groups)
    await db.flush()
    if old_filename != payload.filename:
        old_path = get_project_inventory_dir(project_name) / old_filename
        if old_path.exists():
            old_path.unlink()
    write_public_inventory_file(project_name, inventory)
    return _to_detail(inventory)


async def get_managed_inventory_detail(
    db: AsyncSession,
    project_name: str,
    filename: str,
) -> ManagedInventoryDetail | None:
    inventory = await get_managed_inventory_model(db, project_name, filename)
    return _to_detail(inventory) if inventory else None


async def delete_managed_inventory(db: AsyncSession, project_name: str, filename: str) -> bool:
    inventory = await get_managed_inventory_model(db, project_name, filename)
    if inventory is None:
        return False
    await db.delete(inventory)
    inventory_file = get_project_inventory_dir(project_name) / filename
    if inventory_file.exists():
        inventory_file.unlink()
    await db.flush()
    return True


async def materialize_runtime_inventory(
    db: AsyncSession,
    project_name: str,
    filename: str,
    private_data_dir: str,
) -> str | None:
    inventory = await get_managed_inventory_model(db, project_name, filename)
    if inventory is None:
        return None

    refs = sorted(
        {
            ref
            for group in inventory.groups
            for host in group.hosts
            for ref in (host.ansibleharness_login_credential_ref, host.ansibleharness_become_credential_ref)
            if ref
        }
    )
    secrets_by_ref: dict[str, str] = {}
    for ref in refs:
        credential = await get_project_credential(db, project_name, ref)
        if credential is not None:
            secrets_by_ref[ref] = decrypt_secret(credential)

    fd, path = tempfile.mkstemp(prefix="managed-runtime-", suffix=".ini", dir=private_data_dir, text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as runtime_file:
        runtime_file.write(render_runtime_inventory(_to_render_groups(inventory), secrets_by_ref))
    os.chmod(path, 0o600)
    return path
