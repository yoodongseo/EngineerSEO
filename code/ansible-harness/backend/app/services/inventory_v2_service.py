"""Top-level managed inventory v2 and inventory-local credential service."""

import os
import tempfile
from datetime import datetime, timezone
from typing import TypeAlias
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
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
from app.schemas.credentials import (
    InventoryCredentialCreate,
    InventoryCredentialSummary,
    InventoryCredentialUpdate,
)
from app.schemas.inventories import (
    InventoryMigrationResult,
    ManagedInventoryV2Create,
    ManagedInventoryV2Detail,
    ManagedInventoryV2Group as ManagedInventoryV2GroupSchema,
    ManagedInventoryV2GroupCreate,
    ManagedInventoryV2Host as ManagedInventoryV2HostSchema,
    ManagedInventoryV2HostAttach,
    ManagedInventoryV2HostAssetDetail,
    ManagedInventoryV2HostAssetMembership,
    ManagedInventoryV2HostAssetCreate,
    ManagedInventoryV2HostAssetUpdate,
    ManagedInventoryV2HostCreate,
    ManagedInventoryV2ListItem,
    ManagedInventoryV2Membership,
    ManagedInventoryV2Update,
)
from app.services.credential_service import decrypt_secret_value, encrypt_secret
from app.services.inventory_renderer import RenderGroup, RenderHost, render_public_inventory, render_runtime_inventory_with_become


class HostAssetConflictError(RuntimeError):
    """Raised when an inventory-scoped host operation would affect another inventory."""


async def _build_unique_migrated_name(db: AsyncSession, preferred_name: str) -> str:
    """Return a user-facing migrated inventory name without exposing project provenance."""

    result = await db.execute(select(ManagedInventoryV2.name))
    existing_names = {str(name) for name in result.scalars().all()}
    if preferred_name not in existing_names:
        return preferred_name

    stem = preferred_name
    suffix = 2
    while f"{stem} ({suffix})" in existing_names:
        suffix += 1
    return f"{stem} ({suffix})"


CredentialRecord: TypeAlias = InventoryCredential | GlobalCredential


