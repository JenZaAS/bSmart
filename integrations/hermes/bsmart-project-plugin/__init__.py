"""Hermes slash-command adapter for the shared bSmart project engine."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_DEFAULT_SYSTEM_ROOT = "/workspace/bSmart-System"
_DEFAULT_PROJECTS_ROOT = "/projects"
_DEFAULT_ARCHIVE_ROOT = "/workspace/bSmart/.project-archives"
_DEFAULT_HOME = "/workspace/bSmart"


def _system_roots() -> list[Path]:
    """Checkout that holds scripts/bsmart_instance.py.

    An installed copy under HERMES_HOME/plugins/bsmart-project/ is not next to
    that file. BSMART_SYSTEM_ROOT wins. When it is unset, the container
    default /workspace/bSmart-System is used so container-storage.yaml is
    still read. The source checkout is last, for a plugin that has not been
    copied out of the repo.
    """
    roots: list[Path] = []
    system = os.environ.get("BSMART_SYSTEM_ROOT")
    roots.append(Path(system).expanduser() if system else Path(_DEFAULT_SYSTEM_ROOT))
    here = Path(__file__).resolve()
    if len(here.parents) >= 4:
        roots.append(here.parents[3])
    return roots


def _instance_helper():
    for root in _system_roots():
        path = root / "scripts" / "bsmart_instance.py"
        if not path.is_file():
            continue
        name = "bsmart_instance_" + str(abs(hash(str(path.absolute()))))
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


def _instance_workspace() -> Path | None:
    for root in _system_roots():
        if (root / "scripts" / "bsmart_instance.py").is_file():
            return root.resolve().parent
    return None


def _projects_root() -> str:
    """Env override, then the storage spec, then /projects and ./projects."""
    override = os.environ.get("BSMART_PROJECT_ROOT")
    if override:
        return str(Path(override).expanduser().resolve())
    helper = _instance_helper()
    workspace = _instance_workspace()
    if helper is not None and workspace is not None:
        selected = helper.select_instance_project_root(workspace)
        if selected is not None:
            return str(selected)
    return str(Path(_DEFAULT_PROJECTS_ROOT).resolve())


_HARNESS_SESSION_KEYS = (
    "HERMES_SESSION_KEY",
    "HERMES_SESSION_ID",
    "CLAUDE_SESSION_ID",
    "CURSOR_CONVERSATION_ID",
    "CURSOR_SESSION_ID",
    "CODEX_THREAD_ID",
    "CODEX_SESSION_ID",
)


def _sanitize_session_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")[:80]


def _hermes_context_value(name: str) -> str:
    """Hermes keeps the live chat id in a context variable, not os.environ."""
    try:
        from gateway.session_context import get_session_env
    except ImportError:
        return ""
    try:
        return str(get_session_env(name, "") or "").strip()
    except Exception:
        return ""


def _channel_session_id() -> str:
    """Stable id for this conversation. Fallback is one channel per instance home.

    A harness that exposes a session id gets its own file. Parallel chats on a
    harness that exposes none share channel-client; /project delete NAME does
    not depend on that file.
    """
    explicit = os.environ.get("BSMART_SESSION_ID", "").strip()
    if explicit:
        cleaned = _sanitize_session_id(explicit)
        if not cleaned or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", cleaned):
            raise ValueError("Invalid session id")
        return cleaned
    for name in ("HERMES_SESSION_KEY", "HERMES_SESSION_ID"):
        value = _hermes_context_value(name) or os.environ.get(name, "").strip()
        if value:
            cleaned = _sanitize_session_id("hermes-" + value)
            if cleaned:
                return cleaned
    for name in _HARNESS_SESSION_KEYS:
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        cleaned = _sanitize_session_id(name.lower().replace("_", "-") + "-" + value)
        if cleaned:
            return cleaned
    return "channel-client"


def _context() -> dict[str, str]:
    """Resolve trusted process configuration, never paths from chat arguments."""
    archive = Path(os.environ.get("BSMART_ARCHIVE_ROOT", _DEFAULT_ARCHIVE_ROOT)).resolve()
    home = Path(os.environ.get("BSMART_INSTANCE_HOME", "")).expanduser().resolve() if os.environ.get("BSMART_INSTANCE_HOME") else archive.parent
    return {
        "projectsRoot": _projects_root(),
        "archiveRoot": str(archive),
        "home": str(home),
    }


def _session_from_env() -> dict[str, str | None] | None:
    """Return this process's session only when the caller set it. Do not invent one."""
    if "BSMART_SESSION_PROJECT" not in os.environ and "BSMART_SESSION_WORKSTREAM" not in os.environ:
        return None
    project = os.environ.get("BSMART_SESSION_PROJECT", "").strip()
    workstream = os.environ.get("BSMART_SESSION_WORKSTREAM", "").strip()
    if project.lower() in {"", "none", "free"}:
        project = ""
    if workstream.lower() in {"", "none"}:
        workstream = ""
    return {"project": project or None, "workstream": workstream or None}


