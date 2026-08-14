"""Render structured managed inventories into Ansible inventory text."""

import json
from dataclasses import dataclass
from typing import Any


SECRET_VAR_MARKERS = ("password", "passwd", "secret", "private_key", "token")


@dataclass(frozen=True)
class RenderHost:
    name: str
    address: str
    connection_type: str
    port: int
    remote_user: str | None
    become_enabled: bool
    become_user: str | None
    login_credential_ref: str | None
    become_credential_ref: str | None
    login_credential_type: str | None
    become_credential_type: str | None
    login_credential_username: str | None
    become_credential_username: str | None
    host_vars: dict[str, Any]


@dataclass(frozen=True)
class RenderGroup:
    name: str
    group_vars: dict[str, Any]
    hosts: list[RenderHost]


def _safe_var_items(values: dict[str, Any]) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []
    for key, value in sorted(values.items()):
        lowered = key.lower()
        if any(marker in lowered for marker in SECRET_VAR_MARKERS):
            continue
        items.append((key, value))
    return items


def _stringify(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _encode_ini_value(value: Any) -> str:
    if isinstance(value, str):
        if value == "" or any(char.isspace() for char in value) or any(char in value for char in ('"', "'", "#", ";", "\\")):
            return json.dumps(value)
        return value
    return _stringify(value)


def _format_assignment(key: str, value: Any) -> str:
    return f"{key}={_encode_ini_value(value)}"


def render_public_inventory(groups: list[RenderGroup]) -> str:
    """Render non-secret compatibility inventory for listing and manual inspection."""

    lines: list[str] = []
    for group in groups:
        lines.append(f"[{group.name}]")
        for host in group.hosts:
            parts = [host.name, _format_assignment("ansible_host", host.address), _format_assignment("ansible_connection", host.connection_type)]
            parts.append(_format_assignment("ansible_port", host.port))
            ansible_user = host.remote_user or host.login_credential_username
            if ansible_user:
                parts.append(_format_assignment("ansible_user", ansible_user))
            if host.become_enabled:
                parts.append(_format_assignment("ansible_become", True))
                ansible_become_user = host.become_credential_username or host.become_user
                if ansible_become_user:
                    parts.append(_format_assignment("ansible_become_user", ansible_become_user))
            if host.login_credential_ref:
                parts.append(_format_assignment("ansibleharness_login_credential_ref", host.login_credential_ref))
            if host.become_credential_ref:
                parts.append(_format_assignment("ansibleharness_become_credential_ref", host.become_credential_ref))
            for key, value in _safe_var_items(host.host_vars):
                parts.append(_format_assignment(key, value))
            lines.append(" ".join(parts))
        if group.group_vars:
            lines.append("")
            lines.append(f"[{group.name}:vars]")
            for key, value in _safe_var_items(group.group_vars):
                lines.append(_format_assignment(key, value))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n" if lines else ""


def render_runtime_inventory(groups: list[RenderGroup], secrets_by_ref: dict[str, str]) -> str:
    """Render execution inventory with resolved secrets injected only into a temp file."""

    return render_runtime_inventory_with_become(groups, secrets_by_ref, {})


def render_runtime_inventory_with_become(
    groups: list[RenderGroup],
    secrets_by_ref: dict[str, str],
    become_secrets_by_ref: dict[str, str],
    inventory_vars: dict | None = None,
) -> str:
    """Render execution inventory with login and optional become secrets."""

    lines: list[str] = []
    for group in groups:
        lines.append(f"[{group.name}]")
        for host in group.hosts:
            parts = [host.name, _format_assignment("ansible_host", host.address), _format_assignment("ansible_connection", host.connection_type)]
            parts.append(_format_assignment("ansible_port", host.port))
            ansible_user = host.remote_user or host.login_credential_username
            if ansible_user:
                parts.append(_format_assignment("ansible_user", ansible_user))
            if host.login_credential_ref and host.login_credential_ref in secrets_by_ref:
                if host.login_credential_type == "ssh_key":
                    parts.append(_format_assignment("ansible_ssh_private_key_file", secrets_by_ref[host.login_credential_ref]))
                else:
                    parts.append(_format_assignment("ansible_password", secrets_by_ref[host.login_credential_ref]))
            if host.become_enabled:
                parts.append(_format_assignment("ansible_become", True))
                ansible_become_user = host.become_credential_username or host.become_user
                if ansible_become_user:
                    parts.append(_format_assignment("ansible_become_user", ansible_become_user))
                if host.login_credential_ref and host.login_credential_ref in become_secrets_by_ref:
                    parts.append(_format_assignment("ansible_become_password", become_secrets_by_ref[host.login_credential_ref]))
                elif host.become_credential_ref and host.become_credential_ref in secrets_by_ref:
                    parts.append(_format_assignment("ansible_become_password", secrets_by_ref[host.become_credential_ref]))
            for key, value in sorted(host.host_vars.items()):
                parts.append(_format_assignment(key, value))
            lines.append(" ".join(parts))
        if group.group_vars:
            lines.append("")
            lines.append(f"[{group.name}:vars]")
            for key, value in sorted(group.group_vars.items()):
                lines.append(_format_assignment(key, value))
        lines.append("")
    
    if inventory_vars:
        lines.append("[all:vars]")
        for key, value in sorted(inventory_vars.items()):
            lines.append(_format_assignment(key, value))
        lines.append("")
        
    return "\n".join(lines).rstrip("\n") + "\n" if lines else ""