def _normalize_tags(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                normalized.append(stripped)
    return normalized


def _inventory_tags_from_model(inventory: ManagedInventoryV2) -> list[str]:
    tags = _normalize_tags(inventory.tags)
    return tags or _normalize_tags(inventory.badges)


def _group_tags_from_model(group: ManagedInventoryV2Group) -> list[str]:
    tags = _normalize_tags(group.tags)
    if tags:
        return tags
    preview_zone = (group.group_vars or {}).get("_preview_zone")
    if isinstance(preview_zone, str):
        stripped = preview_zone.strip()
        if stripped:
            return [stripped]
    return []


def _to_credential_summary(credential: CredentialRecord) -> InventoryCredentialSummary:
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


def _decrypt_credential_secret(credential: CredentialRecord) -> str:
    return decrypt_secret_value(str(credential.encrypted_secret), str(credential.nonce))


def _decrypt_become_secret(credential: CredentialRecord) -> str | None:
    if not credential.encrypted_become_secret or not credential.become_nonce:
        return None
    return decrypt_secret_value(str(credential.encrypted_become_secret), str(credential.become_nonce))


def _credential_has_become_account(credential: CredentialRecord) -> bool:
    return bool((credential.encrypted_become_secret and credential.become_nonce) or credential.become_username)


def _host_key_from_values(name: str, persisted_key: str | None = None) -> str:
    return persisted_key.strip() if persisted_key and persisted_key.strip() else name.strip()


def _host_schema_from_model(host: ManagedInventoryV2Host) -> ManagedInventoryV2HostSchema:
    return ManagedInventoryV2HostSchema(
        key=_host_key_from_values(str(host.name), host.host_key),
        name=str(host.name),
        address=str(host.address),
        connection_type=str(host.connection_type),
        port=int(host.port),
        remote_user=host.remote_user,
        become_enabled=bool(host.become_enabled),
        become_user=host.become_user,
        login_credential_ref=host.login_credential_ref,
        become_credential_ref=host.become_credential_ref,
        host_vars=host.host_vars or {},
        connection_status={
            "status": host.connection_status,
            "checked_at": host.checked_at,
            "failure_code": host.failure_code,
            "failure_message": host.failure_message,
        },
    )


def _host_create_from_asset(asset: ManagedInventoryV2HostAssetCreate) -> ManagedInventoryV2HostCreate:
    return ManagedInventoryV2HostCreate(
        key=asset.key,
        name=asset.name,
        address=asset.address,
        connection_type=asset.connection_type,
        port=asset.port,
        remote_user=asset.remote_user,
        become_enabled=asset.become_enabled,
        become_user=asset.become_user,
        login_credential_ref=asset.login_credential_ref,
        become_credential_ref=asset.become_credential_ref,
        host_vars=asset.host_vars,
    )


def _host_asset_detail_from_model(host: ManagedInventoryV2Host) -> ManagedInventoryV2HostAssetDetail:
    return ManagedInventoryV2HostAssetDetail(
        id=host.id,
        **_host_schema_from_model(host).model_dump(),
        memberships=[
            ManagedInventoryV2HostAssetMembership(
                inventory_id=membership.inventory_id,
                inventory_name=str(membership.inventory.name),
                group_name=str(membership.group.name),
            )
            for membership in host.memberships
        ],
    )


def _groups_from_host_contract(
    groups_payload: list[ManagedInventoryV2GroupCreate],
    hosts_payload: list[ManagedInventoryV2HostAssetCreate],
    memberships: list[ManagedInventoryV2Membership],
) -> list[ManagedInventoryV2GroupCreate]:
    hosts_by_key = {host.key: host for host in hosts_payload}
    membership_keys_by_group: dict[str, list[str]] = {}
    for membership in memberships:
        membership_keys_by_group.setdefault(membership.group_name, [])
        if membership.host_key not in membership_keys_by_group[membership.group_name]:
            membership_keys_by_group[membership.group_name].append(membership.host_key)

    normalized_groups: list[ManagedInventoryV2GroupCreate] = []
    seen_group_names: set[str] = set()
    for group in groups_payload:
        seen_group_names.add(group.name)
        ordered_keys = group.host_keys or membership_keys_by_group.get(group.name, [])
        normalized_groups.append(
            ManagedInventoryV2GroupCreate(
                name=group.name,
                tags=group.tags,
                group_vars=group.group_vars,
                hosts=[_host_create_from_asset(hosts_by_key[key]) for key in ordered_keys if key in hosts_by_key],
                host_keys=ordered_keys,
            )
        )

    for group_name, ordered_keys in membership_keys_by_group.items():
        if group_name in seen_group_names:
            continue
        normalized_groups.append(
            ManagedInventoryV2GroupCreate(
                name=group_name,
                hosts=[_host_create_from_asset(hosts_by_key[key]) for key in ordered_keys if key in hosts_by_key],
                host_keys=ordered_keys,
            )
        )
    return normalized_groups


def _payload_groups(payload: ManagedInventoryV2Create | ManagedInventoryV2Update) -> list[ManagedInventoryV2GroupCreate]:
    if payload.hosts or payload.memberships or any(group.host_keys for group in payload.groups):
        return _groups_from_host_contract(payload.groups, payload.hosts, payload.memberships)
    return payload.groups


async def _get_inventory_model(db: AsyncSession, inventory_id: UUID) -> ManagedInventoryV2 | None:
    result = await db.execute(
        select(ManagedInventoryV2)
        .options(
            selectinload(ManagedInventoryV2.groups)
            .selectinload(ManagedInventoryV2Group.host_memberships)
            .selectinload(ManagedInventoryV2HostMembership.host),
            selectinload(ManagedInventoryV2.host_memberships).selectinload(ManagedInventoryV2HostMembership.host),
            selectinload(ManagedInventoryV2.credentials),
        )
        .where(ManagedInventoryV2.id == inventory_id)
    )
    return result.scalar_one_or_none()


def _credential_refs_from_groups(groups_payload: list[ManagedInventoryV2GroupCreate]) -> set[str]:
    return {
        ref
        for group in groups_payload
        for host in group.hosts
        for ref in (host.login_credential_ref, host.become_credential_ref)
        if ref
    }


def _credential_refs_from_inventory(inventory: ManagedInventoryV2) -> set[str]:
    return {
        ref
        for membership in inventory.host_memberships
        for host in [membership.host]
        for ref in (host.login_credential_ref, host.become_credential_ref)
        if ref
    }


async def _get_active_global_credentials_by_ref(db: AsyncSession, refs: set[str]) -> dict[str, GlobalCredential]:
    if not refs:
        return {}
    result = await db.execute(
        select(GlobalCredential).where(GlobalCredential.ref.in_(refs), GlobalCredential.is_active.is_(True))
    )
    return {str(credential.ref): credential for credential in result.scalars().all()}


async def _get_render_credentials_for_inventory(db: AsyncSession, inventory: ManagedInventoryV2) -> list[GlobalCredential]:
    return list((await _get_active_global_credentials_by_ref(db, _credential_refs_from_inventory(inventory))).values())


def _to_render_groups(inventory: ManagedInventoryV2, credentials: list[CredentialRecord] | None = None) -> list[RenderGroup]:
    active_credentials = credentials if credentials is not None else [c for c in inventory.credentials if c.is_active]
    credential_types = {str(c.ref): str(c.credential_type) for c in active_credentials if c.is_active}
    credential_usernames = {str(c.ref): str(c.username) for c in active_credentials if c.is_active}
    credential_become_usernames = {
        str(c.ref): str(c.become_username)
        for c in active_credentials
        if c.is_active and c.become_username
    }
    groups: list[RenderGroup] = []
    for group in inventory.groups:
        hosts: list[RenderHost] = []
        for membership in group.host_memberships:
            host = membership.host
            login_ref = host.login_credential_ref
            become_ref = host.become_credential_ref
            become_username_ref = become_ref or login_ref
            hosts.append(
                RenderHost(
                    name=str(host.name),
                    address=str(host.address),
                    connection_type=str(host.connection_type),
                    port=int(host.port),
                    remote_user=host.remote_user,
                    become_enabled=bool(host.become_enabled),
                    become_user=host.become_user,
                    login_credential_ref=login_ref,
                    become_credential_ref=become_ref,
                    login_credential_type=credential_types.get(login_ref) if login_ref else None,
                    become_credential_type=credential_types.get(become_ref) if become_ref else None,
                    login_credential_username=credential_usernames.get(login_ref) if login_ref else None,
                    become_credential_username=credential_become_usernames.get(become_username_ref)
                    if become_username_ref
                    else None,
                    host_vars=host.host_vars or {},
                )
            )
        groups.append(RenderGroup(name=str(group.name), group_vars=group.group_vars or {}, hosts=hosts))
    return groups


def _filter_render_groups_for_target(
    groups: list[RenderGroup],
    target_scope: str | None,
    target_group_name: str | None,
    target_host_name: str | None,
    extra_vars: dict | None = None,
) -> list[RenderGroup]:
    normalized_scope = (target_scope or "inventory").strip() or "inventory"
    target_group_names = [g.strip() for g in target_group_name.split(",")] if target_group_name else []
    target_host_names = [h.strip() for h in target_host_name.split(",")] if target_host_name else []

    filtered_groups = groups
    if normalized_scope == "group" and target_group_names:
        filtered_groups = [group for group in groups if group.name in target_group_names]
    elif normalized_scope == "host" and target_host_names:
        temp_groups: list[RenderGroup] = []
        for group in groups:
            if target_group_names and group.name not in target_group_names:
                continue
            hosts = [host for host in group.hosts if host.name in target_host_names]
            if hosts:
                temp_groups.append(RenderGroup(name=group.name, group_vars=group.group_vars, hosts=hosts))
        filtered_groups = temp_groups

    # Inject dynamic group_vars and host_vars from extra_vars
    if extra_vars:
        dyn_group_vars = extra_vars.get("__group_vars__", {})
        dyn_host_vars = extra_vars.get("__host_vars__", {})
        
        for group in filtered_groups:
            if group.name in dyn_group_vars:
                # Merge group vars
                group.group_vars = {**group.group_vars, **dyn_group_vars[group.name]}
            for host in group.hosts:
                if host.name in dyn_host_vars:
                    # Merge host vars
                    host.host_vars = {**host.host_vars, **dyn_host_vars[host.name]}
                    
    return filtered_groups


def _to_detail(inventory: ManagedInventoryV2, credentials: list[CredentialRecord] | None = None) -> ManagedInventoryV2Detail:
    host_assets_by_key: dict[str, ManagedInventoryV2HostSchema] = {}
    memberships: list[ManagedInventoryV2Membership] = []
    groups = [
        ManagedInventoryV2GroupSchema(
            name=str(group.name),
            tags=_group_tags_from_model(group),
            group_vars=group.group_vars or {},
            host_keys=[
                _host_key_from_values(str(membership.host.name), membership.host.host_key)
                for membership in group.host_memberships
            ],
            hosts=[_host_schema_from_model(membership.host) for membership in group.host_memberships],
        )
        for group in inventory.groups
    ]
    for group in inventory.groups:
        for membership in group.host_memberships:
            host = membership.host
            key = _host_key_from_values(str(host.name), host.host_key)
            host_assets_by_key.setdefault(key, _host_schema_from_model(host))
            memberships.append(ManagedInventoryV2Membership(group_name=str(group.name), host_key=key))
    return ManagedInventoryV2Detail(
        id=inventory.id,
        name=str(inventory.name),
        description=str(inventory.description or ""),
        tags=_inventory_tags_from_model(inventory),
        revision=int(inventory.revision),
        source_type=str(inventory.source_type),
        rendered_content=render_public_inventory(_to_render_groups(inventory, credentials)),
        groups=groups,
        hosts=list(host_assets_by_key.values()),
        memberships=memberships,
    )


async def _replace_groups(db: AsyncSession, inventory: ManagedInventoryV2, groups_payload: list) -> None:
    normalized_host_payloads_by_key: dict[str, ManagedInventoryV2HostCreate] = {}
    for group_payload in groups_payload:
        for host_payload in group_payload.hosts:
            host_key = _host_key_from_values(host_payload.name, host_payload.key)
            existing_payload = normalized_host_payloads_by_key.get(host_key)
            if existing_payload is None:
                normalized_host_payloads_by_key[host_key] = host_payload
                continue
            if existing_payload.model_dump() != host_payload.model_dump():
                raise ValueError(
                    f"Conflicting host definitions detected for host key/name '{host_key}'"
                )
    existing_memberships = list(inventory.__dict__.get("host_memberships", []))
    existing_hosts_by_key = {
        _host_key_from_values(str(membership.host.name), membership.host.host_key): membership.host
        for membership in existing_memberships
    }
    hosts_by_key = {
        host_key: existing_hosts_by_key.get(host_key) or ManagedInventoryV2Host(host_key=host_key)
        for host_key in normalized_host_payloads_by_key
    }

    for membership in existing_memberships:
        membership.host.group_id = None
    await db.flush()

    if "groups" in inventory.__dict__:
        inventory.groups.clear()
    for host_key, host_payload in normalized_host_payloads_by_key.items():
        host = hosts_by_key[host_key]
        db.add(host)
        host.group_id = None
        host.host_key = host_key
        host.name = host_payload.name
        host.address = host_payload.address
        host.connection_type = host_payload.connection_type
        host.port = host_payload.port
        host.remote_user = host_payload.remote_user
        host.become_enabled = host_payload.become_enabled
        host.become_user = host_payload.become_user
        host.login_credential_ref = host_payload.login_credential_ref
        host.become_credential_ref = host_payload.become_credential_ref
        host.host_vars = host_payload.host_vars
    for group_index, group_payload in enumerate(groups_payload):
        group = ManagedInventoryV2Group(
            id=uuid4(),
            inventory=inventory,
            name=group_payload.name,
            position=group_index,
            tags=_normalize_tags(group_payload.tags),
            group_vars=group_payload.group_vars,
        )
        db.add(group)
        for host_index, host_payload in enumerate(group_payload.hosts):
            host_key = _host_key_from_values(host_payload.name, host_payload.key)
            host = hosts_by_key[host_key]
            host.group_id = group.id
            host.position = host_index
            group.host_memberships.append(
                ManagedInventoryV2HostMembership(
                    inventory=inventory,
                    host=host,
                    position=host_index,
                )
            )


async def _validate_credential_refs(db: AsyncSession, inventory: ManagedInventoryV2, groups_payload: list) -> None:
    credential_refs = _credential_refs_from_groups(groups_payload)
    active_credentials_by_ref = await _get_active_global_credentials_by_ref(db, credential_refs)
    for group in groups_payload:
        for host in group.hosts:
            for ref in (host.login_credential_ref, host.become_credential_ref):
                if ref and ref not in active_credentials_by_ref:
                    raise ValueError(f"Credential ref '{ref}' does not exist in the shared credential pool")
            if host.login_credential_ref:
                credential = active_credentials_by_ref[host.login_credential_ref]
                if credential.credential_type == "become_password":
                    raise ValueError("become_password credentials cannot be used as login credentials")


async def list_inventories(db: AsyncSession) -> list[ManagedInventoryV2ListItem]:
    result = await db.execute(
        select(ManagedInventoryV2)
        .options(
            selectinload(ManagedInventoryV2.groups),
            selectinload(ManagedInventoryV2.host_memberships),
        )
        .order_by(ManagedInventoryV2.name.asc())
    )
    return [
        ManagedInventoryV2ListItem(
            id=inv.id,
            name=str(inv.name),
            description=str(inv.description or ""),
            tags=_inventory_tags_from_model(inv),
            revision=int(inv.revision),
            source_type=str(inv.source_type),
            group_count=len(inv.groups),
            host_count=len({m.host_id for m in inv.host_memberships}),
        )
        for inv in result.scalars().unique().all()
    ]


async def list_host_assets(db: AsyncSession) -> list[ManagedInventoryV2HostAssetDetail]:
    result = await db.execute(
        select(ManagedInventoryV2Host)
        .options(
            selectinload(ManagedInventoryV2Host.memberships).selectinload(ManagedInventoryV2HostMembership.inventory),
            selectinload(ManagedInventoryV2Host.memberships).selectinload(ManagedInventoryV2HostMembership.group),
        )
        .order_by(ManagedInventoryV2Host.name.asc(), ManagedInventoryV2Host.address.asc())
    )
    return [_host_asset_detail_from_model(host) for host in result.scalars().unique().all()]


async def _get_host_asset_model(db: AsyncSession, host_id: UUID) -> ManagedInventoryV2Host | None:
    result = await db.execute(
        select(ManagedInventoryV2Host)
        .options(
            selectinload(ManagedInventoryV2Host.memberships).selectinload(ManagedInventoryV2HostMembership.inventory),
            selectinload(ManagedInventoryV2Host.memberships).selectinload(ManagedInventoryV2HostMembership.group),
        )
        .where(ManagedInventoryV2Host.id == host_id)
    )
    return result.scalar_one_or_none()


async def get_host_asset(db: AsyncSession, host_id: UUID) -> ManagedInventoryV2HostAssetDetail | None:
    host = await _get_host_asset_model(db, host_id)
    return _host_asset_detail_from_model(host) if host else None


async def _validate_host_asset_credentials(
    db: AsyncSession,
    *,
    login_credential_ref: str | None,
    become_credential_ref: str | None,
    become_enabled: bool,
) -> None:
    credential_refs = {ref for ref in (login_credential_ref, become_credential_ref) if ref}
    active_credentials_by_ref = await _get_active_global_credentials_by_ref(db, credential_refs)

    for ref in credential_refs:
        if ref not in active_credentials_by_ref:
            raise ValueError(f"Credential ref '{ref}' does not exist in the shared credential pool")

    if login_credential_ref:
        credential = active_credentials_by_ref[login_credential_ref]
        if credential.credential_type == "become_password":
            raise ValueError("become_password credentials cannot be used as login credentials")


async def update_host_asset(
    db: AsyncSession,
    host_id: UUID,
    payload: ManagedInventoryV2HostAssetUpdate,
) -> ManagedInventoryV2HostAssetDetail | None:
    host = await _get_host_asset_model(db, host_id)
    if host is None:
        return None

    fields = payload.model_fields_set
    name = payload.name.strip() if "name" in fields and payload.name is not None else str(host.name)
    address = payload.address.strip() if "address" in fields and payload.address is not None else str(host.address)
    if not name or not address:
        raise ValueError("Host name and address are required")

    login_credential_ref = (
        payload.login_credential_ref.strip()
        if "login_credential_ref" in fields and payload.login_credential_ref
        else None
        if "login_credential_ref" in fields
        else host.login_credential_ref
    )
    become_credential_ref = (
        payload.become_credential_ref.strip()
        if "become_credential_ref" in fields and payload.become_credential_ref
        else None
        if "become_credential_ref" in fields
        else host.become_credential_ref
    )
    become_enabled = bool(payload.become_enabled) if "become_enabled" in fields else bool(host.become_enabled)

    await _validate_host_asset_credentials(
        db,
        login_credential_ref=login_credential_ref,
        become_credential_ref=become_credential_ref,
        become_enabled=become_enabled,
    )

    host.name = name
    host.address = address
    if "connection_type" in fields and payload.connection_type is not None:
        host.connection_type = payload.connection_type
    if "port" in fields and payload.port is not None:
        host.port = payload.port
    if "remote_user" in fields:
        host.remote_user = payload.remote_user.strip() if payload.remote_user else None
    host.become_enabled = become_enabled
    if "become_user" in fields:
        host.become_user = payload.become_user.strip() if payload.become_user else None
    host.login_credential_ref = login_credential_ref
    host.become_credential_ref = become_credential_ref
    if "host_vars" in fields and payload.host_vars is not None:
        host.host_vars = payload.host_vars

    await db.flush()
    reloaded = await _get_host_asset_model(db, host_id)
    if reloaded is None:
        raise RuntimeError(f"Updated host asset '{host_id}' could not be reloaded")
    return _host_asset_detail_from_model(reloaded)


async def delete_host_asset(db: AsyncSession, host_id: UUID) -> bool:
    host = await db.get(ManagedInventoryV2Host, host_id)
    if host is None:
        return False

    await db.delete(host)
    await db.flush()
    return True


async def attach_host_to_inventory_group(
    db: AsyncSession,
    inventory_id: UUID,
    payload: ManagedInventoryV2HostAttach,
) -> ManagedInventoryV2Detail | None:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return None

    host = await db.get(ManagedInventoryV2Host, payload.host_id)
    if host is None:
        raise LookupError(f"Host asset '{payload.host_id}' not found")

    group_name = payload.group_name.strip()
    if not group_name:
        raise ValueError("Group name is required")

    group = next((item for item in inventory.groups if str(item.name) == group_name), None)
    if group is None:
        raise LookupError(f"Group '{group_name}' not found in inventory '{inventory_id}'")

    existing_result = await db.execute(
        select(ManagedInventoryV2HostMembership).where(
            ManagedInventoryV2HostMembership.inventory_id == inventory_id,
            ManagedInventoryV2HostMembership.group_id == group.id,
            ManagedInventoryV2HostMembership.host_id == host.id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise HostAssetConflictError(
            f"Host '{host.name}' is already linked to group '{group_name}' in inventory '{inventory.name}'"
        )

    next_position = max((membership.position for membership in group.host_memberships), default=-1) + 1
    group.host_memberships.append(
        ManagedInventoryV2HostMembership(inventory=inventory, host=host, position=next_position)
    )
    host.group_id = group.id
    host.position = next_position
    await db.flush()

    reloaded = await _get_inventory_model(db, inventory_id)
    if reloaded is None:
        raise RuntimeError(f"Inventory '{inventory_id}' could not be reloaded after host attach")
    credentials = await _get_render_credentials_for_inventory(db, reloaded)
    return _to_detail(reloaded, credentials)


async def create_inventory(db: AsyncSession, payload: ManagedInventoryV2Create) -> ManagedInventoryV2Detail:
    inventory = ManagedInventoryV2(
        name=payload.name,
        description=payload.description.strip(),
        tags=_normalize_tags(payload.tags),
        badges=_normalize_tags(payload.tags),
        source_type="native",
    )
    db.add(inventory)
    groups_payload = _payload_groups(payload)
    await _validate_credential_refs(db, inventory, groups_payload)
    await _replace_groups(db, inventory, groups_payload)
    await db.flush()
    reloaded = await _get_inventory_model(db, inventory.id)
    if reloaded is None:
        raise RuntimeError(f"Created inventory '{inventory.id}' could not be reloaded")
    credentials = await _get_render_credentials_for_inventory(db, reloaded)
    return _to_detail(reloaded, credentials)


async def get_inventory_detail(db: AsyncSession, inventory_id: UUID) -> ManagedInventoryV2Detail | None:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return None
    credentials = await _get_render_credentials_for_inventory(db, inventory)
    return _to_detail(inventory, credentials)


async def update_inventory(db: AsyncSession, inventory_id: UUID, payload: ManagedInventoryV2Update) -> ManagedInventoryV2Detail | None:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return None
    groups_payload = _payload_groups(payload)
    await _validate_credential_refs(db, inventory, groups_payload)
    inventory.name = payload.name
    inventory.description = payload.description.strip()
    inventory.tags = _normalize_tags(payload.tags)
    inventory.badges = _normalize_tags(payload.tags)
    inventory.revision = int(inventory.revision) + 1
    await _replace_groups(db, inventory, groups_payload)
    await db.flush()
    reloaded = await _get_inventory_model(db, inventory_id)
    if reloaded is None:
        raise RuntimeError(f"Updated inventory '{inventory_id}' could not be reloaded")
    credentials = await _get_render_credentials_for_inventory(db, reloaded)
    return _to_detail(reloaded, credentials)


async def delete_inventory(db: AsyncSession, inventory_id: UUID) -> bool:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return False
    for membership in inventory.host_memberships:
        membership.host.group_id = None
    await db.flush()
    await db.delete(inventory)
    await db.flush()
    return True


async def delete_inventory_host(db: AsyncSession, inventory_id: UUID, host_key: str) -> bool:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return False
    target_host: ManagedInventoryV2Host | None = None
    for membership in inventory.host_memberships:
        key = _host_key_from_values(str(membership.host.name), membership.host.host_key)
        if key == host_key:
            target_host = membership.host
            break
    if target_host is None:
        return False
    membership_result = await db.execute(
        select(ManagedInventoryV2HostMembership).where(
            ManagedInventoryV2HostMembership.host_id == target_host.id
        )
    )
    for membership in membership_result.scalars().all():
        if membership.inventory_id != inventory_id:
            raise HostAssetConflictError(
                f"Host '{host_key}' is still linked to another inventory and cannot be deleted here"
            )
    await db.delete(target_host)
    await db.flush()
    return True


async def list_inventory_credentials(db: AsyncSession, inventory_id: UUID) -> list[InventoryCredentialSummary]:
    return await list_global_credentials(db)


async def get_inventory_credential(db: AsyncSession, inventory_id: UUID, ref: str) -> GlobalCredential | None:
    return await get_global_credential(db, ref)


async def create_inventory_credential(
    db: AsyncSession,
    inventory_id: UUID,
    payload: InventoryCredentialCreate,
) -> InventoryCredentialSummary:
    return await create_global_credential(db, payload)


async def update_inventory_credential(
    db: AsyncSession,
    inventory_id: UUID,
    ref: str,
    payload: InventoryCredentialUpdate,
) -> InventoryCredentialSummary | None:
    return await update_global_credential(db, ref, payload)


async def delete_inventory_credential(db: AsyncSession, inventory_id: UUID, ref: str) -> bool:
    return await delete_global_credential(db, ref)


async def list_global_credentials(db: AsyncSession) -> list[InventoryCredentialSummary]:
    result = await db.execute(
        select(GlobalCredential).where(GlobalCredential.is_active.is_(True)).order_by(GlobalCredential.name.asc())
    )
    return [_to_credential_summary(c) for c in result.scalars().all()]


async def get_global_credential(db: AsyncSession, ref: str) -> GlobalCredential | None:
    result = await db.execute(
        select(GlobalCredential).where(GlobalCredential.ref == ref, GlobalCredential.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def create_global_credential(db: AsyncSession, payload: InventoryCredentialCreate) -> InventoryCredentialSummary:
    ciphertext, nonce = encrypt_secret(payload.secret)
    become_ciphertext: str | None = None
    become_nonce: str | None = None
    if payload.become_secret is not None:
        become_ciphertext, become_nonce = encrypt_secret(payload.become_secret)

    credential = GlobalCredential(
        ref=f"gcred_{uuid4().hex}",
        name=payload.name,
        credential_type=payload.credential_type,
        username=payload.username,
        become_username=payload.become_username,
        encrypted_secret=ciphertext,
        nonce=nonce,
        encrypted_become_secret=become_ciphertext,
        become_nonce=become_nonce,
        key_id=settings.CREDENTIAL_ENCRYPTION_KEY_ID,
    )
    db.add(credential)
    await db.flush()
    return _to_credential_summary(credential)


async def update_global_credential(
    db: AsyncSession,
    ref: str,
    payload: InventoryCredentialUpdate,
) -> InventoryCredentialSummary | None:
    credential = await get_global_credential(db, ref)
    if credential is None:
        return None
    credential.name = payload.name
    credential.username = payload.username
    if "become_username" in payload.model_fields_set:
        credential.become_username = payload.become_username
    if payload.secret is not None:
        ciphertext, nonce = encrypt_secret(payload.secret)
        credential.encrypted_secret = ciphertext
        credential.nonce = nonce
        credential.key_id = settings.CREDENTIAL_ENCRYPTION_KEY_ID
        credential.last_rotated_at = datetime.now(timezone.utc)
    if payload.clear_become_secret:
        credential.encrypted_become_secret = None
        credential.become_nonce = None
        credential.last_rotated_at = datetime.now(timezone.utc)
    elif payload.become_secret is not None:
        become_ciphertext, become_nonce = encrypt_secret(payload.become_secret)
        credential.encrypted_become_secret = become_ciphertext
        credential.become_nonce = become_nonce
        credential.key_id = settings.CREDENTIAL_ENCRYPTION_KEY_ID
        credential.last_rotated_at = datetime.now(timezone.utc)
    await db.flush()
    return _to_credential_summary(credential)


async def _global_credential_is_referenced(db: AsyncSession, ref: str) -> bool:
    v2_result = await db.execute(
        select(ManagedInventoryV2Host.id).where(
            (ManagedInventoryV2Host.login_credential_ref == ref) | (ManagedInventoryV2Host.become_credential_ref == ref)
        )
    )
    if v2_result.first() is not None:
        return True

    legacy_result = await db.execute(
        select(ManagedInventoryHost.id).where(
            (ManagedInventoryHost.ansibleharness_login_credential_ref == ref)
            | (ManagedInventoryHost.ansibleharness_become_credential_ref == ref)
        )
    )
    return legacy_result.first() is not None


async def delete_global_credential(db: AsyncSession, ref: str) -> bool:
    credential = await get_global_credential(db, ref)
    if credential is None:
        return False
    if await _global_credential_is_referenced(db, ref):
        raise ValueError(f"Credential '{ref}' is still used by one or more hosts")
    credential.is_active = False
    await db.flush()
    return True


async def migrate_legacy_managed_inventories(db: AsyncSession) -> InventoryMigrationResult:
    result = await db.execute(
        select(ManagedInventory)
        .options(
            selectinload(ManagedInventory.groups).selectinload(ManagedInventoryGroup.hosts),
        )
    )
    legacy = result.scalars().all()
    migrated = 0
    skipped = 0
    errors: list[str] = []
    for inv in legacy:
        existing = await db.execute(
            select(ManagedInventoryV2).where(
                ManagedInventoryV2.source_type == "legacy_project",
                ManagedInventoryV2.source_legacy_project == inv.project_name,
                ManagedInventoryV2.source_legacy_filename == inv.filename,
            )
        )
        if existing.scalar_one_or_none() is not None:
            skipped += 1
            continue

        referenced_refs = {
            ref
            for group in inv.groups
            for host in group.hosts
            for ref in (host.ansibleharness_login_credential_ref, host.ansibleharness_become_credential_ref)
            if ref
        }

        v2 = ManagedInventoryV2(
            name=await _build_unique_migrated_name(db, str(inv.filename)),
            revision=int(inv.revision),
            source_type="legacy_project",
            source_legacy_project=inv.project_name,
            source_legacy_filename=inv.filename,
            source_legacy_inventory_id=inv.id,
        )
        for gidx, group in enumerate(inv.groups):
            v2g = ManagedInventoryV2Group(name=group.name, position=gidx, group_vars=group.group_vars or {})
            for hidx, host in enumerate(group.hosts):
                v2_host = ManagedInventoryV2Host(
                    host_key=host.name,
                    name=host.name,
                    address=host.address,
                    connection_type=host.connection_type,
                    port=host.port,
                    remote_user=host.remote_user,
                    become_enabled=host.become_enabled,
                    become_user=host.become_user,
                    login_credential_ref=host.ansibleharness_login_credential_ref,
                    become_credential_ref=host.ansibleharness_become_credential_ref,
                    host_vars=host.host_vars or {},
                    position=hidx,
                    connection_status=host.connection_status,
                    checked_at=host.checked_at,
                    failure_code=host.failure_code,
                    failure_message=host.failure_message,
                )
                v2g.host_memberships.append(
                    ManagedInventoryV2HostMembership(inventory=v2, host=v2_host, position=hidx)
                )
            v2.groups.append(v2g)

        creds = await db.execute(
            select(ProjectCredential).where(
                ProjectCredential.project_name == inv.project_name,
                ProjectCredential.is_active.is_(True),
                ProjectCredential.ref.in_(referenced_refs),
            )
        )
        for cred in creds.scalars().all():
            if await get_global_credential(db, str(cred.ref)) is None:
                db.add(
                    GlobalCredential(
                        ref=str(cred.ref),
                        name=str(cred.name),
                        credential_type=str(cred.credential_type),
                        username=str(cred.username),
                        encrypted_secret=str(cred.encrypted_secret),
                        nonce=str(cred.nonce),
                        key_id=str(cred.key_id),
                        is_active=bool(cred.is_active),
                        last_rotated_at=cred.last_rotated_at,
                    )
                )
            v2.credentials.append(
                InventoryCredential(
                    ref=str(cred.ref),
                    name=str(cred.name),
                    credential_type=str(cred.credential_type),
                    username=str(cred.username),
                    encrypted_secret=str(cred.encrypted_secret),
                    nonce=str(cred.nonce),
                    key_id=str(cred.key_id),
                    is_active=bool(cred.is_active),
                    last_rotated_at=cred.last_rotated_at,
                )
            )

        db.add(v2)
        try:
            await db.flush()
            migrated += 1
        except Exception as exc:
            errors.append(f"{inv.project_name}/{inv.filename}: {exc}")
    return InventoryMigrationResult(migrated=migrated, skipped_existing=skipped, errors=errors)


async def materialize_v2_runtime_inventory(
    db: AsyncSession,
    inventory_id: UUID,
    private_data_dir: str,
    target_scope: str | None = None,
    target_group_name: str | None = None,
    target_host_name: str | None = None,
    extra_vars: dict | None = None,
    inventory_vars: dict | None = None,
) -> tuple[str, int] | None:
    inventory = await _get_inventory_model(db, inventory_id)
    if inventory is None:
        return None

    refs = sorted(
        {
            ref
            for membership in inventory.host_memberships
            for host in [membership.host]
            for ref in (host.login_credential_ref, host.become_credential_ref)
            if ref
        }
    )
    secrets_by_ref: dict[str, str] = {}
    become_secrets_by_ref: dict[str, str] = {}
    credentials = list((await _get_active_global_credentials_by_ref(db, set(refs))).values())
    credentials_by_ref = {str(credential.ref): credential for credential in credentials}
    for ref in refs:
        credential = credentials_by_ref.get(ref)
        if credential is not None:
            secrets_by_ref[ref] = _decrypt_credential_secret(credential)
            become_secret = _decrypt_become_secret(credential)
            if become_secret is not None:
                become_secrets_by_ref[ref] = become_secret

    fd, path = tempfile.mkstemp(prefix="managed-v2-runtime-", suffix=".ini", dir=private_data_dir, text=True)
    render_groups = _filter_render_groups_for_target(
        _to_render_groups(inventory, credentials),
        target_scope,
        target_group_name,
        target_host_name,
        extra_vars,
    )
    with os.fdopen(fd, "w", encoding="utf-8") as runtime_file:
        runtime_file.write(render_runtime_inventory_with_become(render_groups, secrets_by_ref, become_secrets_by_ref, inventory_vars))
    os.chmod(path, 0o600)
    return path, int(inventory.revision)
