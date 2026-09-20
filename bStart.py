#!/usr/bin/env python3
"""Deterministic bSmart session startup.

This is the tracked system entrypoint. It performs safe system freshness checks,
repairs only the agreed General-role bootstrap files, resolves one role and its
project/workstream context, and emits a compact startup payload.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
DEFAULT_WORKSPACE = SCRIPT_ROOT.parent


def now_utc() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(command: list[str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 1, "", str(exc))


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


def resolve_paths(workspace: Path) -> tuple[Path, Path]:
    system = workspace / "bSmart-System"
    content = workspace / "bSmart"
    if not system.is_dir() and SCRIPT_ROOT.is_dir():
        system = SCRIPT_ROOT
        workspace = system.parent
    if not content.exists() and Path("/workspace/bSmart").is_dir():
        content = Path("/workspace/bSmart")
    return system.resolve(), content.resolve()


def git_status(repo: Path, label: str) -> str:
    if not (repo / ".git").exists():
        return f"{label}: no Git repository"
    status = run(["git", "status", "--porcelain"], repo, 20)
    branch = run(["git", "branch", "--show-current"], repo, 20)
    if status.returncode != 0 or branch.returncode != 0:
        return f"{label}: Git status unavailable"
    dirty = bool(status.stdout.strip())
    branch_name = branch.stdout.strip() or "detached"
    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo, 20)
    if upstream.returncode != 0:
        suffix = "uncommitted changes" if dirty else "clean; no remote tracking branch"
        return f"{label}: {suffix} ({branch_name})"
    counts = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"], repo, 20)
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
    proc = run([sys.executable, str(helper), "--auto-pull"], system, 90)
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
        "bSmart_Templates/AGENTS.md", "bSmart_Templates/CLAUDE.md",
        "bSmart_Templates/role.template.md", "bSmart_Templates/current-role.template.md",
    )
    missing = [item for item in required if not (system / item).is_file()]
    if missing:
        return ["Integrity: blocked; missing system files: " + ", ".join(missing)]
    if repaired:
        return ["Integrity: OK; repaired " + ", ".join(repaired)]
    return ["Integrity: OK"]


def general_role_content(system: Path) -> str:
    template = system / "bSmart_Templates" / "role.template.md"
    if template.is_file():
        text = template.read_text(encoding="utf-8")
        replacements = {
            "<role-name>": "General",
            "<role-id>": "general",
            "<role focus>": "General operational focus",
            "<short operational focus>": "General operational focus",
            "<project-slug> | none": "none",
            "<workstream-name> | none": "none",
            "<ISO-8601 UTC timestamp>": now_utc(),
            "<short current focus>": "No active project focus.",
            "<short resume point>": "No active handoff.",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    return (
        "# General role\n\n```yaml\nrole:\n  name: General\n  id: general\nstate:\n  active_project: none\n  active_workstream: none\n  updated_at_utc: " + now_utc() + "\n```\n"
    )


def ensure_role_bootstrap(system: Path, content: Path) -> tuple[str, Path, list[str]]:
    roles = content / "Roles"
    selector = roles / "current_role.md"
    general = roles / "general_role.md"
    notes: list[str] = []
    roles.mkdir(parents=True, exist_ok=True)
    if not selector.is_file():
        selector.write_text("# bSmart current role\n\n```yaml\nrole_selection:\n  current_role: general\n  updated_at_utc: " + now_utc() + "\n```\n", encoding="utf-8")
    selected = first_value(selector.read_text(encoding="utf-8", errors="replace"), ("current_role",)) or "general"
    selected_file = roles / f"{selected}_role.md"
    if not selected_file.is_file():
        selected = "general"
        selected_file = general
        selector.write_text("# bSmart current role\n\n```yaml\nrole_selection:\n  current_role: general\n  updated_at_utc: " + now_utc() + "\n```\n", encoding="utf-8")
    if not general.is_file():
        general.write_text(general_role_content(system), encoding="utf-8")
    return selected, selected_file, notes


def project_root(content: Path) -> Path | None:
    override = os.environ.get("BSMART_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser()
        return candidate.resolve() if candidate.is_dir() and os.access(candidate, os.R_OK) else None
    for candidate in (Path("/projects"), content.parent / "projects"):
        if candidate.is_dir() and os.access(candidate, os.R_OK):
            return candidate.resolve()
    return None


def context_value(role_text: str, keys: tuple[str, ...]) -> str:
    return first_value(role_text, keys) or "none"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic bSmart session startup.")
    parser.add_argument("--root", default=str(DEFAULT_WORKSPACE))
    parser.add_argument("--role", help="select a role for this startup without changing the selector")
    parser.add_argument("--skip-update", action="store_true")
    parser.add_argument("--skip-integrity", action="store_true")
    args = parser.parse_args()
    workspace = Path(args.root).expanduser().resolve()
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
    role, role_file, role_notes = ensure_role_bootstrap(system, content)
    if args.role:
        requested = re.sub(r"[^A-Za-z0-9_-]", "", args.role)
        candidate = content / "Roles" / f"{requested}_role.md"
        if candidate.is_file():
            role, role_file = requested, candidate
        else:
            warnings.append(f"Role: requested role not found; using {role}")
    warnings.extend(role_notes)
    role_text = role_file.read_text(encoding="utf-8", errors="replace")
    project = context_value(role_text, ("active_project", "project"))
    workstream = context_value(role_text, ("active_workstream", "workstream"))
    root = project_root(content)
    project_line = f"Project: {project}"
    context_files = [p for p in (system / "bSmart.md", system / "bSmart_Invariants.md", agent_file,
                                  content / "bGuardrails.md", role_file) if p.is_file()]
    loaded_context: list[tuple[Path, str]] = []
    if not agent_file.is_file():
        warnings.append("Agent profile is missing; setup is required.")
    if root is None:
        project_line = "Project: unavailable"
        warnings.append("Projects are currently unavailable; the project mount appears to be down.")
    else:
        project_line = f"Project: {project}"
        if project != "none":
            project_dir = root / project
            project_file = project_dir / "project.md"
            if project_file.is_file():
                context_files.append(project_file)
            else:
                warnings.append(f"Project: selected project metadata not found: {project_file}")
            if workstream != "none":
                workstream_file = project_dir / "workstreams" / workstream / "README.md"
                if workstream_file.is_file():
                    context_files.append(workstream_file)
                else:
                    warnings.append(f"Workstream: selected workstream metadata not found: {workstream_file}")
    for path in context_files:
        try:
            loaded_context.append((path, path.read_text(encoding="utf-8", errors="replace")))
        except OSError as exc:
            warnings.append(f"Context: could not read {path}: {exc}")
    print(f"Hi, {greeting_name}!")
    print("bSmart — Startup")
    print(f"Agent: {agent}")
    print(f"Role: {role.title()}")
    print(f"  Use: /role list | /role set <role> | /role add <role> | /role help")
    print(project_line)
    print("  Use: /project list | /project <project> | /project add <project> | /project help")
    print(f"Workstream: {workstream}")
    print("  Use: /project ws <workstream> | /project add ws <workstream> | /project help")
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
    scoped_paths = {agent_file, content / "bGuardrails.md", role_file}
    scoped_paths.update(path for path in context_files if "/projects/" in str(path) or "/projects" in str(path.parent))
    for path, text in loaded_context:
        if path in scoped_paths:
            print(f"--- {path} ---")
            print(text.rstrip())
    return 0 if not any("blocked" in warning.lower() for warning in warnings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
