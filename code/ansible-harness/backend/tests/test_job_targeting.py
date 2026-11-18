from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError


@pytest.fixture(autouse=True)
def _backend_cwd(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])


def test_job_create_validates_target_scope_fields() -> None:
    from app.schemas.job import JobCreate

    valid = JobCreate(project="sample", playbook="site.yml", target_scope="host", target_group_name="web", target_host_name="web-01")
    assert valid.target_scope == "host"
    assert valid.target_group_name == "web"
    assert valid.target_host_name == "web-01"

    with pytest.raises(ValidationError):
        JobCreate(project="sample", playbook="site.yml", target_scope="inventory", target_group_name="web")

    with pytest.raises(ValidationError):
        JobCreate(project="sample", playbook="site.yml", target_scope="group")

    with pytest.raises(ValidationError):
        JobCreate(project="sample", playbook="site.yml", target_scope="host")


def test_render_runtime_inventory_quotes_inline_values_with_spaces() -> None:
    from app.services.inventory_renderer import RenderGroup, RenderHost, render_runtime_inventory_with_become

    rendered = render_runtime_inventory_with_become(
        [
            RenderGroup(
                name="web",
                group_vars={"release_name": "Blue Green"},
                hosts=[
                    RenderHost(
                        name="web-01",
                        address="10.0.0.10",
                        connection_type="ssh",
                        port=22,
                        remote_user="rocky",
                        become_enabled=False,
                        become_user=None,
                        login_credential_ref=None,
                        become_credential_ref=None,
                        login_credential_type=None,
                        become_credential_type=None,
                        login_credential_username=None,
                        become_credential_username=None,
                        host_vars={"platform": "Rocky Linux 9.7"},
                    )
                ],
            )
        ],
        {},
        {},
    )

    host_line = next(line for line in rendered.splitlines() if line.startswith("web-01 "))
    tokens = shlex.split(host_line)

    assert 'platform="Rocky Linux 9.7"' in host_line
    assert "platform=Rocky Linux 9.7" in tokens
    assert all(index == 0 or "=" in token for index, token in enumerate(tokens))


async def test_create_job_persists_target_fields_and_validates_v2_scope(async_client, ai_test_env, monkeypatch) -> None:
    from app.api import jobs as jobs_api  # type: ignore[reportMissingImports]
    from app.database import async_session, init_db  # type: ignore[reportMissingImports]
    import app.services.ansible_service as ansible_service  # type: ignore[reportMissingImports]

    await init_db()

    ansible_root = Path(ai_test_env["kb_dir"]).parent / "ansible"
    project_dir = ansible_root / "projects" / "sample"
    playbook_dir = project_dir / "playbooks"
    playbook_dir.mkdir(parents=True, exist_ok=True)
    (playbook_dir / "site.yml").write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

    monkeypatch.setattr(ai_test_env["config"].settings, "ANSIBLE_DATA_DIR", str(ansible_root))
    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    async def fake_execute_job(_job_id):
        return None

    monkeypatch.setattr(jobs_api, "execute_job", fake_execute_job)

    inventory_response = await async_client.post(
        "/api/inventories",
        json={
            "name": "job-targeting-inventory",
            "groups": [
                {
                    "name": "web",
                    "hosts": [
                        {"name": "web-01", "address": "10.10.0.10"},
                        {"name": "web-02", "address": "10.10.0.11"},
                    ],
                },
                {
                    "name": "db",
                    "hosts": [
                        {"name": "db-01", "address": "10.10.0.20"},
                    ],
                },
                {
                    "name": "그룹#1",
                    "hosts": [
                        {"name": "한글-host", "address": "10.10.0.30"},
                    ],
                },
            ],
        },
    )
    assert inventory_response.status_code == 201
    inventory_id = inventory_response.json()["id"]

    create_response = await async_client.post(
        "/api/jobs",
        json={
            "project": "sample",
            "playbook": "site.yml",
            "managed_inventory_id": inventory_id,
            "target_scope": "host",
            "target_group_name": "web",
            "target_host_name": "web-01",
            "extra_vars": {"ticket": "OPS-100"},
        },
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["target_scope"] == "host"
    assert payload["target_group_name"] == "web"
    assert payload["target_host_name"] == "web-01"
    assert payload["managed_inventory_id"] == inventory_id

    detail_response = await async_client.get(f"/api/jobs/{payload['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["target_host_name"] == "web-01"

    unicode_group_response = await async_client.post(
        "/api/jobs",
        json={
            "project": "sample",
            "playbook": "site.yml",
            "managed_inventory_id": inventory_id,
            "target_scope": "group",
            "target_group_name": "그룹#1",
        },
    )

    assert unicode_group_response.status_code == 201
    unicode_group_payload = unicode_group_response.json()
    assert unicode_group_payload["target_scope"] == "group"
    assert unicode_group_payload["target_group_name"] == "그룹#1"

    from app.services.inventory_v2_service import materialize_v2_runtime_inventory

    async with async_session() as session:
        materialized = await materialize_v2_runtime_inventory(
            session,
            UUID(inventory_id),
            str(project_dir),
            target_scope="group",
            target_group_name="그룹#1",
        )

    assert materialized is not None
    runtime_path, _revision = materialized
    runtime_content = Path(runtime_path).read_text(encoding="utf-8")
    assert "[그룹#1]" in runtime_content
    assert "한글-host" in runtime_content
    assert "[web]" not in runtime_content
    assert "web-01" not in runtime_content

    invalid_response = await async_client.post(
        "/api/jobs",
        json={
            "project": "sample",
            "playbook": "site.yml",
            "managed_inventory_id": inventory_id,
            "target_scope": "group",
            "target_group_name": "missing-group",
        },
    )

    assert invalid_response.status_code == 400
    assert "Target group 'missing-group' not found" in invalid_response.json()["detail"]

    for task in [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]:
        if task.done():
            continue
        coro = task.get_coro()
        if coro is not None and getattr(coro, "__name__", None) == "fake_execute_job":
            await task
