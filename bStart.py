#!/usr/bin/env python3
"""Deterministic bSmart session startup.

This is the tracked system entrypoint. It performs safe system freshness checks,
reads the project index, and emits a compact startup payload. A new session
starts in Free mode. It does not read or write a shared project selector.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

# absolute() keeps a symlinked bSmart-System attached to the instance that
# launched it. resolve() would follow that link into another instance.
SCRIPT_ROOT = Path(__file__).absolute().parent


def system_checkout(path: Path) -> bool:
    return (path / "scripts" / "bsmart-system-update-check").is_file()


def workspace_root_copy(path: Path) -> bool:
    """True for the installed bStart.py that sits beside bSmart-System/."""
    return (path / "bSmart-System").is_dir() and not system_checkout(path)


def default_workspace() -> Path:
    # The canonical file lives in bSmart-System, so the workspace is its parent.
    # bsmart-instance-upgrade also copies this file to the workspace root; that
    # copy must not treat the parent of the workspace as the workspace.
    if workspace_root_copy(SCRIPT_ROOT):
        return SCRIPT_ROOT
    return SCRIPT_ROOT.parent


DEFAULT_WORKSPACE = default_workspace()


def configure_output_streams() -> None:
    """Print instance text without raising UnicodeEncodeError.

    This function stays in this file. bsmart-instance-upgrade installs the
    workspace-root copy as this file alone, so the fix cannot live in a helper
    the copy would have to import.

    A pipe or redirect on Windows uses the ANSI code page (often cp1252) with
    a strict error handler. Session hooks capture startup that way, and project
    or content files can contain characters that page cannot encode, such as
    U+2610. UTF-8 keeps those characters. When a stream cannot change encoding,
    keep its current encoding and escape characters it cannot represent.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            try:
                reconfigure(errors="backslashreplace")
            except (AttributeError, OSError, ValueError):
                continue


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(command: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


def git_safe_directory(repo: Path) -> str:
    """Forward slashes, so Git's safe.directory match works on Windows."""
    return os.path.normpath(str(repo)).replace("\\", "/")


def git_run(repo: Path, args: list[str], timeout: int = 20) -> subprocess.CompletedProcess[str]:
    return run(["git", "-c", f"safe.directory={git_safe_directory(repo)}", *args], repo, timeout)


def first_value(text: str, keys: tuple[str, ...]) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        for key in keys:
            match = re.match(rf"{re.escape(key)}\s*:\s*[`\"']?([^`\"']+?)[`\"']?\s*$", stripped)
            if match:
                value = match.group(1).strip()
                if value and not value.startswith("<"):
                    return value
    return None


def content_root_for(workspace: Path) -> Path:
    """Content root for this instance: sibling bSmart, not another instance's.

    Same rule as scripts/bsmart_instance.default_content_root. This file is
    also copied to the workspace root, so it does not import that module.
    """
    sibling = workspace / "bSmart"
    container = Path("/workspace/bSmart")
    if sibling.is_dir():
        return sibling
    if os.path.normpath(str(workspace.absolute())) == os.path.normpath("/workspace") and container.is_dir():
        return container
    return sibling


def resolve_paths(workspace: Path) -> tuple[Path, Path]:
    system = workspace / "bSmart-System"
    if system.is_dir():
        # Keep the launched path. Resolving a symlinked bSmart-System jumps to
        # the checkout it points at and would cache state in that other instance.
        return system, content_root_for(workspace)
    if system_checkout(SCRIPT_ROOT):
        if (workspace / "bSmart").is_dir():
            return SCRIPT_ROOT, workspace / "bSmart"
        return SCRIPT_ROOT, content_root_for(SCRIPT_ROOT.parent)
    if workspace_root_copy(SCRIPT_ROOT):
        workspace = SCRIPT_ROOT
        return workspace / "bSmart-System", content_root_for(workspace)
    return system, content_root_for(workspace)


def git_status(repo: Path, label: str) -> str:
    if not (repo / ".git").exists():
        return f"{label}: no Git repository"
    status = git_run(repo, ["status", "--porcelain"])
    branch = git_run(repo, ["branch", "--show-current"])
    if status.returncode != 0 or branch.returncode != 0:
        return f"{label}: Git status unavailable"
    dirty = bool(status.stdout.strip())
    branch_name = branch.stdout.strip() or "detached"
    upstream = git_run(repo, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if upstream.returncode != 0:
        suffix = "uncommitted changes" if dirty else "clean; no remote tracking branch"
        return f"{label}: {suffix} ({branch_name})"
    counts = git_run(repo, ["rev-list", "--left-right", "--count", "HEAD...@{u}"])
    ahead = behind = 0
    if counts.returncode == 0:
        values = counts.stdout.split()
        if len(values) >= 2:
            ahead, behind = int(values[0]), int(values[1])
    parts: list[str] = []
    if dirty:
        parts.append("uncommitted changes")
    if ahead:
        parts.append(f"{ahead} commit{'s' if ahead != 1 else ''} ahead")
    if behind:
        parts.append(f"{behind} commit{'s' if behind != 1 else ''} behind")
    if not parts:
        parts.append("up-to-date")
    return f"{label}: {'; '.join(parts)} ({branch_name})"


def safe_system_update(system: Path, content: Path, skip: bool) -> tuple[bool, str]:
    if skip:
        return False, "bSmart-System: update check skipped"
    helper = system / "scripts" / "bsmart-system-update-check"
    if not helper.is_file():
        return False, "bSmart-System: update helper unavailable"
    state = content / "State" / "bsmart-system-update.yaml"
    proc = run(
        [sys.executable, str(helper), "--auto-pull", "--repo", str(system), "--state", str(state)],
        system,
        90,
    )
    output = " ".join((proc.stdout + " " + proc.stderr).split())
    updated = "updated" in output.lower() and "skipped" not in output.lower()
    if not output:
        output = "update check returned no status"
    return updated, f"bSmart-System update: {output}"


def integrity_check(system: Path) -> list[str]:
    repaired: list[str] = []
    claude = system / "bSmart_Templates" / "CLAUDE.md"
    agents = system / "bSmart_Templates" / "AGENTS.md"
    if not claude.is_file() and agents.is_file():
        claude.write_text(agents.read_text(encoding="utf-8"), encoding="utf-8")
        repaired.append("CLAUDE.md")
    required = (
        "bSmart.md", "bSmart_Invariants.md", "bSmart_Map.md", "bSmart_Features.md",
        "bSmart_Setup.md", "bSmart_Protocols/protocols.md",
        "bSmart_Protocols/roles-and-concurrency.md",
        "bSmart_Protocols/projects.md",
        "bSmart_Templates/AGENTS.md", "bSmart_Templates/CLAUDE.md",
    )
    missing = [item for item in required if not (system / item).is_file()]
    if missing:
        return ["Integrity: blocked; missing system files: " + ", ".join(missing)]
    if repaired:
        return ["Integrity: OK; repaired " + ", ".join(repaired)]
    return ["Integrity: OK"]


def load_named_module(relative: str):
    """Load a checkout helper by path.

    The workspace-root copy of this file does not sit beside the helper.
    A unique module name keeps one process from reusing another checkout's copy.
    """
    candidates = (
        SCRIPT_ROOT / "scripts" / relative,
        SCRIPT_ROOT / "bSmart-System" / "scripts" / relative,
    )
    for path in candidates:
        if not path.is_file():
            continue
        name = "bsmart_" + path.stem + "_" + str(abs(hash(str(path.absolute()))))
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return None


def load_instance_module():
    return load_named_module("bsmart_instance.py")


def load_session_module():
    return load_named_module("bsmart_session_projects.py")


def project_root(content: Path) -> Path | None:
    module = load_instance_module()
    if module is not None:
        return module.select_instance_project_root(content.parent)
    override = os.environ.get("BSMART_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser()
        return candidate.resolve() if candidate.is_dir() and os.access(candidate, os.R_OK) else None
    for candidate in (Path("/projects"), content.parent / "projects"):
        if candidate.is_dir() and os.access(candidate, os.R_OK):
            return candidate.resolve()
    return None


def project_catalog(root: Path | None, warnings: list[str]) -> list[str]:
    """Read or create the project index. Return active-project display lines.

    A missing index is generated from project folders. A present index is not
    rewritten; mismatches are reported with the repair command.
    """
    if root is None:
        return []
    module = load_session_module()
    if module is None:
        warnings.append("Index: session project helper is unavailable.")
        return []
    try:
        rows, created = module.ensure_index(root)
        mismatches = module.self_check(root, rows)
    except OSError as exc:
        warnings.append(f"Index: could not read project index: {exc}")
        return []
    if created:
        warnings.append("Index: created from project folders.")
    else:
        for mismatch in mismatches:
            warnings.append(f"Index: {mismatch}")
        if mismatches:
            warnings.append("Index: repair with /project index repair")
    lines = []
    for row in module.active_rows(rows):
        label = row.get("label") or ""
        suffix = f" ({label})" if label else ""
        lines.append(f"  - {row['name']}{suffix}")
    return lines


def main() -> int:
    configure_output_streams()
    parser = argparse.ArgumentParser(description="Run deterministic bSmart session startup.")
    parser.add_argument("--root", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--role", help=argparse.SUPPRESS)
    parser.add_argument("--skip-update", action="store_true")
    parser.add_argument("--skip-integrity", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.root).expanduser().absolute()
    system, content = resolve_paths(workspace)
    warnings: list[str] = []
    updated, update_line = safe_system_update(system, content, args.skip_update)
    integrity: list[str] = []
    if updated and not args.skip_integrity:
        integrity = integrity_check(system)
        if any("blocked" in line for line in integrity):
            warnings.extend(integrity)

    agent_file = content / "bSmart_Agent.md"
    agent_text = agent_file.read_text(encoding="utf-8", errors="replace") if agent_file.is_file() else ""
    agent = first_value(agent_text, ("name",)) or first_value(agent_text, ("agent.name",)) or "unknown"
    operator = first_value(agent_text, ("operator",)) or "there"
    greeting_name = operator.split()[0] if operator not in {"there", "unknown"} else "there"
    if args.role:
        warnings.append("Role: /role is deprecated. This session stays in Free mode. Use /project.")
    if (content / "Roles").exists():
        warnings.append("Roles: deprecated historical files. They are not this session's project. See bSmart_Protocols/roles-and-concurrency.md.")
    root = project_root(content)
    context_files = [p for p in (system / "bSmart.md", system / "bSmart_Invariants.md", agent_file,
                                  content / "bGuardrails.md") if p.is_file()]
    loaded_context: list[tuple[Path, str]] = []
    if not agent_file.is_file():
        warnings.append("Agent profile is missing; setup is required.")
    active_lines: list[str] = []
    if root is None:
        project_line = "Project (session): unavailable"
        warnings.append("Projects are currently unavailable; the project mount appears to be down.")
    else:
        project_line = "Project (session): Free mode"
        active_lines = project_catalog(root, warnings)
    for path in context_files:
        try:
            loaded_context.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError as exc:
            warnings.append(f"Context: could not read {path}: {exc}")
    print(f"Hi, {greeting_name}!")
    print("bSmart — Startup")
    print(f"Agent: {agent}")
    print(project_line)
    print("  Use: /project list | /project <project> | /project add <project> | /project help")
    print("Workstream: none")
    print("  Use: /project ws <workstream> | /project add ws <workstream> | /project help")
    print("Active projects:")
    if active_lines:
        for line in active_lines:
            print(line)
    else:
        print("  - none")
    print("Awareness: In Free mode, casual chat stays casual. When real work, decisions, or knowledge appear, suggest a matching project or creating one. If the topic matches another project's label or aliases, ask once whether to switch or only note it. Never switch silently. If the operator says stay, do not ask again.")
    print("Tags: After real work, start with one line per scope: bSmart [<scope>]: <ops> - <note of at most 5 words>. Scope is a project label, library, instance, or system. Inside a project report read, write, or delete. Outside a project report only write or delete. Do not tag log or history writes, pure chat, or web lookups.")
    print(git_status(system, "bSmart-System"))
    print(git_status(content, "bSmart-Instance"))
    print(update_line)
    for line in integrity:
        print(line)
    for warning in warnings:
        print(f"> {warning}")
    print("Context files:")
    for path in context_files:
        print(f"  - {path}")
    scoped_paths = {agent_file, content / "bGuardrails.md"}
    for path, text in loaded_context:
        if path in scoped_paths:
            print(f"--- {path} ---")
            print(text.rstrip())
    return 0 if not any("blocked" in warning.lower() for warning in warnings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
