"""Hermes slash-command adapter for the shared bSmart project engine."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

_DEFAULT_SYSTEM_ROOT = "/workspace/bSmart-System"
_DEFAULT_PROJECTS_ROOT = "/projects"
_DEFAULT_STATE_FILE = "/workspace/bSmart/bSmart_State.md"
_DEFAULT_ARCHIVE_ROOT = "/workspace/bSmart/.project-archives"


def _context() -> dict[str, str]:
    """Resolve trusted process configuration, never paths from chat arguments."""
    state_file = Path(os.environ.get("BSMART_STATE_FILE", _DEFAULT_STATE_FILE)).resolve()
    return {
        "projectsRoot": str(Path(os.environ.get("BSMART_PROJECT_ROOT", _DEFAULT_PROJECTS_ROOT)).resolve()),
        "stateFile": str(state_file),
        "archiveRoot": str(Path(os.environ.get("BSMART_ARCHIVE_ROOT", _DEFAULT_ARCHIVE_ROOT)).resolve()),
        "home": str(state_file.parent),
    }


def _cli_path() -> Path:
    root = Path(os.environ.get("BSMART_SYSTEM_ROOT", _DEFAULT_SYSTEM_ROOT)).resolve()
    cli = root / "scripts" / "bsmart-project.mjs"
    if not cli.is_file():
        raise RuntimeError(f"bSmart project CLI not found: {cli}")
    return cli


def _execute(command: str) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        return {"status": "error", "diagnostic": "Node.js executable not found"}
    try:
        completed = subprocess.run(
            [node, str(_cli_path())],
            input=json.dumps({"command": command, "context": _context()}),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        return {"status": "error", "diagnostic": str(exc)}
    try:
        result = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        detail = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        return {"status": "error", "diagnostic": f"Invalid bSmart project CLI response: {detail}"}
    if not isinstance(result, dict):
        return {"status": "error", "diagnostic": "Invalid bSmart project CLI response shape"}
    return result


def _format(result: dict[str, Any]) -> str:
    status = result.get("status")
    diagnostic = str(result.get("diagnostic") or "Project command completed")
    if status == "error":
        return f"Project command failed: {diagnostic}"
    if status == "cancelled":
        return diagnostic
    if status == "pending":
        pending = result.get("pending") or {}
        pending_id = pending.get("id")
        target = pending.get("target") or pending.get("project") or "unknown"
        operation = pending.get("operation") or "change"
        rename = f" to `{pending.get('newName')}`" if pending.get("newName") else ""
        if not pending_id:
            return f"Confirmation required for {operation} target `{target}`{rename}, but no confirmation ID was returned."
        return (
            f"Confirmation required: {operation} exact target `{target}`{rename}.\n"
            f"Yes: /project yes {pending_id}\n"
            f"No: /project no {pending_id}"
        )
    projects = result.get("projects")
    selection = result.get("selection") or {}
    if isinstance(projects, list):
        current = selection.get("project")
        lines = ["Projects:"]
        if not projects:
            lines.append("- none")
        for project in projects:
            name = project.get("name", "?") if isinstance(project, dict) else str(project)
            kind = project.get("kind") if isinstance(project, dict) else None
            marker = " (current)" if name == current else ""
            suffix = f" [{kind}]" if kind else ""
            lines.append(f"- {name}{suffix}{marker}")
        lines.append(f"Current: {current or 'Free Mode'}")
        if selection.get("workstream"):
            lines[-1] += f" / {selection['workstream']}"
        return "\n".join(lines)
    if status == "ok" and "selection" in result:
        project = selection.get("project")
        if not project:
            return f"{diagnostic}. Current: Free Mode."
        current = project
        if selection.get("workstream"):
            current += f" / {selection['workstream']}"
        return f"{diagnostic}. Current: {current}."
    return diagnostic


def _handler(prefix: str):
    def handle(raw_args: str) -> str:
        args = (raw_args or "").strip()
        command = prefix + (f" {args}" if args else "")
        return _format(_execute(command))
    return handle


def register(ctx: Any) -> None:
    description = "List, select, create, rename, retire, or delete bSmart projects."
    args_hint = "[list|NAME|ws WS|add NAME|rename NAME|retire|delete|yes ID|no ID]"
    ctx.register_command("project", _handler("/project"), description, args_hint)
    ctx.register_command("projcet", _handler("/projcet"), "Alias for /project.", args_hint)
