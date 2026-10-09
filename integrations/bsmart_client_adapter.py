#!/usr/bin/env python3
"""Deterministic /project and /role entry for Cursor, Codex, and Claude.

The Hermes plugin remains the chat adapter for Hermes. This script is the
shared caller for the other clients. It does not implement project or role
behavior; it resolves trusted paths and calls the Hermes adapter, which calls
the shared Node engines.
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys
from pathlib import Path

_KINDS = {"project", "role"}
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_./:-]+$")


def find_workspace(start: Path) -> Path | None:
    current = start.expanduser()
    try:
        current = current.resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        if (candidate / "bSmart-System" / "bStart.py").is_file():
            return candidate
    return None


def workspace_from_here() -> Path | None:
    here = Path(__file__).resolve()
    if here.parent.name == "integrations" and len(here.parents) > 2:
        candidate = here.parents[2]
        if (candidate / "bSmart-System" / "bStart.py").is_file():
            return candidate
    return find_workspace(Path.cwd())


def load_instance_helper(workspace: Path):
    """Shared project-root resolver. Loaded by path so a copied adapter still finds it."""
    candidates = (
        Path(__file__).resolve().parents[1] / "scripts" / "bsmart_instance.py",
        workspace / "bSmart-System" / "scripts" / "bsmart_instance.py",
    )
    for path in candidates:
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


def instance_project_root(workspace: Path) -> Path:
    helper = load_instance_helper(workspace)
    if helper is not None:
        selected = helper.select_instance_project_root(workspace)
        if selected is not None:
            return selected
    mounted = Path("/projects")
    return mounted if mounted.is_dir() else workspace / "projects"


def ensure_environment(workspace: Path) -> None:
    """Fill only unset bSmart path variables. Chat arguments never set these."""
    content = workspace / "bSmart"
    container_roles = Path("/workspace/bSmart/Roles")
    roles = container_roles if container_roles.is_dir() else content / "Roles"
    projects = instance_project_root(workspace)
    values = {
        "BSMART_SYSTEM_ROOT": workspace / "bSmart-System",
        "BSMART_PROJECT_ROOT": projects,
        "BSMART_ROLES_ROOT": roles,
        "BSMART_ROLE_SELECTOR": roles / "current_role.md",
        "BSMART_LEGACY_STATE_FILE": content / "bSmart_State.md",
        "BSMART_ARCHIVE_ROOT": content / ".project-archives",
    }
    for key, path in values.items():
        if not os.environ.get(key):
            os.environ[key] = str(path)


def load_hermes_adapter():
    system = Path(os.environ["BSMART_SYSTEM_ROOT"]).resolve()
    plugin = system / "integrations" / "hermes" / "bsmart-project-plugin" / "__init__.py"
    if not plugin.is_file():
        raise RuntimeError(f"Hermes project adapter not found: {plugin}")
    spec = importlib.util.spec_from_file_location("bsmart_hermes_project_plugin", plugin)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load Hermes project adapter: {plugin}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quote_token(token: str) -> str:
    if _SAFE_TOKEN.fullmatch(token):
        return token
    return '"' + token.replace('"', "") + '"'


def command_text(kind: str, args: list[str]) -> str:
    if any(token.startswith("-") or "\n" in token or "\x00" in token for token in args):
        raise ValueError("flags and control characters are not accepted")
    if not args:
        return f"/{kind}"
    return f"/{kind} " + " ".join(quote_token(token) for token in args)


def run(kind: str, args: list[str], workspace: Path | None = None) -> str:
    if kind not in _KINDS:
        raise ValueError("Use project or role")
    root = workspace or workspace_from_here()
    if root is None:
        raise RuntimeError("bSmart workspace not found")
    ensure_environment(root)
    plugin = load_hermes_adapter()
    if kind == "role":
        return plugin._role_handler(" ".join(quote_token(token) for token in args) if args else "")
    return plugin._format(plugin._execute(command_text(kind, args)))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in _KINDS:
        print("Use: bsmart_client_adapter.py project|role [arguments]", file=sys.stderr)
        return 2
    try:
        text = run(args[0], args[1:])
    except (OSError, RuntimeError, ValueError) as exc:
        label = "Role command failed" if args[0] == "role" else "Project command failed"
        text = f"{label}: {exc}"
    sys.stdout.write(text if text.endswith("\n") else text + "\n")
    return 0 if not text.startswith(("Project command failed:", "Role command failed:")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
