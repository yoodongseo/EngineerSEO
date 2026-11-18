"""Ansible Runner service - handles playbook execution with multi-project and real-time log streaming."""

import asyncio
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models.job import Job

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)

# In-memory log buffers for live streaming
JOB_LOG_BUFFERS: dict[str, dict] = {}
_buffer_lock = threading.Lock()
_LIMIT_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")


def _init_log_buffer(job_id: str) -> None:
    with _buffer_lock:
        JOB_LOG_BUFFERS[str(job_id)] = {
            "lines": [],
            "finished": False,
            "status": "running",
            "rc": None,
        }


def _append_log(job_id: str, line: str) -> None:
    key = str(job_id)
    with _buffer_lock:
        if key in JOB_LOG_BUFFERS:
            JOB_LOG_BUFFERS[key]["lines"].append(line)


def _finish_log_buffer(job_id: str, status: str, rc: int | None) -> None:
    key = str(job_id)
    with _buffer_lock:
        if key in JOB_LOG_BUFFERS:
            JOB_LOG_BUFFERS[key]["finished"] = True
            JOB_LOG_BUFFERS[key]["status"] = status
            JOB_LOG_BUFFERS[key]["rc"] = rc


def get_live_log_snapshot(job_id: str, offset: int = 0) -> dict | None:
    key = str(job_id)
    with _buffer_lock:
        buf = JOB_LOG_BUFFERS.get(key)
        if buf is None:
            return None
        return {
            "lines": buf["lines"][offset:],
            "total": len(buf["lines"]),
            "finished": buf["finished"],
            "status": buf["status"],
            "rc": buf["rc"],
        }


def cleanup_log_buffer(job_id: str) -> None:
    key = str(job_id)
    with _buffer_lock:
        JOB_LOG_BUFFERS.pop(key, None)


