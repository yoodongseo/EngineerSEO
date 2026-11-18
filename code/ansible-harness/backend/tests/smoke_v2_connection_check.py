"""Smoke test for v2 connection-check endpoints.

Creates a v2 inventory with one local host, one ssh host, and one winrm host,
then exercises all three POST endpoints.  Runs against SQLite so no Postgres
or Docker is required.
"""

import asyncio
import os
import sys
from uuid import UUID

# Force SQLite + encryption key BEFORE any app import
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "test-key-00000000000")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY_ID", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import Base, async_session, engine
from app.main import app
from app.models.managed_inventory_v2 import (
    ManagedInventoryV2,
    ManagedInventoryV2Group,
    ManagedInventoryV2Host,
    ManagedInventoryV2HostMembership,
)
from app.schemas.job import (
    ManagedInventoryV2BulkConnectionCheckResult,
    ManagedInventoryV2HostConnectionCheckResult,
)

from httpx import ASGITransport, AsyncClient


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    inventory = ManagedInventoryV2(name="smoke-check-inv", source_type="native")
    group1 = ManagedInventoryV2Group(name="mixed_group", position=0, group_vars={})
    local_host = ManagedInventoryV2Host(
            name="local-box",
            address="127.0.0.1",
            connection_type="local",
            port=0,
            position=0,
    )
    ssh_host = ManagedInventoryV2Host(
            name="remote-ssh",
            address="192.0.2.1",
            connection_type="ssh",
            port=22,
            position=1,
    )
    winrm_host = ManagedInventoryV2Host(
            name="remote-winrm",
            address="198.51.100.1",
            connection_type="winrm",
            port=5986,
            position=2,
    )
    group1.host_memberships = [
        ManagedInventoryV2HostMembership(inventory=inventory, host=local_host, position=0),
        ManagedInventoryV2HostMembership(inventory=inventory, host=ssh_host, position=1),
        ManagedInventoryV2HostMembership(inventory=inventory, host=winrm_host, position=2),
    ]
    inventory.groups = [group1]

    async with async_session() as session:
        session.add(inventory)
        await session.flush()
        inv_id = inventory.id
        group_name = str(group1.name)
        await session.commit()

    print(f"Created inventory: id={inv_id}")

    transport = ASGITransport(app=app)
    results: list[str] = []

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Host connection-check (local -- should succeed immediately)
        r = await client.post(
            f"/api/inventories/{inv_id}/groups/{group_name}/hosts/local-box/connection-check"
        )
        assert r.status_code == 200, f"Host check failed: {r.status_code} {r.text}"
        host_result = ManagedInventoryV2HostConnectionCheckResult.model_validate(r.json())
        assert host_result.host_name == "local-box"
        assert host_result.group_name == group_name
        assert host_result.status == "success"
        assert host_result.failure_code is None
        assert host_result.checked_at is not None
        results.append(f"host-check local-box: status={host_result.status}")
        print(f"  PASS: {results[-1]}")

        # 2. Host connection-check (remote-ssh -- unreachable IP -> DNS failure)
        r = await client.post(
            f"/api/inventories/{inv_id}/groups/{group_name}/hosts/remote-ssh/connection-check"
        )
        assert r.status_code == 200, f"Host check remote-ssh failed: {r.status_code} {r.text}"
        host_result2 = ManagedInventoryV2HostConnectionCheckResult.model_validate(r.json())
        assert host_result2.host_name == "remote-ssh"
        assert host_result2.status == "failed"
        assert host_result2.failure_code is not None
        results.append(
            f"host-check remote-ssh: status={host_result2.status} code={host_result2.failure_code}"
        )
        print(f"  PASS: {results[-1]}")

        # 3. Group connection-check
        r = await client.post(
            f"/api/inventories/{inv_id}/groups/{group_name}/connection-check"
        )
        assert r.status_code == 200, f"Group check failed: {r.status_code} {r.text}"
        group_result = ManagedInventoryV2BulkConnectionCheckResult.model_validate(r.json())
        assert group_result.target.scope == "group"
        assert group_result.target.group_name == group_name
        assert group_result.summary.total_hosts == 3
        assert group_result.summary.success >= 1
        assert group_result.summary.failed >= 1
        results.append(
            f"group-check: total={group_result.summary.total_hosts} "
            f"success={group_result.summary.success} failed={group_result.summary.failed}"
        )
        print(f"  PASS: {results[-1]}")

        # 4. Inventory-wide connection-check
        r = await client.post(
            f"/api/inventories/{inv_id}/connection-check"
        )
        assert r.status_code == 200, f"Inventory check failed: {r.status_code} {r.text}"
        inv_result = ManagedInventoryV2BulkConnectionCheckResult.model_validate(r.json())
        assert inv_result.target.scope == "inventory"
        assert inv_result.target.inventory_id == inv_id
        assert inv_result.summary.total_hosts == 3
        results.append(
            f"inventory-check: total={inv_result.summary.total_hosts} "
            f"success={inv_result.summary.success} failed={inv_result.summary.failed}"
        )
        print(f"  PASS: {results[-1]}")

        # 5. Verify DB persistence via GET detail
        r = await client.get(f"/api/inventories/{inv_id}")
        assert r.status_code == 200, f"Inventory detail failed: {r.status_code} {r.text}"
        detail = r.json()
        persisted_hosts = detail["groups"][0]["hosts"]
        local_persisted = [h for h in persisted_hosts if h["name"] == "local-box"][0]
        assert local_persisted["connection_status"]["status"] == "success"
        assert local_persisted["connection_status"]["checked_at"] is not None
        results.append(
            f"db-persist local-box: status={local_persisted['connection_status']['status']}"
        )
        print(f"  PASS: {results[-1]}")

        # 6. 404 error paths
        r = await client.post(
            f"/api/inventories/{inv_id}/groups/nonexistent/hosts/local-box/connection-check"
        )
        assert r.status_code == 404, f"Expected 404 for bad group: got {r.status_code}"

        r = await client.post(
            f"/api/inventories/{UUID('00000000-0000-0000-0000-000000000000')}/connection-check"
        )
        assert r.status_code == 404, f"Expected 404 for bad inventory: got {r.status_code}"

        results.append("404-error-handling: PASS")
        print(f"  PASS: {results[-1]}")

    print(f"\n{'='*50}")
    print(f"SMOKE TEST RESULTS ({len(results)}/{len(results)} passed)")
    for line in results:
        print(f"  {line}")
    print(f"{'='*50}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    asyncio.run(main())
