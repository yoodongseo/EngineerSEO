"""Inventory-related backend contract tests."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _backend_cwd(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])


def _assert_unknown_status_managed_inventory_list(payload, expected_names):
    assert payload == [
        {
            "name": name,
            "path": name,
            "status_summary": "unknown",
        }
        for name in expected_names
    ]


def _unknown_connection_status():
    return {
        "status": "unknown",
        "checked_at": None,
        "failure_code": None,
        "failure_message": None,
    }


async def test_list_project_inventories_returns_project_file_list(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/inventories")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload
    assert payload == [
        {
            "name": "hosts.sample",
            "path": "hosts.sample",
        }
    ]


async def test_global_credentials_are_shared_across_v2_inventories(async_client):
    suffix = uuid4().hex
    credential_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"shared-login-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "secret-value",
        },
    )
    assert credential_response.status_code == 201
    credential_ref = credential_response.json()["ref"]

    first_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-credential-inventory-a-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-a",
                            "address": "10.10.0.1",
                            "login_credential_ref": credential_ref,
                        }
                    ],
                }
            ],
        },
    )
    assert first_response.status_code == 201

    second_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-credential-inventory-b-{suffix}",
            "groups": [
                {
                    "name": "db",
                    "hosts": [
                        {
                            "name": "db-b",
                            "address": "10.10.0.2",
                            "login_credential_ref": credential_ref,
                        }
                    ],
                }
            ],
        },
    )
    assert second_response.status_code == 201
    assert second_response.json()["hosts"][0]["login_credential_ref"] == credential_ref

    alias_response = await async_client.get(f"/api/inventories/{first_response.json()['id']}/credentials")
    assert alias_response.status_code == 200
    assert credential_ref in [item["ref"] for item in alias_response.json()]


async def test_inventory_v2_persists_description_and_tags(async_client):
    suffix = uuid4().hex

    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    create_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"metadata-inventory-{suffix}",
            "description": "운영 서버 인벤토리",
            "tags": ["production", "linux"],
            "groups": [],
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["description"] == "운영 서버 인벤토리"
    assert created_payload["tags"] == ["production", "linux"]
    assert "badges" not in created_payload

    inventory_id = created_payload["id"]
    update_response = await async_client.put(
        f"/api/inventories/{inventory_id}",
        json={
            "name": f"metadata-inventory-renamed-{suffix}",
            "description": "수정된 설명",
            "tags": ["staging", "windows"],
            "groups": [],
        },
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["description"] == "수정된 설명"
    assert updated_payload["tags"] == ["staging", "windows"]

    get_response = await async_client.get(f"/api/inventories/{inventory_id}")
    assert get_response.status_code == 200
    persisted_payload = get_response.json()
    assert persisted_payload["description"] == "수정된 설명"
    assert persisted_payload["tags"] == ["staging", "windows"]


async def test_inventory_v2_accepts_legacy_badges_and_group_preview_zone(async_client):
    suffix = uuid4().hex

    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    create_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"legacy-tag-compat-{suffix}",
            "description": "legacy payload",
            "badges": ["legacy", "prod"],
            "groups": [
                {
                    "name": "preview",
                    "group_vars": {"_preview_zone": "dmz"},
                }
            ],
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["tags"] == ["legacy", "prod"]
    assert payload["groups"] == [
        {
            "name": "preview",
            "tags": ["dmz"],
            "group_vars": {"_preview_zone": "dmz"},
            "host_keys": [],
            "hosts": [],
        }
    ]


async def test_inventory_v2_persists_group_tags(async_client):
    suffix = uuid4().hex

    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    create_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"group-tags-{suffix}",
            "description": "group tags",
            "tags": ["shared"],
            "groups": [
                {
                    "name": "web",
                    "tags": ["production", "linux"],
                }
            ],
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()
    assert created_payload["groups"][0]["tags"] == ["production", "linux"]

    inventory_id = created_payload["id"]
    update_response = await async_client.put(
        f"/api/inventories/{inventory_id}",
        json={
            "name": f"group-tags-updated-{suffix}",
            "description": "group tags updated",
            "tags": ["shared", "updated"],
            "groups": [
                {
                    "name": "web",
                    "tags": ["staging"],
                }
            ],
        },
    )

    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["groups"][0]["tags"] == ["staging"]

    get_response = await async_client.get(f"/api/inventories/{inventory_id}")
    assert get_response.status_code == 200
    persisted_payload = get_response.json()
    assert persisted_payload["tags"] == ["shared", "updated"]
    assert persisted_payload["groups"][0]["tags"] == ["staging"]


async def test_inventory_v2_reads_backfilled_legacy_db_tags(async_client):
    suffix = uuid4().hex

    from sqlalchemy import select  # type: ignore[reportMissingImports]

    from app.database import async_session, init_db  # type: ignore[reportMissingImports]
    from app.models.managed_inventory_v2 import (  # type: ignore[reportMissingImports]
        ManagedInventoryV2,
        ManagedInventoryV2Group,
    )

    await init_db()

    inventory = ManagedInventoryV2(
        name=f"legacy-db-tags-{suffix}",
        description="legacy db row",
        tags=[],
        badges=["legacy-db", "prod"],
        source_type="native",
    )

    async with async_session() as session:
        session.add(inventory)
        await session.flush()
        session.add(
            ManagedInventoryV2Group(
                inventory_id=inventory.id,
                name="preview",
                position=0,
                tags=[],
                group_vars={"_preview_zone": "dmz"},
            )
        )
        await session.commit()

    await init_db()

    async with async_session() as session:
        persisted_inventory = await session.get(ManagedInventoryV2, inventory.id)
        persisted_group = (
            await session.execute(
                select(ManagedInventoryV2Group).where(ManagedInventoryV2Group.inventory_id == inventory.id)
            )
        ).scalar_one()

    assert persisted_inventory is not None
    assert persisted_inventory.tags == ["legacy-db", "prod"]
    assert persisted_group.tags == ["dmz"]

    detail_response = await async_client.get(f"/api/inventories/{inventory.id}")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["tags"] == ["legacy-db", "prod"]
    assert payload["groups"][0]["tags"] == ["dmz"]


async def test_inventory_v2_rejects_missing_global_credential_ref(async_client):
    suffix = uuid4().hex
    response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"missing-global-credential-ref-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-missing",
                            "address": "10.10.1.1",
                            "login_credential_ref": "gcred_missing",
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "shared credential pool" in response.json()["detail"]


async def test_delete_inventory_preserves_host_asset_and_removes_memberships(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"delete-inventory-preserve-host-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": f"preserved-host-{suffix}",
                            "address": "10.20.0.1",
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201
    inventory_payload = inventory_response.json()
    inventory_id = UUID(inventory_payload["id"])
    host_key = inventory_payload["hosts"][0]["key"]

    from sqlalchemy import select  # type: ignore[reportMissingImports]

    from app.database import async_session  # type: ignore[reportMissingImports]
    from app.models.managed_inventory_v2 import (  # type: ignore[reportMissingImports]
        ManagedInventoryV2Host,
        ManagedInventoryV2HostMembership,
    )

    async with async_session() as session:
        host_result = await session.execute(
            select(ManagedInventoryV2Host).where(ManagedInventoryV2Host.host_key == host_key)
        )
        host = host_result.scalar_one()
        host_id = host.id

    delete_response = await async_client.delete(f"/api/inventories/{inventory_id}")

    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/inventories/{inventory_id}")
    assert get_response.status_code == 404

    async with async_session() as session:
        preserved_host = await session.get(ManagedInventoryV2Host, host_id)
        membership_result = await session.execute(
            select(ManagedInventoryV2HostMembership).where(
                ManagedInventoryV2HostMembership.host_id == host_id
            )
        )

    assert preserved_host is not None
    assert preserved_host.host_key == host_key
    assert membership_result.scalars().all() == []


async def test_delete_inventory_host_removes_host_asset_and_memberships(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"delete-host-asset-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": f"host-delete-target-{suffix}",
                            "address": "10.20.0.2",
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201
    inventory_payload = inventory_response.json()
    inventory_id = UUID(inventory_payload["id"])
    host_key = inventory_payload["hosts"][0]["key"]

    from sqlalchemy import select  # type: ignore[reportMissingImports]

    from app.database import async_session  # type: ignore[reportMissingImports]
    from app.models.managed_inventory_v2 import (  # type: ignore[reportMissingImports]
        ManagedInventoryV2Host,
        ManagedInventoryV2HostMembership,
    )

    async with async_session() as session:
        host_result = await session.execute(
            select(ManagedInventoryV2Host).where(ManagedInventoryV2Host.host_key == host_key)
        )
        host = host_result.scalar_one()
        host_id = host.id

    delete_response = await async_client.delete(f"/api/inventories/{inventory_id}/hosts/{host_key}")

    assert delete_response.status_code == 204

    detail_response = await async_client.get(f"/api/inventories/{inventory_id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["hosts"] == []
    assert detail_payload["memberships"] == []
    assert detail_payload["groups"][0]["host_keys"] == []

    missing_response = await async_client.delete(f"/api/inventories/{inventory_id}/hosts/{host_key}")
    assert missing_response.status_code == 404

    async with async_session() as session:
        deleted_host = await session.get(ManagedInventoryV2Host, host_id)
        membership_result = await session.execute(
            select(ManagedInventoryV2HostMembership).where(
                ManagedInventoryV2HostMembership.host_id == host_id
            )
        )

    assert deleted_host is None
    assert membership_result.scalars().all() == []


async def test_same_host_key_across_inventories_does_not_share_or_delete_other_asset(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    first_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-host-name-a-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": f"shared-host-{suffix}",
                            "address": "10.20.1.1",
                        }
                    ],
                }
            ],
        },
    )
    assert first_response.status_code == 201

    second_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-host-name-b-{suffix}",
            "groups": [
                {
                    "name": "db",
                    "hosts": [
                        {
                            "name": f"shared-host-{suffix}",
                            "address": "10.20.1.2",
                        }
                    ],
                }
            ],
        },
    )
    assert second_response.status_code == 201

    first_payload = first_response.json()
    second_payload = second_response.json()
    host_key = first_payload["hosts"][0]["key"]
    assert second_payload["hosts"][0]["key"] == host_key

    delete_response = await async_client.delete(f"/api/inventories/{first_payload['id']}/hosts/{host_key}")
    assert delete_response.status_code == 204

    first_detail = await async_client.get(f"/api/inventories/{first_payload['id']}")
    second_detail = await async_client.get(f"/api/inventories/{second_payload['id']}")

    assert first_detail.status_code == 200
    assert second_detail.status_code == 200
    assert first_detail.json()["hosts"] == []
    assert len(second_detail.json()["hosts"]) == 1
    assert second_detail.json()["hosts"][0]["address"] == "10.20.1.2"


async def test_same_inventory_host_can_belong_to_multiple_groups(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    create_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"multi-group-host-{suffix}",
            "groups": [
                {"name": "web"},
                {"name": "prod"},
            ],
            "hosts": [
                {
                    "key": f"shared-host-{suffix}",
                    "name": f"shared-host-{suffix}",
                    "address": "10.20.2.1",
                }
            ],
            "memberships": [
                {"group_name": "web", "host_key": f"shared-host-{suffix}"},
                {"group_name": "prod", "host_key": f"shared-host-{suffix}"},
            ],
        },
    )
    assert create_response.status_code == 201

    detail_payload = create_response.json()
    assert len(detail_payload["hosts"]) == 1
    assert sorted(detail_payload["groups"][0]["host_keys"] + detail_payload["groups"][1]["host_keys"]) == [
        f"shared-host-{suffix}",
        f"shared-host-{suffix}",
    ]
    assert sorted(detail_payload["memberships"], key=lambda item: item["group_name"]) == [
        {"group_name": "prod", "host_key": f"shared-host-{suffix}"},
        {"group_name": "web", "host_key": f"shared-host-{suffix}"},
    ]

    fetch_response = await async_client.get(f"/api/inventories/{detail_payload['id']}")
    assert fetch_response.status_code == 200
    fetched = fetch_response.json()
    assert len(fetched["hosts"]) == 1
    assert sorted(fetched["memberships"], key=lambda item: item["group_name"]) == [
        {"group_name": "prod", "host_key": f"shared-host-{suffix}"},
        {"group_name": "web", "host_key": f"shared-host-{suffix}"},
    ]


async def test_list_host_assets_includes_orphan_and_membership_context(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    orphan_source_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"orphan-source-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": f"orphan-host-{suffix}",
                            "address": "10.20.3.1",
                        }
                    ],
                }
            ],
        },
    )
    assert orphan_source_response.status_code == 201
    orphan_source_payload = orphan_source_response.json()
    orphan_key = orphan_source_payload["hosts"][0]["key"]

    attached_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"attached-source-{suffix}",
            "groups": [
                {
                    "name": "prod",
                    "hosts": [
                        {
                            "name": f"attached-host-{suffix}",
                            "address": "10.20.3.2",
                        }
                    ],
                }
            ],
        },
    )
    assert attached_response.status_code == 201
    attached_payload = attached_response.json()
    attached_key = attached_payload["hosts"][0]["key"]

    delete_response = await async_client.delete(f"/api/inventories/{orphan_source_payload['id']}")
    assert delete_response.status_code == 204

    host_assets_response = await async_client.get("/api/hosts")
    assert host_assets_response.status_code == 200
    host_assets = host_assets_response.json()
    host_assets_by_key = {host["key"]: host for host in host_assets}

    assert orphan_key in host_assets_by_key
    assert host_assets_by_key[orphan_key]["memberships"] == []
    assert host_assets_by_key[orphan_key]["address"] == "10.20.3.1"

    assert attached_key in host_assets_by_key
    assert host_assets_by_key[attached_key]["memberships"] == [
        {
            "inventory_id": attached_payload["id"],
            "inventory_name": f"attached-source-{suffix}",
            "group_name": "prod",
        }
    ]


async def test_update_host_asset_by_id_updates_fields(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"host-asset-update-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": f"host-asset-update-target-{suffix}",
                            "address": "10.20.4.1",
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201
    host_key = inventory_response.json()["hosts"][0]["key"]

    host_assets_response = await async_client.get("/api/hosts")
    host_asset = next(host for host in host_assets_response.json() if host["key"] == host_key)

    update_response = await async_client.patch(
        f"/api/hosts/{host_asset['id']}",
        json={
            "name": f"host-asset-updated-{suffix}",
            "address": "10.20.4.99",
            "connection_type": "local",
            "port": 1,
            "host_vars": {"ansibleharness_preview_platform": "Linux", "note": "updated"},
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["id"] == host_asset["id"]
    assert updated["name"] == f"host-asset-updated-{suffix}"
    assert updated["address"] == "10.20.4.99"
    assert updated["connection_type"] == "local"
    assert updated["memberships"] == host_asset["memberships"]


async def test_attach_orphan_host_asset_to_inventory_group(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    orphan_source_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"attach-orphan-source-{suffix}",
            "groups": [{"name": "old", "hosts": [{"name": f"attach-orphan-{suffix}", "address": "10.20.5.1"}]}],
        },
    )
    assert orphan_source_response.status_code == 201
    orphan_payload = orphan_source_response.json()
    orphan_key = orphan_payload["hosts"][0]["key"]
    assert (await async_client.delete(f"/api/inventories/{orphan_payload['id']}")).status_code == 204

    target_response = await async_client.post(
        "/api/inventories",
        json={"name": f"attach-orphan-target-{suffix}", "groups": [{"name": "new"}]},
    )
    assert target_response.status_code == 201
    target_payload = target_response.json()

    host_assets_response = await async_client.get("/api/hosts")
    host_asset = next(host for host in host_assets_response.json() if host["key"] == orphan_key)
    assert host_asset["memberships"] == []

    attach_response = await async_client.post(
        f"/api/inventories/{target_payload['id']}/hosts",
        json={"host_id": host_asset["id"], "group_name": "new"},
    )

    assert attach_response.status_code == 200
    attached = attach_response.json()
    assert attached["hosts"][0]["key"] == orphan_key
    assert attached["memberships"] == [{"group_name": "new", "host_key": orphan_key}]


async def test_attach_host_asset_to_another_inventory_and_reject_duplicate(async_client):
    suffix = uuid4().hex
    from app.database import init_db  # type: ignore[reportMissingImports]

    await init_db()

    source_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"attach-source-{suffix}",
            "groups": [{"name": "web", "hosts": [{"name": f"attach-shared-{suffix}", "address": "10.20.6.1"}]}],
        },
    )
    assert source_response.status_code == 201
    source_payload = source_response.json()
    host_key = source_payload["hosts"][0]["key"]

    target_response = await async_client.post(
        "/api/inventories",
        json={"name": f"attach-target-{suffix}", "groups": [{"name": "prod"}]},
    )
    assert target_response.status_code == 201
    target_payload = target_response.json()

    host_assets_response = await async_client.get("/api/hosts")
    host_asset = next(host for host in host_assets_response.json() if host["key"] == host_key)

    attach_response = await async_client.post(
        f"/api/inventories/{target_payload['id']}/hosts",
        json={"host_id": host_asset["id"], "group_name": "prod"},
    )
    assert attach_response.status_code == 200

    duplicate_response = await async_client.post(
        f"/api/inventories/{target_payload['id']}/hosts",
        json={"host_id": host_asset["id"], "group_name": "prod"},
    )
    assert duplicate_response.status_code == 409

    refreshed_assets_response = await async_client.get("/api/hosts")
    refreshed_asset = next(host for host in refreshed_assets_response.json() if host["id"] == host_asset["id"])
    assert sorted(membership["inventory_name"] for membership in refreshed_asset["memberships"]) == [
        f"attach-source-{suffix}",
        f"attach-target-{suffix}",
    ]


async def test_delete_global_credential_rejects_active_host_reference(async_client):
    suffix = uuid4().hex
    credential_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"shared-delete-guard-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "secret-value",
        },
    )
    assert credential_response.status_code == 201
    credential_ref = credential_response.json()["ref"]

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-delete-guard-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-delete-guard",
                            "address": "10.10.2.1",
                            "login_credential_ref": credential_ref,
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201

    delete_response = await async_client.delete(f"/api/credentials/{credential_ref}")

    assert delete_response.status_code == 409
    assert "still used" in delete_response.json()["detail"]


async def test_v2_inventory_uses_login_credential_embedded_become_account(async_client):
    suffix = uuid4().hex
    credential_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"shared-login-with-become-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "login-secret",
            "become_username": "root",
            "become_secret": "become-secret",
        },
    )
    assert credential_response.status_code == 201
    credential_ref = credential_response.json()["ref"]

    response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-login-become-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-become",
                            "address": "10.10.3.1",
                            "login_credential_ref": credential_ref,
                            "become_enabled": True,
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["hosts"][0]["login_credential_ref"] == credential_ref
    assert payload["hosts"][0]["become_enabled"] is True
    assert payload["hosts"][0]["become_credential_ref"] is None
    assert "ansible_become=true" in payload["rendered_content"]
    assert "ansible_become_user=root" in payload["rendered_content"]


async def test_v2_runtime_inventory_injects_login_credential_embedded_become_secret(async_client, tmp_path):
    suffix = uuid4().hex
    credential_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"runtime-login-with-become-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "login-secret",
            "become_username": "root",
            "become_secret": "become-secret",
        },
    )
    assert credential_response.status_code == 201
    credential_ref = credential_response.json()["ref"]

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"runtime-login-become-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-runtime-become",
                            "address": "10.10.3.2",
                            "login_credential_ref": credential_ref,
                            "become_enabled": True,
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201

    from app.database import async_session  # type: ignore[reportMissingImports]
    from app.services.inventory_v2_service import materialize_v2_runtime_inventory  # type: ignore[reportMissingImports]

    async with async_session() as session:
        materialized = await materialize_v2_runtime_inventory(
            session,
            UUID(inventory_response.json()["id"]),
            str(tmp_path),
        )

    assert materialized is not None
    runtime_path, _revision = materialized
    runtime_content = Path(runtime_path).read_text(encoding="utf-8")
    assert "ansible_become=true" in runtime_content
    assert "ansible_become_user=root" in runtime_content
    assert "ansible_password=login-secret" in runtime_content
    assert "ansible_become_password=become-secret" in runtime_content


async def test_v2_runtime_inventory_uses_new_embedded_become_after_legacy_login_change(async_client, tmp_path):
    suffix = uuid4().hex
    old_login_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"legacy-login-before-change-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "old-login-secret",
        },
    )
    assert old_login_response.status_code == 201
    old_login_ref = old_login_response.json()["ref"]

    new_login_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"embedded-login-after-change-{suffix}",
            "credential_type": "ssh_password",
            "username": "deploy",
            "secret": "new-login-secret",
            "become_username": "admin",
            "become_secret": "new-become-secret",
        },
    )
    assert new_login_response.status_code == 201
    new_login_ref = new_login_response.json()["ref"]

    from app.database import async_session  # type: ignore[reportMissingImports]
    from app.models.managed_inventory_v2 import GlobalCredential  # type: ignore[reportMissingImports]
    from app.services.credential_service import encrypt_secret  # type: ignore[reportMissingImports]

    legacy_become_ref = f"legacy-become-{suffix}"
    legacy_secret, legacy_nonce = encrypt_secret("legacy-become-secret")
    async with async_session() as session:
        session.add(
            GlobalCredential(
                ref=legacy_become_ref,
                name=f"legacy-become-before-change-{suffix}",
                credential_type="become_password",
                username="root",
                encrypted_secret=legacy_secret,
                nonce=legacy_nonce,
            )
        )
        await session.commit()

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"legacy-login-change-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-legacy-change",
                            "address": "10.10.3.3",
                            "login_credential_ref": old_login_ref,
                            "become_enabled": True,
                            "become_user": "root",
                            "become_credential_ref": legacy_become_ref,
                        }
                    ],
                }
            ],
        },
    )
    assert inventory_response.status_code == 201
    inventory_id = inventory_response.json()["id"]

    update_response = await async_client.put(
        f"/api/inventories/{inventory_id}",
        json={
            "name": f"legacy-login-change-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-legacy-change",
                            "address": "10.10.3.3",
                            "login_credential_ref": new_login_ref,
                            "become_enabled": True,
                        }
                    ],
                }
            ],
        },
    )
    assert update_response.status_code == 200
    updated_payload = update_response.json()
    assert updated_payload["hosts"][0]["login_credential_ref"] == new_login_ref
    assert updated_payload["hosts"][0]["become_credential_ref"] is None
    assert "ansible_become_user=admin" in updated_payload["rendered_content"]

    async with async_session() as session:
        from app.services.inventory_v2_service import materialize_v2_runtime_inventory  # type: ignore[reportMissingImports]

        materialized = await materialize_v2_runtime_inventory(session, UUID(inventory_id), str(tmp_path))

    assert materialized is not None
    runtime_path, _revision = materialized
    runtime_content = Path(runtime_path).read_text(encoding="utf-8")
    assert "ansible_become_user=admin" in runtime_content
    assert "ansible_password=new-login-secret" in runtime_content
    assert "ansible_become_password=new-become-secret" in runtime_content
    assert "legacy-become-secret" not in runtime_content


async def test_v2_inventory_rejects_become_without_embedded_become_account(async_client):
    suffix = uuid4().hex
    credential_response = await async_client.post(
        "/api/credentials",
        json={
            "name": f"shared-login-without-become-{suffix}",
            "credential_type": "ssh_password",
            "username": "ops",
            "secret": "login-secret",
        },
    )
    assert credential_response.status_code == 201
    credential_ref = credential_response.json()["ref"]

    response = await async_client.post(
        "/api/inventories",
        json={
            "name": f"shared-login-no-become-inventory-{suffix}",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {
                            "name": "web-no-become",
                            "address": "10.10.4.1",
                            "login_credential_ref": credential_ref,
                            "become_enabled": True,
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 400
    assert "become account information" in response.json()["detail"]


async def test_list_managed_inventories_returns_project_file_list(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod_windows.ini").write_text("[prod]\nweb-01\n", encoding="utf-8")
    (inventory_dir / "qa_windows.ini").write_text("[qa]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod_windows.ini", "qa_windows.ini"])


async def test_list_managed_inventories_ignores_directory_entries(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod_windows.ini").write_text("[prod]\nweb-01\n", encoding="utf-8")
    (inventory_dir / "group_vars").mkdir()

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod_windows.ini"])


async def test_list_managed_inventories_returns_files_sorted_by_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "z_windows.ini").write_text("[z]\n")
    (inventory_dir / "a_windows.ini").write_text("[a]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["a_windows.ini", "z_windows.ini"])


async def test_list_managed_inventories_includes_hidden_files_when_they_are_regular_files(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / ".secret.ini").write_text("[hidden]\n")
    (inventory_dir / "visible.ini").write_text("[visible]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), [".secret.ini", "visible.ini"])


async def test_list_managed_inventories_includes_symlinked_regular_files(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    target_file = inventory_dir / "real.ini"
    target_file.write_text("[real]\n")
    (inventory_dir / "linked.ini").symlink_to(target_file)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["linked.ini", "real.ini"])


async def test_list_managed_inventories_ignores_broken_symlinks(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "visible.ini").write_text("[visible]\n")
    (inventory_dir / "broken.ini").symlink_to(inventory_dir / "missing.ini")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["visible.ini"])


async def test_list_managed_inventories_returns_only_top_level_files(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    nested_dir = inventory_dir / "nested"
    nested_dir.mkdir(parents=True)
    (inventory_dir / "top.ini").write_text("[top]\n")
    (nested_dir / "nested.ini").write_text("[nested]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["top.ini"])


async def test_list_managed_inventories_includes_top_level_regular_files_regardless_of_extension(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "hosts.txt").write_text("host-a\n")
    (inventory_dir / "prod.ini").write_text("[prod]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["hosts.txt", "prod.ini"])


async def test_list_managed_inventories_sorts_mixed_case_filenames_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "b.ini").write_text("[b]\n")
    (inventory_dir / "A.ini").write_text("[A]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["A.ini", "b.ini"])


async def test_list_managed_inventories_sorts_numeric_like_filenames_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "2.ini").write_text("[two]\n")
    (inventory_dir / "10.ini").write_text("[ten]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["10.ini", "2.ini"])


async def test_list_managed_inventories_includes_top_level_regular_files_with_spaces_in_name(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod windows.ini").write_text("[prod]\n")
    (inventory_dir / "qa.ini").write_text("[qa]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod windows.ini", "qa.ini"])


async def test_list_managed_inventories_sorts_hyphen_and_underscore_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod_config.ini").write_text("[underscore]\n")
    (inventory_dir / "prod-config.ini").write_text("[hyphen]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod-config.ini", "prod_config.ini"])


async def test_list_managed_inventories_sorts_punctuation_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "!prod.ini").write_text("[punctuation]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["!prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_unicode_filenames_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "가나다.ini").write_text("[korean]\n")
    (inventory_dir / "alpha.ini").write_text("[alpha]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["alpha.ini", "가나다.ini"])


async def test_list_managed_inventories_includes_multiple_dots_filenames_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.backup.ini").write_text("[backup]\n")
    (inventory_dir / "prod.ini").write_text("[prod]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod.backup.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_at_sign_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "@prod.ini").write_text("[at]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["@prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_hash_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "#prod.ini").write_text("[hash]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["#prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_tilde_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "~prod.ini").write_text("[tilde]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["prod.ini", "~prod.ini"])


async def test_list_managed_inventories_sorts_plus_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "+prod.ini").write_text("[plus]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["+prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_dollar_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "$prod.ini").write_text("[dollar]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["$prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_caret_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "^prod.ini").write_text("[caret]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["^prod.ini", "prod.ini"])


async def test_list_managed_inventories_sorts_percent_prefixed_names_by_current_string_order(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod.ini").write_text("[prod]\n")
    (inventory_dir / "%prod.ini").write_text("[percent]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    _assert_unknown_status_managed_inventory_list(response.json(), ["%prod.ini", "prod.ini"])


async def test_list_managed_inventories_returns_empty_collection_for_empty_inventory_dir(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_managed_inventories_returns_empty_collection_when_inventory_dir_is_missing(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    project_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/managed-inventories")

    assert response.status_code == 200
    assert response.json() == []


async def test_get_managed_inventory_returns_existing_file_contract(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod_windows.ini").write_text("[prod]\nweb-01\n", encoding="utf-8")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "prod_windows.ini",
        "path": "prod_windows.ini",
        "status_summary": "unknown",
        "content": "[prod]\nweb-01\n",
        "groups": [],
    }


async def test_get_managed_inventory_returns_404_for_missing_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/missing.ini",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Managed inventory 'missing.ini' not found"}


async def test_get_managed_inventory_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/not-a-real-project/managed-inventories/prod_windows.ini",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_get_managed_inventory_returns_400_for_invalid_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/..\\prod_windows.ini",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_list_managed_inventories_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/not-a-real-project/managed-inventories")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_create_managed_inventory_returns_created_file_contract(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "prod_windows.ini"},
    )

    assert response.status_code == 201
    assert response.json() == {
        "name": "prod_windows.ini",
        "path": "prod_windows.ini",
    }
    assert (inventory_dir / "prod_windows.ini").read_text(encoding="utf-8") == ""


async def test_create_managed_inventory_writes_supplied_content(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    content = "[prod]\nweb-01 ansible_host=192.0.2.20\n"
    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "prod_windows.ini", "content": content},
    )

    assert response.status_code == 201
    assert response.json() == {
        "name": "prod_windows.ini",
        "path": "prod_windows.ini",
    }
    assert (inventory_dir / "prod_windows.ini").read_text(encoding="utf-8") == content


async def test_create_managed_inventory_accepts_minimal_group_first_payload(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {}
                        }
                    ]
                }
            ]
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "name": "grouped_windows.ini",
        "path": "grouped_windows.ini",
    }
    assert (inventory_dir / "grouped_windows.ini").read_text(encoding="utf-8") == (
        "[Windows]\n"
        "win-host-01 ansible_host=192.0.2.203 ansible_connection=winrm ansible_port=5986\n"
    )


async def test_create_then_get_managed_inventory_returns_structured_detail_with_unknown_status_and_nullable_credential_refs(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": None,
                            "ansibleharness_become_credential_ref": None,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )

    assert create_response.status_code == 201

    detail_response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini",
    )

    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "name": "grouped_windows.ini",
        "path": "grouped_windows.ini",
        "status_summary": "unknown",
        "content": "[Windows]\nwin-host-01 ansible_host=192.0.2.203 ansible_connection=winrm ansible_port=5986\n",
        "groups": [
            {
                "name": "Windows",
                "hosts": [
                    {
                        "name": "win-host-01",
                        "address": "192.0.2.203",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": None,
                        "ansibleharness_become_credential_ref": None,
                        "host_vars": {},
                        "connection_status": _unknown_connection_status(),
                    }
                ],
            }
        ],
    }


async def test_create_managed_inventory_with_project_credential_refs_then_get_returns_same_opaque_refs(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    login_credential_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "login-secret",
        },
    )
    assert login_credential_response.status_code == 201
    login_ref = login_credential_response.json()["ref"]

    become_credential_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-become",
            "credential_type": "become_password",
            "username": "Administrator",
            "secret": "become-secret",
        },
    )
    assert become_credential_response.status_code == 201
    become_ref = become_credential_response.json()["ref"]

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": login_ref,
                            "ansibleharness_become_credential_ref": become_ref,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )

    assert create_response.status_code == 201

    detail_response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini",
    )

    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "name": "grouped_windows.ini",
        "path": "grouped_windows.ini",
        "status_summary": "unknown",
        "content": "[Windows]\nwin-host-01 ansible_host=192.0.2.203 ansible_connection=winrm ansible_port=5986\n",
        "groups": [
            {
                "name": "Windows",
                "hosts": [
                    {
                        "name": "win-host-01",
                        "address": "192.0.2.203",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": login_ref,
                        "ansibleharness_become_credential_ref": become_ref,
                        "host_vars": {},
                        "connection_status": _unknown_connection_status(),
                    }
                ],
            }
        ],
    }


async def test_get_managed_inventory_backfills_unknown_host_connection_status_for_legacy_metadata(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "grouped_windows.ini").write_text("[Windows]\nwin-host-01\n", encoding="utf-8")

    metadata_dir = project_dir / ".managed_inventory_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "grouped_windows.ini.json").write_text(
        """
{
  "groups": [
    {
      "name": "Windows",
      "hosts": [
        {
          "name": "win-host-01",
          "address": "192.0.2.203",
          "connection_type": "winrm",
          "port": 5986,
          "ansibleharness_login_credential_ref": null,
          "ansibleharness_become_credential_ref": null,
          "host_vars": {}
        }
      ]
    }
  ]
}
        """.strip(),
        encoding="utf-8",
    )

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini",
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "grouped_windows.ini",
        "path": "grouped_windows.ini",
        "status_summary": "unknown",
        "content": "[Windows]\nwin-host-01\n",
        "groups": [
            {
                "name": "Windows",
                "hosts": [
                    {
                        "name": "win-host-01",
                        "address": "192.0.2.203",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": None,
                        "ansibleharness_become_credential_ref": None,
                        "host_vars": {},
                        "connection_status": _unknown_connection_status(),
                    }
                ],
            }
        ],
    }


async def test_create_managed_inventory_rejects_client_supplied_host_connection_status(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": None,
                            "ansibleharness_become_credential_ref": None,
                            "host_vars": {},
                            "connection_status": {
                                "status": "failed",
                                "checked_at": None,
                                "failure_code": "AUTH_FAILED",
                                "failure_message": "should not be accepted",
                            },
                        }
                    ],
                }
            ],
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "groups", 0, "hosts", 0, "connection_status"] for error in payload["detail"])
    assert not (inventory_dir / "grouped_windows.ini").exists()


async def test_trigger_managed_inventory_host_connection_test_returns_canonical_success_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_connection_test(project_name, filename, group_name, host_name, host):
        assert project_name == "sample_windows"
        assert filename == "grouped_windows.ini"
        assert group_name == "Windows"
        assert host_name == "win-host-01"
        assert host.connection_type == "winrm"
        return {
            "project_name": project_name,
            "inventory_filename": filename,
            "group_name": group_name,
            "host_name": host_name,
            "status": "success",
            "checked_at": "2026-05-08T08:00:00Z",
            "failure_code": None,
            "failure_message": None,
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_host_connection_test", _fake_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Windows/hosts/win-host-01/connection-test",
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_name": "sample_windows",
        "inventory_filename": "grouped_windows.ini",
        "group_name": "Windows",
        "host_name": "win-host-01",
        "status": "success",
        "checked_at": "2026-05-08T08:00:00Z",
        "failure_code": None,
        "failure_message": None,
    }


async def test_trigger_managed_inventory_host_connection_test_returns_standardized_failure_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_connection_test(project_name, filename, group_name, host_name, host):
        return {
            "project_name": project_name,
            "inventory_filename": filename,
            "group_name": group_name,
            "host_name": host_name,
            "status": "failed",
            "checked_at": "2026-05-08T08:05:00Z",
            "failure_code": "AUTH_FAILED",
            "failure_message": "Invalid password",
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_host_connection_test", _fake_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Windows/hosts/win-host-01/connection-test",
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_name": "sample_windows",
        "inventory_filename": "grouped_windows.ini",
        "group_name": "Windows",
        "host_name": "win-host-01",
        "status": "failed",
        "checked_at": "2026-05-08T08:05:00Z",
        "failure_code": "AUTH_FAILED",
        "failure_message": "Invalid password",
    }


async def test_trigger_managed_inventory_host_connection_test_returns_404_for_missing_host_in_group(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _should_not_run(*args, **kwargs):
        raise AssertionError("connection test runner should not be called for missing host")

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_host_connection_test", _should_not_run)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Windows/hosts/not-a-real-host/connection-test",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Host 'not-a-real-host' not found in group 'Windows' for managed inventory 'grouped_windows.ini'"
    }


async def test_trigger_managed_inventory_group_connection_test_returns_canonical_bulk_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        },
                        {
                            "name": "win-host-02",
                            "address": "192.0.2.204",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        },
                    ],
                },
                {
                    "name": "Linux",
                    "hosts": [
                        {
                            "name": "linux-host-01",
                            "address": "192.0.2.10",
                            "connection_type": "ssh",
                            "port": 22,
                            "host_vars": {},
                        }
                    ],
                },
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_group_connection_test(project_name, filename, group_name, group):
        assert project_name == "sample_windows"
        assert filename == "grouped_windows.ini"
        assert group_name == "Windows"
        assert group.name == "Windows"
        assert [host.name for host in group.hosts] == ["win-host-01", "win-host-02"]
        return {
            "target": {
                "scope": "group",
                "project_name": project_name,
                "inventory_filename": filename,
                "group_name": group_name,
            },
            "summary": {
                "total_hosts": 2,
                "success": 1,
                "failed": 1,
                "unknown": 0,
                "stale": 0,
            },
            "results": [
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": group_name,
                    "host_name": "win-host-01",
                    "status": "success",
                    "checked_at": "2026-05-08T10:00:00Z",
                    "failure_code": None,
                    "failure_message": None,
                },
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": group_name,
                    "host_name": "win-host-02",
                    "status": "failed",
                    "checked_at": "2026-05-08T10:00:01Z",
                    "failure_code": "AUTH_FAILED",
                    "failure_message": "Invalid password",
                },
            ],
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_group_connection_test", _fake_group_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Windows/connection-test",
    )

    assert response.status_code == 200
    assert response.json() == {
        "target": {
            "scope": "group",
            "project_name": "sample_windows",
            "inventory_filename": "grouped_windows.ini",
            "group_name": "Windows",
        },
        "summary": {
            "total_hosts": 2,
            "success": 1,
            "failed": 1,
            "unknown": 0,
            "stale": 0,
        },
        "results": [
            {
                "project_name": "sample_windows",
                "inventory_filename": "grouped_windows.ini",
                "group_name": "Windows",
                "host_name": "win-host-01",
                "status": "success",
                "checked_at": "2026-05-08T10:00:00Z",
                "failure_code": None,
                "failure_message": None,
            },
            {
                "project_name": "sample_windows",
                "inventory_filename": "grouped_windows.ini",
                "group_name": "Windows",
                "host_name": "win-host-02",
                "status": "failed",
                "checked_at": "2026-05-08T10:00:01Z",
                "failure_code": "AUTH_FAILED",
                "failure_message": "Invalid password",
            },
        ],
    }


async def test_trigger_managed_inventory_group_connection_test_preserves_standardized_failure_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_group_connection_test(project_name, filename, group_name, group):
        return {
            "target": {
                "scope": "group",
                "project_name": project_name,
                "inventory_filename": filename,
                "group_name": group_name,
            },
            "summary": {
                "total_hosts": 1,
                "success": 0,
                "failed": 1,
                "unknown": 0,
                "stale": 0,
            },
            "results": [
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": group_name,
                    "host_name": "win-host-01",
                    "status": "failed",
                    "checked_at": "2026-05-08T10:05:00Z",
                    "failure_code": "AUTH_FAILED",
                    "failure_message": "Invalid password",
                }
            ],
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_group_connection_test", _fake_group_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Windows/connection-test",
    )

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "project_name": "sample_windows",
            "inventory_filename": "grouped_windows.ini",
            "group_name": "Windows",
            "host_name": "win-host-01",
            "status": "failed",
            "checked_at": "2026-05-08T10:05:00Z",
            "failure_code": "AUTH_FAILED",
            "failure_message": "Invalid password",
        }
    ]


async def test_trigger_managed_inventory_group_connection_test_returns_404_for_missing_group(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _should_not_run(*args, **kwargs):
        raise AssertionError("group connection test runner should not be called for missing group")

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_group_connection_test", _should_not_run)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/groups/Linux/connection-test",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Managed inventory group 'Linux' not found in 'grouped_windows.ini'"
    }


async def test_trigger_managed_inventory_inventory_connection_test_returns_canonical_bulk_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        },
                        {
                            "name": "win-host-02",
                            "address": "192.0.2.204",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        },
                    ],
                },
                {
                    "name": "Linux",
                    "hosts": [
                        {
                            "name": "linux-host-01",
                            "address": "192.0.2.10",
                            "connection_type": "ssh",
                            "port": 22,
                            "host_vars": {},
                        }
                    ],
                },
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_inventory_connection_test(project_name, filename, groups):
        assert project_name == "sample_windows"
        assert filename == "grouped_windows.ini"
        assert [group.name for group in groups] == ["Windows", "Linux"]
        assert [(group.name, [host.name for host in group.hosts]) for group in groups] == [
            ("Windows", ["win-host-01", "win-host-02"]),
            ("Linux", ["linux-host-01"]),
        ]
        return {
            "target": {
                "scope": "inventory",
                "project_name": project_name,
                "inventory_filename": filename,
                "group_name": None,
            },
            "summary": {
                "total_hosts": 3,
                "success": 1,
                "failed": 1,
                "unknown": 1,
                "stale": 0,
            },
            "results": [
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": "Windows",
                    "host_name": "win-host-01",
                    "status": "success",
                    "checked_at": "2026-05-08T11:00:00Z",
                    "failure_code": None,
                    "failure_message": None,
                },
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": "Windows",
                    "host_name": "win-host-02",
                    "status": "failed",
                    "checked_at": "2026-05-08T11:00:01Z",
                    "failure_code": "AUTH_FAILED",
                    "failure_message": "Invalid password",
                },
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": "Linux",
                    "host_name": "linux-host-01",
                    "status": "unknown",
                    "checked_at": None,
                    "failure_code": None,
                    "failure_message": None,
                },
            ],
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_inventory_connection_test", _fake_inventory_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/connection-test",
    )

    assert response.status_code == 200
    assert response.json() == {
        "target": {
            "scope": "inventory",
            "project_name": "sample_windows",
            "inventory_filename": "grouped_windows.ini",
            "group_name": None,
        },
        "summary": {
            "total_hosts": 3,
            "success": 1,
            "failed": 1,
            "unknown": 1,
            "stale": 0,
        },
        "results": [
            {
                "project_name": "sample_windows",
                "inventory_filename": "grouped_windows.ini",
                "group_name": "Windows",
                "host_name": "win-host-01",
                "status": "success",
                "checked_at": "2026-05-08T11:00:00Z",
                "failure_code": None,
                "failure_message": None,
            },
            {
                "project_name": "sample_windows",
                "inventory_filename": "grouped_windows.ini",
                "group_name": "Windows",
                "host_name": "win-host-02",
                "status": "failed",
                "checked_at": "2026-05-08T11:00:01Z",
                "failure_code": "AUTH_FAILED",
                "failure_message": "Invalid password",
            },
            {
                "project_name": "sample_windows",
                "inventory_filename": "grouped_windows.ini",
                "group_name": "Linux",
                "host_name": "linux-host-01",
                "status": "unknown",
                "checked_at": None,
                "failure_code": None,
                "failure_message": None,
            },
        ],
    }


async def test_trigger_managed_inventory_inventory_connection_test_preserves_standardized_failure_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )
    assert create_response.status_code == 201

    async def _fake_inventory_connection_test(project_name, filename, groups):
        return {
            "target": {
                "scope": "inventory",
                "project_name": project_name,
                "inventory_filename": filename,
                "group_name": None,
            },
            "summary": {
                "total_hosts": 1,
                "success": 0,
                "failed": 1,
                "unknown": 0,
                "stale": 0,
            },
            "results": [
                {
                    "project_name": project_name,
                    "inventory_filename": filename,
                    "group_name": "Windows",
                    "host_name": "win-host-01",
                    "status": "failed",
                    "checked_at": "2026-05-08T11:05:00Z",
                    "failure_code": "AUTH_FAILED",
                    "failure_message": "Invalid password",
                }
            ],
        }

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_inventory_connection_test", _fake_inventory_connection_test)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini/connection-test",
    )

    assert response.status_code == 200
    assert response.json()["results"] == [
        {
            "project_name": "sample_windows",
            "inventory_filename": "grouped_windows.ini",
            "group_name": "Windows",
            "host_name": "win-host-01",
            "status": "failed",
            "checked_at": "2026-05-08T11:05:00Z",
            "failure_code": "AUTH_FAILED",
            "failure_message": "Invalid password",
        }
    ]


async def test_trigger_managed_inventory_inventory_connection_test_returns_404_for_missing_inventory(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.api.project_managed_inventories as project_managed_inventories_api  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    async def _should_not_run(*args, **kwargs):
        raise AssertionError("inventory connection test runner should not be called for missing inventory")

    monkeypatch.setattr(project_managed_inventories_api, "_run_managed_inventory_inventory_connection_test", _should_not_run)

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories/not-a-real.ini/connection-test",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Managed inventory 'not-a-real.ini' not found"
    }


async def test_get_managed_inventory_returns_persisted_host_connection_status_fields(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "grouped_windows.ini").write_text("[Windows]\nwin-host-01\nwin-host-02\n", encoding="utf-8")

    metadata_dir = project_dir / ".managed_inventory_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "grouped_windows.ini.json").write_text(
        """
{
  "groups": [
    {
      "name": "Windows",
      "hosts": [
        {
          "name": "win-host-01",
          "address": "192.0.2.203",
          "connection_type": "winrm",
          "port": 5986,
          "ansibleharness_login_credential_ref": null,
          "ansibleharness_become_credential_ref": null,
          "host_vars": {},
          "connection_status": {
            "status": "failed",
            "checked_at": "2026-05-08T07:30:00+00:00",
            "failure_code": "AUTH_FAILED",
            "failure_message": "Access denied"
          }
        },
        {
          "name": "win-host-02",
          "address": "192.0.2.204",
          "connection_type": "winrm",
          "port": 5986,
          "ansibleharness_login_credential_ref": null,
          "ansibleharness_become_credential_ref": null,
          "host_vars": {},
          "connection_status": {
            "status": "stale",
            "checked_at": "2026-05-07T07:30:00+00:00",
            "failure_code": null,
            "failure_message": null
          }
        }
      ]
    }
  ]
}
        """.strip(),
        encoding="utf-8",
    )

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/grouped_windows.ini",
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "grouped_windows.ini",
        "path": "grouped_windows.ini",
        "status_summary": "unknown",
        "content": "[Windows]\nwin-host-01\nwin-host-02\n",
        "groups": [
            {
                "name": "Windows",
                "hosts": [
                    {
                        "name": "win-host-01",
                        "address": "192.0.2.203",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": None,
                        "ansibleharness_become_credential_ref": None,
                        "host_vars": {},
                        "connection_status": {
                            "status": "failed",
                            "checked_at": "2026-05-08T07:30:00Z",
                            "failure_code": "AUTH_FAILED",
                            "failure_message": "Access denied",
                        },
                    },
                    {
                        "name": "win-host-02",
                        "address": "192.0.2.204",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": None,
                        "ansibleharness_become_credential_ref": None,
                        "host_vars": {},
                        "connection_status": {
                            "status": "stale",
                            "checked_at": "2026-05-07T07:30:00Z",
                            "failure_code": None,
                            "failure_message": None,
                        },
                    },
                ],
            }
        ],
    }


async def test_create_managed_inventory_rejects_client_supplied_status_summary(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "status_summary": "failed",
            "groups": [],
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "status_summary"] for error in payload["detail"])
    assert not (inventory_dir / "grouped_windows.ini").exists()


async def test_create_managed_inventory_rejects_credential_ref_from_different_project(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    windows_project_dir = ansible_root / "projects" / "sample_windows"
    linux_project_dir = ansible_root / "projects" / "sample_linux"
    (windows_project_dir / "inventory").mkdir(parents=True)
    (linux_project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    foreign_credential_response = await async_client.post(
        "/api/projects/sample_linux/credentials",
        json={
            "name": "linux-admin",
            "credential_type": "ssh_password",
            "username": "root",
            "secret": "linux-secret",
        },
    )
    assert foreign_credential_response.status_code == 201
    foreign_ref = foreign_credential_response.json()["ref"]

    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": foreign_ref,
                            "ansibleharness_become_credential_ref": None,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )

    assert create_response.status_code == 400
    assert create_response.json() == {
        "detail": f"Credential ref '{foreign_ref}' does not belong to project 'sample_windows'"
    }
    assert not ((windows_project_dir / "inventory") / "grouped_windows.ini").exists()


async def test_create_managed_inventory_rejects_nonexistent_same_project_credential_ref(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    missing_ref = "cred_missing_same_project_ref"
    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": missing_ref,
                            "ansibleharness_become_credential_ref": None,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )

    assert create_response.status_code == 400
    assert create_response.json() == {
        "detail": f"Credential ref '{missing_ref}' does not belong to project 'sample_windows'"
    }
    assert not ((project_dir / "inventory") / "grouped_windows.ini").exists()


async def test_create_managed_inventory_rejects_nonexistent_same_project_become_credential_ref(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    missing_ref = "cred_missing_same_project_become_ref"
    create_response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={
            "filename": "grouped_windows.ini",
            "groups": [
                {
                    "name": "Windows",
                    "hosts": [
                        {
                            "name": "win-host-01",
                            "address": "192.0.2.203",
                            "connection_type": "winrm",
                            "port": 5986,
                            "ansibleharness_login_credential_ref": None,
                            "ansibleharness_become_credential_ref": missing_ref,
                            "host_vars": {},
                        }
                    ],
                }
            ],
        },
    )

    assert create_response.status_code == 400
    assert create_response.json() == {
        "detail": f"Credential ref '{missing_ref}' does not belong to project 'sample_windows'"
    }
    assert not ((project_dir / "inventory") / "grouped_windows.ini").exists()


async def test_create_managed_inventory_returns_409_for_duplicate_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    (inventory_dir / "prod_windows.ini").write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "prod_windows.ini"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Managed inventory 'prod_windows.ini' already exists"}


async def test_create_managed_inventory_returns_400_for_invalid_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "../prod_windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_create_managed_inventory_returns_400_for_backslash_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "prod\\windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_create_managed_inventory_returns_400_for_empty_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": ""},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_create_managed_inventory_returns_400_for_dot_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": "."},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_create_managed_inventory_returns_400_for_dotdot_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/managed-inventories",
        json={"filename": ".."},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_create_managed_inventory_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/not-a-real-project/managed-inventories",
        json={"filename": "prod_windows.ini"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_create_project_credential_returns_non_secret_summary_with_opaque_ref(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "windows-local-admin"
    assert payload["credential_type"] == "winrm_password"
    assert isinstance(payload["ref"], str)
    assert payload["ref"]
    assert "secret" not in payload
    assert "username" not in payload


async def test_create_then_list_project_credentials_returns_non_secret_summaries_only(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert create_response.status_code == 201
    created_payload = create_response.json()

    list_response = await async_client.get("/api/projects/sample_windows/credentials")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "ref": created_payload["ref"],
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
        }
    ]

    metadata_payload = ((project_dir / ".credential_metadata") / "credentials.json").read_text(encoding="utf-8")
    assert "not-a-real-secret" not in metadata_payload
    assert "Administrator" not in metadata_payload


async def test_create_two_project_credentials_then_list_returns_non_secret_summaries_in_creation_order(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    first_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )
    second_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "linux-deploy-user",
            "credential_type": "ssh_password",
            "username": "svc_runner_account",
            "secret": "also-not-real",
        },
    )

    assert first_create_response.status_code == 201
    assert second_create_response.status_code == 201
    first_payload = first_create_response.json()
    second_payload = second_create_response.json()

    list_response = await async_client.get("/api/projects/sample_windows/credentials")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "ref": first_payload["ref"],
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
        },
        {
            "ref": second_payload["ref"],
            "name": "linux-deploy-user",
            "credential_type": "ssh_password",
        },
    ]

    metadata_payload = ((project_dir / ".credential_metadata") / "credentials.json").read_text(encoding="utf-8")
    assert "not-a-real-secret" not in metadata_payload
    assert "also-not-real" not in metadata_payload
    assert "Administrator" not in metadata_payload
    assert "svc_runner_account" not in metadata_payload


async def test_create_two_project_credentials_with_same_name_returns_distinct_refs_and_lists_both(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    first_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "shared-display-name",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )
    second_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "shared-display-name",
            "credential_type": "ssh_password",
            "username": "svc_runner_account",
            "secret": "also-not-real",
        },
    )

    assert first_create_response.status_code == 201
    assert second_create_response.status_code == 201
    first_payload = first_create_response.json()
    second_payload = second_create_response.json()
    assert first_payload["ref"] != second_payload["ref"]

    list_response = await async_client.get("/api/projects/sample_windows/credentials")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "ref": first_payload["ref"],
            "name": "shared-display-name",
            "credential_type": "winrm_password",
        },
        {
            "ref": second_payload["ref"],
            "name": "shared-display-name",
            "credential_type": "ssh_password",
        },
    ]


async def test_create_two_project_credentials_with_same_name_and_type_returns_distinct_refs_and_lists_both(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    first_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "shared-display-name",
            "credential_type": "ssh_password",
            "username": "svc_runner_account",
            "secret": "not-a-real-secret",
        },
    )
    second_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "shared-display-name",
            "credential_type": "ssh_password",
            "username": "svc_runner_account_two",
            "secret": "also-not-real",
        },
    )

    assert first_create_response.status_code == 201
    assert second_create_response.status_code == 201
    first_payload = first_create_response.json()
    second_payload = second_create_response.json()
    assert first_payload["ref"] != second_payload["ref"]

    list_response = await async_client.get("/api/projects/sample_windows/credentials")

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "ref": first_payload["ref"],
            "name": "shared-display-name",
            "credential_type": "ssh_password",
        },
        {
            "ref": second_payload["ref"],
            "name": "shared-display-name",
            "credential_type": "ssh_password",
        },
    ]


async def test_create_two_project_credentials_persists_summary_only_store_shape(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import json
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    first_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )
    second_create_response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "linux-deploy-user",
            "credential_type": "ssh_password",
            "username": "svc_runner_account",
            "secret": "also-not-real",
        },
    )

    assert first_create_response.status_code == 201
    assert second_create_response.status_code == 201
    first_payload = first_create_response.json()
    second_payload = second_create_response.json()

    store_payload = json.loads(((project_dir / ".credential_metadata") / "credentials.json").read_text(encoding="utf-8"))

    assert store_payload == {
        "credentials": [
            {
                "ref": first_payload["ref"],
                "name": "windows-local-admin",
                "credential_type": "winrm_password",
            },
            {
                "ref": second_payload["ref"],
                "name": "linux-deploy-user",
                "credential_type": "ssh_password",
            },
        ]
    }


async def test_create_project_credential_rejects_unsupported_phase1_credential_type_without_writing_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "kerberos_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "credential_type"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_list_project_credentials_returns_empty_list_when_store_does_not_exist(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/credentials")

    assert response.status_code == 200
    assert response.json() == []
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_list_project_credentials_returns_empty_list_when_store_has_no_credentials_key(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)
    metadata_dir = project_dir / ".credential_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "credentials.json").write_text('{"unexpected": []}', encoding="utf-8")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/credentials")

    assert response.status_code == 200
    assert response.json() == []


async def test_list_project_credentials_returns_500_when_store_contains_malformed_summary_item(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)
    metadata_dir = project_dir / ".credential_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "credentials.json").write_text(
        '{"credentials": [{"name": "broken-item", "credential_type": "ssh_password"}]}',
        encoding="utf-8",
    )

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/credentials")

    assert response.status_code == 500
    assert response.json() == {"detail": "Credential store is malformed"}


async def test_list_project_credentials_returns_500_when_store_contains_invalid_json(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)
    metadata_dir = project_dir / ".credential_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "credentials.json").write_text('{"credentials": [', encoding="utf-8")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/credentials")

    assert response.status_code == 500
    assert response.json() == {"detail": "Credential store is malformed"}


async def test_list_project_credentials_returns_500_when_store_top_level_is_not_an_object(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)
    metadata_dir = project_dir / ".credential_metadata"
    metadata_dir.mkdir(parents=True)
    (metadata_dir / "credentials.json").write_text('["credentials"]', encoding="utf-8")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/sample_windows/credentials")

    assert response.status_code == 500
    assert response.json() == {"detail": "Credential store is malformed"}


async def test_list_project_credentials_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.get("/api/projects/not-a-real-project/credentials")

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_create_project_credential_returns_422_when_secret_is_missing_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "secret"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_username_is_missing_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "username"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_name_is_missing_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "name"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_credential_type_is_missing_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "credential_type"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_name_is_empty_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "name"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_username_is_empty_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "",
            "secret": "not-a-real-secret",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "username"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_create_project_credential_returns_422_when_secret_is_empty_and_does_not_write_store(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    (project_dir / "inventory").mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/projects/sample_windows/credentials",
        json={
            "name": "windows-local-admin",
            "credential_type": "winrm_password",
            "username": "Administrator",
            "secret": "",
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert any(error["loc"] == ["body", "secret"] for error in payload["detail"])
    assert not ((project_dir / ".credential_metadata") / "credentials.json").exists()


async def test_delete_managed_inventory_returns_204_and_removes_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    inventory_file = inventory_dir / "prod_windows.ini"
    inventory_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
    )

    assert response.status_code == 204
    assert not inventory_file.exists()


async def test_delete_managed_inventory_removes_persisted_host_connection_status_sidecar(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)
    inventory_file = inventory_dir / "prod_windows.ini"
    inventory_file.write_text("[windows]\n", encoding="utf-8")

    metadata_dir = project_dir / ".managed_inventory_metadata"
    metadata_dir.mkdir(parents=True)
    metadata_path = metadata_dir / "prod_windows.ini.json"
    metadata_path.write_text(
        """
{
  "groups": [
    {
      "name": "Windows",
      "hosts": [
        {
          "name": "win-host-01",
          "address": "192.0.2.203",
          "connection_type": "winrm",
          "port": 5986,
          "ansibleharness_login_credential_ref": null,
          "ansibleharness_become_credential_ref": null,
          "host_vars": {},
          "connection_status": {
            "status": "failed",
            "checked_at": "2026-05-08T07:30:00+00:00",
            "failure_code": "AUTH_FAILED",
            "failure_message": "Access denied"
          }
        }
      ]
    }
  ]
}
        """.strip(),
        encoding="utf-8",
    )

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
    )

    assert response.status_code == 204
    assert not inventory_file.exists()
    assert not metadata_path.exists()


async def test_delete_managed_inventory_returns_404_for_missing_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/missing.ini",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Managed inventory 'missing.ini' not found"}


async def test_delete_managed_inventory_returns_400_for_invalid_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/..\\prod_windows.ini",
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_delete_managed_inventory_returns_405_for_dot_filename_due_to_routing(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/.",
    )

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


async def test_delete_managed_inventory_returns_405_for_dotdot_filename_due_to_routing(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/sample_windows/managed-inventories/..",
    )

    assert response.status_code == 404


async def test_delete_managed_inventory_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.delete(
        "/api/projects/not-a-real-project/managed-inventories/prod_windows.ini",
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_update_managed_inventory_renames_file_and_returns_updated_contract(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "renamed_windows.ini",
        "path": "renamed_windows.ini",
    }
    assert not source_file.exists()
    assert (inventory_dir / "renamed_windows.ini").exists()


async def test_update_managed_inventory_overwrites_content_and_clears_metadata(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[old]\nlegacy-host\n", encoding="utf-8")

    metadata_dir = project_dir / ".managed_inventory_metadata"
    metadata_dir.mkdir(parents=True)
    metadata_path = metadata_dir / "prod_windows.ini.json"
    metadata_path.write_text('{"groups": []}', encoding="utf-8")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    content = "[prod]\nweb-01 ansible_host=192.0.2.20\n"
    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "prod_windows.ini", "content": content},
    )

    assert response.status_code == 200
    assert response.json() == {
        "name": "prod_windows.ini",
        "path": "prod_windows.ini",
    }
    assert source_file.read_text(encoding="utf-8") == content
    assert not metadata_path.exists()


async def test_update_managed_inventory_rename_preserves_persisted_host_connection_status(
    async_client,
    ai_test_env,
    monkeypatch,
    tmp_path,
):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    inventory_dir = project_dir / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n", encoding="utf-8")

    metadata_dir = project_dir / ".managed_inventory_metadata"
    metadata_dir.mkdir(parents=True)
    source_metadata_path = metadata_dir / "prod_windows.ini.json"
    source_metadata_path.write_text(
        """
{
  "groups": [
    {
      "name": "Windows",
      "hosts": [
        {
          "name": "win-host-01",
          "address": "192.0.2.203",
          "connection_type": "winrm",
          "port": 5986,
          "ansibleharness_login_credential_ref": null,
          "ansibleharness_become_credential_ref": null,
          "host_vars": {},
          "connection_status": {
            "status": "success",
            "checked_at": "2026-05-08T07:30:00+00:00",
            "failure_code": null,
            "failure_message": null
          }
        }
      ]
    }
  ]
}
        """.strip(),
        encoding="utf-8",
    )

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 200
    assert not source_metadata_path.exists()

    detail_response = await async_client.get(
        "/api/projects/sample_windows/managed-inventories/renamed_windows.ini",
    )

    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "name": "renamed_windows.ini",
        "path": "renamed_windows.ini",
        "status_summary": "unknown",
        "content": "[windows]\n",
        "groups": [
            {
                "name": "Windows",
                "hosts": [
                    {
                        "name": "win-host-01",
                        "address": "192.0.2.203",
                        "connection_type": "winrm",
                        "port": 5986,
                        "ansibleharness_login_credential_ref": None,
                        "ansibleharness_become_credential_ref": None,
                        "host_vars": {},
                        "connection_status": {
                            "status": "success",
                            "checked_at": "2026-05-08T07:30:00Z",
                            "failure_code": None,
                            "failure_message": None,
                        },
                    }
                ],
            }
        ],
    }


async def test_update_managed_inventory_returns_404_for_missing_source_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/missing.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Managed inventory 'missing.ini' not found"}


async def test_update_managed_inventory_returns_400_for_invalid_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "../renamed_windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_409_for_duplicate_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    target_file = inventory_dir / "renamed_windows.ini"
    source_file.write_text("[prod]\n")
    target_file.write_text("[target]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Managed inventory 'renamed_windows.ini' already exists"}
    assert source_file.exists()
    assert target_file.exists()


async def test_update_managed_inventory_returns_400_for_invalid_source_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/..\\prod_windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_400_for_backslash_source_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod\\windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_405_for_dot_source_filename_due_to_routing(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/.",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed"}


async def test_update_managed_inventory_returns_404_for_dotdot_source_filename_due_to_routing(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/..",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 404


async def test_update_managed_inventory_returns_404_for_nonexistent_project(async_client, ai_test_env, monkeypatch):
    ansible_root = Path(__file__).resolve().parents[2] / "ansible"

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/not-a-real-project/managed-inventories/prod_windows.ini",
        json={"filename": "renamed_windows.ini"},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Project 'not-a-real-project' not found"}


async def test_update_managed_inventory_returns_400_for_empty_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": ""},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_400_for_dot_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "."},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_400_for_dotdot_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": ".."},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_400_for_backslash_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "renamed\\windows.ini"},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid managed inventory filename"}


async def test_update_managed_inventory_returns_409_for_same_source_and_target_filename(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    inventory_dir = ansible_root / "projects" / "sample_windows" / "inventory"
    inventory_dir.mkdir(parents=True)
    source_file = inventory_dir / "prod_windows.ini"
    source_file.write_text("[windows]\n")

    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.put(
        "/api/projects/sample_windows/managed-inventories/prod_windows.ini",
        json={"filename": "prod_windows.ini"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Managed inventory 'prod_windows.ini' already exists"}
    assert source_file.exists()


async def test_create_job_rejects_both_direct_inventory_and_inventory_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    playbook_dir = project_dir / "playbooks"
    inventory_dir = project_dir / "inventory"
    playbook_dir.mkdir(parents=True)
    inventory_dir.mkdir(parents=True)
    (playbook_dir / "site.yml").write_text("---\n- hosts: all\n", encoding="utf-8")
    (inventory_dir / "prod_windows.ini").write_text("[windows]\n", encoding="utf-8")

    import app.api.jobs as jobs_api
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    async def noop_execute_job(job_id):
        return None

    monkeypatch.setattr(jobs_api, "execute_job", noop_execute_job)
    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/jobs",
        json={
            "project": "sample_windows",
            "playbook": "site.yml",
            "inventory": "[windows]\n",
            "inventory_file": "prod_windows.ini",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Use either direct inventory content or inventory_file, not both"}


async def test_create_job_rejects_missing_inventory_file(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    playbook_dir = project_dir / "playbooks"
    inventory_dir = project_dir / "inventory"
    playbook_dir.mkdir(parents=True)
    inventory_dir.mkdir(parents=True)
    (playbook_dir / "site.yml").write_text("---\n- hosts: all\n", encoding="utf-8")

    import app.api.jobs as jobs_api
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    async def noop_execute_job(job_id):
        return None

    monkeypatch.setattr(jobs_api, "execute_job", noop_execute_job)
    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    response = await async_client.post(
        "/api/jobs",
        json={
            "project": "sample_windows",
            "playbook": "site.yml",
            "inventory_file": "missing.ini",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Inventory file 'missing.ini' not found in project 'sample_windows'"}


async def test_create_job_allows_no_inventory_source(async_client, ai_test_env, monkeypatch, tmp_path):
    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    playbook_dir = project_dir / "playbooks"
    playbook_dir.mkdir(parents=True)
    (playbook_dir / "site.yml").write_text("---\n- hosts: all\n", encoding="utf-8")

    import app.api.jobs as jobs_api
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    class FakeSession:
        def add(self, job):
            self.job = job

        async def flush(self):
            self.job.id = uuid4()
            self.job.created_at = datetime.now(timezone.utc)
            self.job.updated_at = self.job.created_at

        async def commit(self):
            return None

        async def refresh(self, job):
            return None

    async def noop_execute_job(job_id):
        return None

    async def override_get_db():
        yield FakeSession()

    monkeypatch.setattr(jobs_api, "execute_job", noop_execute_job)
    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    ai_test_env["main"].app.dependency_overrides[jobs_api.get_db] = override_get_db

    try:
        response = await async_client.post(
            "/api/jobs",
            json={
                "project": "sample_windows",
                "playbook": "site.yml",
            },
        )
    finally:
        ai_test_env["main"].app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["inventory"] is None
    assert response.json()["inventory_file"] is None
