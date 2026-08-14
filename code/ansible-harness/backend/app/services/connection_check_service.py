"""TCP-reachability connection check service for v2 managed inventories.

This is a lightweight adapter seam.  For MVP it performs async TCP
reachability checks.  Future iterations can swap in paramiko / pywinrm
authentication probes behind the same ``_check_host_reachability`` interface.
"""

import asyncio
import socket
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.managed_inventory_v2 import (
    ManagedInventoryV2,
    ManagedInventoryV2Group,
    ManagedInventoryV2Host,
    ManagedInventoryV2HostMembership,
)
from app.schemas.connection_checks import (
    ManagedInventoryV2BulkConnectionCheckResult,
    ManagedInventoryV2BulkConnectionCheckSummary,
    ManagedInventoryV2BulkConnectionCheckTarget,
    ManagedInventoryV2HostConnectionCheckResult,
)

_CHECK_TIMEOUT_SECONDS = 5


async def _check_tcp_reachability(
    host: str, port: int, timeout: float = _CHECK_TIMEOUT_SECONDS
) -> tuple[Literal["success", "failed"], str | None, str | None]:
    """Return (status, failure_code, failure_message) for TCP reachability."""
    try:
        try:
            await asyncio.wait_for(
                asyncio.get_event_loop().getaddrinfo(host, port),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return "failed", "dns_error", f"DNS resolution timed out for '{host}'"
        except socket.gaierror as exc:
            return "failed", "dns_error", f"DNS resolution failed for '{host}': {exc}"

        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            writer.close()
            await writer.wait_closed()
            return "success", None, None
        except asyncio.TimeoutError:
            return (
                "failed",
                "timeout",
                f"TCP connection to {host}:{port} timed out after {timeout}s",
            )
        except ConnectionRefusedError:
            return "failed", "refused", f"TCP connection to {host}:{port} was refused"
        except OSError as exc:
            return "failed", "unreachable", f"Cannot reach {host}:{port}: {exc}"
    except Exception as exc:
        return "failed", "unknown", str(exc)


async def _check_host_reachability(
    host_model: ManagedInventoryV2Host,
    group_name: str,
) -> ManagedInventoryV2HostConnectionCheckResult:
    """Check a single host and update its DB fields in-memory.

    Caller is responsible for ``await db.flush()`` after one or more calls.
    """
    connection_type = str(host_model.connection_type).lower()
    address = str(host_model.address)
    port = int(host_model.port)
    host_name = str(host_model.name)

    if connection_type == "local":
        status: Literal["success", "failed"] = "success"
        failure_code: str | None = None
        failure_message: str | None = None
    else:
        status, failure_code, failure_message = await _check_tcp_reachability(
            address, port
        )

    now = datetime.now(timezone.utc)

    host_model.connection_status = status
    host_model.checked_at = now
    host_model.failure_code = failure_code
    host_model.failure_message = failure_message

    return ManagedInventoryV2HostConnectionCheckResult(
        host_name=host_name,
        group_name=group_name,
        status=status,
        checked_at=now,
        failure_code=failure_code,
        failure_message=failure_message,
    )


def _load_inventory_query(inventory_id: UUID):
    """Return a select-statement with eager-loaded groups and hosts."""
    return (
        select(ManagedInventoryV2)
        .options(
            selectinload(ManagedInventoryV2.groups)
            .selectinload(ManagedInventoryV2Group.host_memberships)
            .selectinload(ManagedInventoryV2HostMembership.host),
        )
        .where(ManagedInventoryV2.id == inventory_id)
    )


def _build_bulk_result(
    inventory_id: UUID,
    scope: Literal["group", "inventory"],
    group_name: str | None,
    results: list[ManagedInventoryV2HostConnectionCheckResult],
) -> ManagedInventoryV2BulkConnectionCheckResult:
    summary = ManagedInventoryV2BulkConnectionCheckSummary(
        total_hosts=len(results),
        success=sum(1 for r in results if r.status == "success"),
        failed=sum(1 for r in results if r.status == "failed"),
        unknown=sum(1 for r in results if r.status == "unknown"),
        stale=sum(1 for r in results if r.status == "stale"),
    )
    target = ManagedInventoryV2BulkConnectionCheckTarget(
        inventory_id=inventory_id,
        scope=scope,
        group_name=group_name,
    )
    return ManagedInventoryV2BulkConnectionCheckResult(
        target=target,
        summary=summary,
        results=results,
    )


async def check_inventory_host(
    db: AsyncSession,
    inventory_id: UUID,
    group_name: str,
    host_name: str,
) -> ManagedInventoryV2HostConnectionCheckResult | None:
    """Check a single host within a group. Returns ``None`` if not found."""
    result = await db.execute(_load_inventory_query(inventory_id))
    inventory = result.scalar_one_or_none()
    if inventory is None:
        return None

    for group in inventory.groups:
        if group.name == group_name:
            for membership in group.host_memberships:
                host = membership.host
                if host.name == host_name:
                    check_result = await _check_host_reachability(host, str(group.name))
                    await db.flush()
                    return check_result
            return None
    return None


async def check_inventory_group(
    db: AsyncSession,
    inventory_id: UUID,
    group_name: str,
) -> ManagedInventoryV2BulkConnectionCheckResult | None:
    """Check all hosts in a group. Returns ``None`` if inventory or group is not found."""
    result = await db.execute(_load_inventory_query(inventory_id))
    inventory = result.scalar_one_or_none()
    if inventory is None:
        return None

    for group in inventory.groups:
        if group.name == group_name:
            results: list[ManagedInventoryV2HostConnectionCheckResult] = []
            for membership in group.host_memberships:
                results.append(await _check_host_reachability(membership.host, str(group.name)))
            await db.flush()
            return _build_bulk_result(
                inventory_id, "group", group_name, results
            )

    return None


async def check_inventory_all(
    db: AsyncSession,
    inventory_id: UUID,
) -> ManagedInventoryV2BulkConnectionCheckResult | None:
    """Check all hosts across every group. Returns ``None`` if inventory not found."""
    result = await db.execute(_load_inventory_query(inventory_id))
    inventory = result.scalar_one_or_none()
    if inventory is None:
        return None

    results = []
    for group in inventory.groups:
        for membership in group.host_memberships:
            results.append(await _check_host_reachability(membership.host, str(group.name)))

    await db.flush()
    return _build_bulk_result(inventory_id, "inventory", None, results)
