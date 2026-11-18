from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ANSIBLE_ROOT = REPO_ROOT / "ansible"
PROJECTS_ROOT = ANSIBLE_ROOT / "projects"
CANONICAL_COLLECTIONS_ROOT = ANSIBLE_ROOT / "ansible_collections"
LEGACY_COLLECTIONS_ROOT = PROJECTS_ROOT / "custom_modules"

PROJECT_CFG_EXPECTATIONS = {
    "sample": "/ansible/projects/sample/roles",
    "register_handler": "/ansible/projects/register_handler/roles",
    "LSJ_PLAY_1": "/ansible/projects/LSJ_PLAY_1/roles",
}


def _read_cfg(project_name: str) -> str:
    return (PROJECTS_ROOT / project_name / "ansible.cfg").read_text(encoding="utf-8")


def test_custom_collection_lives_under_canonical_root() -> None:
    assert (CANONICAL_COLLECTIONS_ROOT / "fap" / "common").is_dir()
    assert (CANONICAL_COLLECTIONS_ROOT / "fap" / "custom").is_dir()
    assert not LEGACY_COLLECTIONS_ROOT.exists()


def test_project_ansible_cfgs_use_canonical_runtime_paths() -> None:
    for project_name, expected_roles_path in PROJECT_CFG_EXPECTATIONS.items():
        cfg = _read_cfg(project_name)

        assert "inventory = /ansible/inventory" in cfg
        assert "library = /ansible/modules" in cfg
        assert f"roles_path = {expected_roles_path}" in cfg
        assert "collections_paths = /ansible/ansible_collections" in cfg
        assert "/fap/ansible" not in cfg
        assert "/opt/ansible-harness/ansible" not in cfg
        assert "custom_modules" not in cfg