def _normalize_limit_identifier(kind: str, value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if not _LIMIT_IDENTIFIER_PATTERN.fullmatch(normalized):
        raise ValueError(
            f"Unsafe {kind} name '{value}'. Only letters, numbers, dot, underscore, and hyphen are allowed for job targeting."
        )
    return normalized


def build_ansible_limit(
    target_scope: str | None,
    target_group_names: list[str] | None,
    target_host_names: list[str] | None,
) -> str | None:
    normalized_scope = (target_scope or "inventory").strip() or "inventory"
    if normalized_scope == "inventory":
        return None

    group_names = [_normalize_limit_identifier("group", g) for g in (target_group_names or [])]
    group_names = [g for g in group_names if g]
    
    host_names = [_normalize_limit_identifier("host", h) for h in (target_host_names or [])]
    host_names = [h for h in host_names if h]

    if normalized_scope == "group":
        if not group_names:
            raise ValueError("Group scope requires target_group_names")
        return ",".join(group_names)

    if normalized_scope == "host":
        if not host_names:
            raise ValueError("Host scope requires target_host_names")
        # If no groups are provided, just limit by hosts. 
        # If groups are provided, we should ideally intersect each group with each host? 
        # Actually ansible supports: group1:&host1,group2:&host2 ...
        # Or simpler: just list the hosts. Usually limiting by host is sufficient because host names are unique across the inventory.
        # But if the user selected groups, they want those hosts IN those groups.
        # To be safe and simple: just limit by host_names.
        if group_names:
            # group1:&host1,group1:&host2,group2:&host1...
            limits = []
            for g in group_names:
                for h in host_names:
                    limits.append(f"{g}:&{h}")
            return ",".join(limits)
        else:
            return ",".join(host_names)

    raise ValueError(f"Unsupported target scope '{target_scope}'")


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from a project vars file."""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load project vars files") from exc

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError(f"Project vars file must contain a mapping: {path}")

    return raw


def _load_project_extra_vars(private_data_dir: str) -> dict[str, Any]:
    """Load project-level vars that Ansible does not auto-load by convention."""
    project_dir = Path(private_data_dir)
    vars_dir = project_dir / "vars"
    loaded: dict[str, Any] = {}

    for candidate in (vars_dir / "vars.yml", vars_dir / "vars.yaml"):
        if candidate.exists() and candidate.is_file():
            loaded.update(_load_yaml_mapping(candidate))
            break

    return loaded


def _merge_extra_vars(
    private_data_dir: str,
    extra_vars: Optional[dict],
) -> dict[str, Any]:
    """Merge project vars with job-provided extra vars.

    Job/API extra vars intentionally win over project files so one-off launches can
    override defaults without editing files on disk.
    """
    merged = _load_project_extra_vars(private_data_dir)
    if extra_vars:
        merged.update(extra_vars)
    return merged


async def persist_live_stdout(job_id: uuid.UUID, stdout: str) -> None:
    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        job.stdout = stdout
        await session.commit()


# --- Project path helpers ---

def _get_projects_root() -> Path:
    """Return the root directory for all projects."""
    return Path(settings.ANSIBLE_DATA_DIR) / "projects"


def _get_project_dir(project_name: str) -> Path:
    """Return the private_data_dir for a specific project."""
    return _get_projects_root() / project_name


def _validate_project(project_name: str) -> Path:
    """Validate a project exists and return its path."""
    project_dir = _get_project_dir(project_name)
    if not project_dir.is_dir():
        raise ValueError(f"Project '{project_name}' not found")
    return project_dir


# --- Project/Playbook/Inventory listing ---

def get_projects() -> list[dict]:
    """List all available projects."""
    root = _get_projects_root()
    if not root.exists():
        return []

    projects = []
    for d in sorted(root.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            playbooks = get_playbooks(d.name)
            inventories = get_inventories(d.name)
            projects.append({
                "name": d.name,
                "playbook_count": len(playbooks),
                "inventory_count": len(inventories),
            })
    return projects


def get_playbooks(project_name: str) -> list[dict]:
    """List available playbooks for a project.
    Searches project/<project>/project/ for .yml/.yaml files recursively.
    """
    try:
        project_dir = _validate_project(project_name)
    except ValueError:
        return []

    # playbook_dir = project_dir / "project" 수정 함 
    playbook_dir = project_dir / "playbooks"
    if not playbook_dir.exists():
        return []

    playbooks = []
    for pattern in ("**/*.yml", "**/*.yaml"):
        for f in sorted(playbook_dir.glob(pattern)):
            if f.is_file() and not f.name.startswith("."):
                rel_path = str(f.relative_to(playbook_dir))
                # Skip roles internal files
                if "roles/" in rel_path and "/tasks/" in rel_path:
                    continue
                if "roles/" in rel_path and "/handlers/" in rel_path:
                    continue
                if "roles/" in rel_path and "/vars/" in rel_path:
                    continue
                if "roles/" in rel_path and "/defaults/" in rel_path:
                    continue
                if "roles/" in rel_path and "/meta/" in rel_path:
                    continue
                playbooks.append({
                    "name": f.name,
                    "path": rel_path,
                    "size": f.stat().st_size,
                })

    # Deduplicate (glob patterns may overlap)
    seen = set()
    unique = []
    for p in playbooks:
        if p["path"] not in seen:
            seen.add(p["path"])
            unique.append(p)
    return unique


def get_inventories(project_name: str) -> list[dict]:
    """List available inventory files for a project."""
    try:
        project_dir = _validate_project(project_name)
    except ValueError:
        return []

    inv_dir = project_dir / "inventory"
    if not inv_dir.exists():
        return []

    inventories = []
    for f in sorted(inv_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            inventories.append({
                "name": f.name,
                "path": str(f.relative_to(inv_dir)),
            })
    return inventories


# --- Playbook execution ---

def _run_playbook_sync(
    job_id: str,
    project_name: str,
    playbook: str,
    inventory: Optional[str] = None,
    inventory_file: Optional[str] = None,
    extra_vars: Optional[dict] = None,
    target_scope: str = "inventory",
    target_group_name: Optional[str] = None,
    target_host_name: Optional[str] = None,
) -> dict:
    """Synchronous ansible-runner execution with real-time log capture."""
    try:
        import ansible_runner
    except ImportError:
        logger.error("ansible-runner is not installed")
        _append_log(job_id, "[ERROR] ansible-runner is not installed on this system")
        return {
            "status": "error", "rc": -1, "stdout": "",
            "error_message": "ansible-runner is not installed on this system",
        }

    # Resolve project directory (ansible-runner private_data_dir)
    private_data_dir = str(_get_project_dir(project_name))

    if not os.path.isdir(private_data_dir):
        error_msg = f"Project directory not found: {private_data_dir}"
        _append_log(job_id, f"[ERROR] {error_msg}")
        return {"status": "error", "rc": -1, "stdout": "", "error_message": error_msg}

    # Prepare inventory
    inv_path = None
    temp_inv_file = None
    temp_runtime_inventory_path = None

    if inventory:
        temp_inv_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".ini", delete=False, dir=private_data_dir
        )
        temp_inv_file.write(inventory)
        temp_inv_file.close()
        inv_path = temp_inv_file.name
    elif inventory_file:
        if os.path.isabs(inventory_file):
            inv_path = inventory_file
            temp_runtime_inventory_path = inventory_file
        else:
            inv_path = os.path.join(private_data_dir, "inventory", inventory_file)
        if not os.path.exists(inv_path):
            error_msg = f"Inventory file not found: {inventory_file}"
            _append_log(job_id, f"[ERROR] {error_msg}")
            return {"status": "error", "rc": -1, "stdout": "", "error_message": error_msg}

    try:
        limit = build_ansible_limit(target_scope, target_group_name, target_host_name)
        runner_env = {
            "ANSIBLE_COLLECTIONS_PATH": settings.ANSIBLE_DATA_DIR,
            "ANSIBLE_LIBRARY": str(Path(settings.ANSIBLE_DATA_DIR) / "modules"),
        }

        runner_kwargs: dict[str, object] = {
            "private_data_dir": private_data_dir,
            "playbook": f"playbooks/{playbook}", # 'playbooks/' 경로 추가
            # "playbook": playbook,
            "envvars": runner_env,
        }
        if inv_path:
            runner_kwargs["inventory"] = inv_path
        merged_extra_vars = _merge_extra_vars(private_data_dir, extra_vars)
        if merged_extra_vars:
            runner_kwargs["extravars"] = merged_extra_vars
        if limit is not None:
            runner_kwargs["limit"] = limit

        _append_log(job_id, f"[HARNESS] Project: {project_name}")
        _append_log(job_id, f"[HARNESS] Playbook: playbooks/{playbook}")
        _append_log(job_id, f"[HARNESS] Data dir: {private_data_dir}")
        _append_log(job_id, f"[HARNESS] Target: {limit or 'inventory'}")
        _append_log(job_id, "")

        def handle_event(event_data):
            stdout_line = event_data.get("stdout", "")
            if stdout_line:
                for line in stdout_line.split("\n"):
                    clean_line = line.rstrip("\r")
                    if clean_line or line == "":
                        _append_log(job_id, clean_line)
            return True

        runner_kwargs["event_handler"] = handle_event
        thread, runner = ansible_runner.run_async(**runner_kwargs)

        while thread.is_alive():
            time.sleep(0.2)

        stdout_text = runner.stdout.read() if runner.stdout else ""

        result = {
            "status": runner.status,
            "rc": runner.rc,
            "stdout": stdout_text,
            "artifact_dir": runner.artifact_dir if hasattr(runner, "artifact_dir") else None,
            "error_message": None,
        }

        _append_log(job_id, "")
        _append_log(job_id, f"[HARNESS] Finished: {runner.status} (rc={runner.rc})")

        return result

    except Exception as e:
        logger.exception("ansible-runner execution failed")
        _append_log(job_id, f"[ERROR] {str(e)}")
        return {"status": "error", "rc": -1, "stdout": "", "error_message": str(e)}
    finally:
        if temp_inv_file and os.path.exists(temp_inv_file.name):
            try:
                os.unlink(temp_inv_file.name)
            except OSError:
                pass
        if temp_runtime_inventory_path and os.path.exists(temp_runtime_inventory_path):
            try:
                os.unlink(temp_runtime_inventory_path)
            except OSError:
                pass


async def execute_job(job_id: uuid.UUID) -> None:
    """Execute an Ansible job asynchronously."""
    logger.info(f"Starting execution for job {job_id}")
    jid = str(job_id)
    _init_log_buffer(jid)

    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error(f"Job {job_id} not found")
            cleanup_log_buffer(jid)
            return

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await session.commit()

        runtime_inventory_path = None
        runner_target_scope = job.target_scope
        runner_target_group_name = job.target_group_name
        runner_target_host_name = job.target_host_name
        inventory_vars = None
        if job.extra_vars and "__inventory_vars__" in job.extra_vars:
            inventory_vars = job.extra_vars.get("__inventory_vars__")

        if job.managed_inventory_id:
            from app.services.inventory_v2_service import materialize_v2_runtime_inventory

            materialized = await materialize_v2_runtime_inventory(
                session,
                job.managed_inventory_id,
                str(_get_project_dir(job.project)),
                job.target_scope,
                job.target_group_name,
                job.target_host_name,
                job.extra_vars,
                inventory_vars,
            )
            if materialized is None:
                job.status = "error"
                job.finished_at = datetime.now(timezone.utc)
                job.error_message = f"Managed inventory '{job.managed_inventory_id}' not found"
                await session.commit()
                _finish_log_buffer(jid, "error", -1)
                return
            runtime_inventory_path, revision = materialized
            job.managed_inventory_revision = revision
            runner_target_scope = "inventory"
            runner_target_group_name = None
            runner_target_host_name = None
            await session.commit()
        elif job.inventory_file:
            from app.services.managed_inventory_service import materialize_runtime_inventory

            runtime_inventory_path = await materialize_runtime_inventory(
                session,
                job.project,
                job.inventory_file,
                str(_get_project_dir(job.project)),
            )

    loop = asyncio.get_event_loop()
    run_future = loop.run_in_executor(
        executor,
        _run_playbook_sync,
        jid,
        job.project,
        job.playbook,
        job.inventory,
        runtime_inventory_path or job.inventory_file,
        job.extra_vars,
        runner_target_scope,
        runner_target_group_name,
        runner_target_host_name,
    )
    last_persisted_total = -1

    while not run_future.done():
        snapshot = get_live_log_snapshot(jid, 0)
        if snapshot is not None and snapshot["total"] != last_persisted_total:
            await persist_live_stdout(job_id, "\n".join(snapshot["lines"]))
            last_persisted_total = snapshot["total"]

        await asyncio.sleep(0.5)

    run_result = await run_future

    status_map = {"successful": "success", "failed": "failed", "timeout": "failed", "error": "error"}
    final_status = status_map.get(run_result["status"], "error")
    _finish_log_buffer(jid, final_status, run_result.get("rc"))

    async with async_session() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            cleanup_log_buffer(jid)
            return

        job.status = final_status
        job.finished_at = datetime.now(timezone.utc)
        job.rc = run_result.get("rc")
        job.stdout = run_result.get("stdout", "")
        job.error_message = run_result.get("error_message")
        job.artifact_dir = run_result.get("artifact_dir")
        await session.commit()

    logger.info(f"Job {job_id} completed with status: {final_status}")
    await asyncio.sleep(30)
    cleanup_log_buffer(jid)