def _cli_path() -> Path:
    root = Path(os.environ.get("BSMART_SYSTEM_ROOT", _DEFAULT_SYSTEM_ROOT)).resolve()
    cli = root / "scripts" / "bsmart-project.mjs"
    if not cli.is_file():
        raise RuntimeError(f"bSmart project CLI not found: {cli}")
    return cli


def _role_cli_path() -> Path:
    root = Path(os.environ.get("BSMART_SYSTEM_ROOT", _DEFAULT_SYSTEM_ROOT)).resolve()
    cli = root / "scripts" / "bsmart-role.mjs"
    if not cli.is_file():
        raise RuntimeError(f"bSmart role CLI not found: {cli}")
    return cli


def _execute(command: str) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        return {"status": "error", "diagnostic": "Node.js executable not found"}
    try:
        request: dict[str, Any] = {"command": command, "context": _context()}
        session = _session_from_env()
        explicit_id = os.environ.get("BSMART_SESSION_ID", "").strip()
        # An explicit project env is this process only and must not overwrite
        # another conversation's file. With no project env, persist by session id.
        if session is not None and not explicit_id:
            request["session"] = session
        else:
            try:
                request["context"]["sessionId"] = _channel_session_id()
            except ValueError as exc:
                return {"status": "error", "diagnostic": str(exc)}
            if session is not None:
                request["session"] = session
        handoff = os.environ.get("BSMART_SESSION_HANDOFF", "").strip()
        if handoff:
            request["handoff"] = handoff
        completed = subprocess.run(
            [node, str(_cli_path())],
            input=json.dumps(request),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
            shell=False,
            encoding="utf-8",
            errors="replace",
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


def _execute_role(command: str) -> dict[str, Any]:
    node = shutil.which("node")
    if not node:
        return {"status": "error", "diagnostic": "Node.js executable not found"}
    try:
        completed = subprocess.run(
            [node, str(_role_cli_path())],
            input=json.dumps({"command": command, "context": _context()}),
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        result = json.loads(completed.stdout)
        return result if isinstance(result, dict) else {"status": "error", "diagnostic": "Invalid bSmart role CLI response shape"}
    except (OSError, subprocess.SubprocessError, RuntimeError, json.JSONDecodeError) as exc:
        return {"status": "error", "diagnostic": str(exc)}


def _format(result: dict[str, Any]) -> str:
    status = result.get("status")
    diagnostic = str(result.get("diagnostic") or "Project command completed")
    if status == "error":
        return f"Project command failed: {diagnostic}"
    if status == "handoff_required":
        return diagnostic
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
            marker = " (current)" if name == current else ""
            lines.append(f"- {name}{marker}")
        lines.append(f"Current: {current or 'Free Mode'}")
        if selection.get("workstream"):
            lines[-1] += f" / {selection['workstream']}"
        return "\n".join(lines)
    if status == "ok" and "selection" in result:
        project = selection.get("project")
        startup = result.get("startup")
        if not project:
            text = f"{diagnostic}. Current: Free Mode."
        else:
            current = project
            if selection.get("workstream"):
                current += f" / {selection['workstream']}"
            text = f"{diagnostic}. Current: {current}."
        if startup:
            text += "\n" + str(startup)
        return text
    return diagnostic


def _handler(prefix: str):
    def handle(raw_args: str) -> str:
        args = (raw_args or "").strip()
        command = prefix + (f" {args}" if args else "")
        return _format(_execute(command))
    return handle


def _role_handler(raw_args: str) -> str:
    result = _execute_role("/role" + (f" {raw_args.strip()}" if raw_args and raw_args.strip() else " help"))
    if result.get("status") == "error":
        return f"Role command failed: {result.get('diagnostic', 'unknown error')}"
    return str(result.get("diagnostic", "Roles are deprecated. Use /project."))


def register(ctx: Any) -> None:
    description = "List, select, create, rename, retire, or delete bSmart projects."
    args_hint = "[list|NAME|ws WS|add NAME|rename NAME|retire|delete|yes ID|no ID]"
    ctx.register_command("project", _handler("/project"), description, args_hint)
    ctx.register_command("role", _role_handler, "Roles are deprecated. Use /project.", "[any arguments]")
