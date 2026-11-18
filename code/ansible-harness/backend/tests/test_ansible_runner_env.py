from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


class _FinishedThread:
    def is_alive(self) -> bool:
        return False


def test_run_playbook_sync_sets_runner_envvars(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    from app.services import ansible_service

    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    playbook_dir = project_dir / "playbooks"
    playbook_dir.mkdir(parents=True)
    (playbook_dir / "ansible.yml").write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    captured: dict[str, object] = {}

    def fake_run_async(**kwargs):
        captured.update(kwargs)
        return _FinishedThread(), SimpleNamespace(
            status="successful",
            rc=0,
            stdout=None,
            artifact_dir=None,
        )

    monkeypatch.setitem(sys.modules, "ansible_runner", SimpleNamespace(run_async=fake_run_async))

    result = ansible_service._run_playbook_sync(
        job_id="job-1",
        project_name="sample_windows",
        playbook="ansible.yml",
    )

    assert result["status"] == "successful"
    assert captured["private_data_dir"] == str(project_dir)
    assert captured["playbook"] == "playbooks/ansible.yml"
    assert captured["envvars"] == {
        "ANSIBLE_COLLECTIONS_PATH": str(ansible_root),
        "ANSIBLE_LIBRARY": str(ansible_root / "modules"),
    }


def test_run_playbook_sync_passes_limit_for_host_scope(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    from app.services import ansible_service

    ansible_root = tmp_path / "ansible"
    project_dir = ansible_root / "projects" / "sample_windows"
    playbook_dir = project_dir / "playbooks"
    playbook_dir.mkdir(parents=True)
    (playbook_dir / "ansible.yml").write_text("---\n- hosts: all\n  tasks: []\n", encoding="utf-8")

    monkeypatch.setattr(ansible_service.settings, "ANSIBLE_DATA_DIR", str(ansible_root))

    captured: dict[str, object] = {}

    def fake_run_async(**kwargs):
        captured.update(kwargs)
        return _FinishedThread(), SimpleNamespace(
            status="successful",
            rc=0,
            stdout=None,
            artifact_dir=None,
        )

    monkeypatch.setitem(sys.modules, "ansible_runner", SimpleNamespace(run_async=fake_run_async))

    result = ansible_service._run_playbook_sync(
        job_id="job-limit-1",
        project_name="sample_windows",
        playbook="ansible.yml",
        target_scope="host",
        target_group_name="web",
        target_host_name="web-01",
    )

    assert result["status"] == "successful"
    assert captured["limit"] == "web:&web-01"
