#!/usr/bin/env python3
"""Session-scoped project index, startup self-check, and role migration.

The active project is not stored here. This module owns the shared project
index, handoff migration, and the backup that makes that migration reversible.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import uuid
from pathlib import Path

INDEX_NAME = "INDEX.md"
INDEX_HEADER = "name | label | aliases | description | status"
INDEX_INTRO = """# bSmart project index
#
# Only /project commands write this file. bStart may create it when it is missing.
#
"""

_BLANK = {
    "",
    "none",
    "null",
    "unspecified",
    "no active project focus.",
    "no active handoff.",
    "review legacy state",
}
_PROJECT_KEYS = ("active_project", "active project (short name)", "project")
_WORKSTREAM_KEYS = ("active_workstream", "active workstream", "workstream")
_FOCUS_KEYS = ("current_focus", "active focus", "focus")
_HANDOFF_KEYS = ("task_handoff", "task handoff", "handoff")
_KNOWN = {*_PROJECT_KEYS, *_WORKSTREAM_KEYS, *_FOCUS_KEYS, *_HANDOFF_KEYS, "updated_at_utc", "updated at (utc)", "name", "id", "mode", "file", "status", "startup_selection", "default_role", "role_focus"}


def short_label(name: str) -> str:
    """Provisional tag label. DigSoftware -> DS. A single word keeps four letters."""
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+", name)
    if len(parts) >= 2:
        letters = "".join(part[0] for part in parts if part[:1].isalnum())
    else:
        letters = re.sub(r"[^A-Za-z0-9]", "", name)[:4]
    return (letters or "P").upper()[:6]


def child_dirs(root: Path) -> list[str]:
    names: list[str] = []
    if not root.is_dir():
        return names
    for child in root.iterdir():
        if child.name.startswith("."):
            continue
        try:
            if child.is_symlink() or not child.is_dir():
                continue
        except OSError:
            continue
        names.append(child.name)
    return sorted(names)


def _clean(value: str) -> str:
    text = value.strip().strip('"').strip("'").strip("`")
    return text.replace("|", "/").replace("\n", " ")


def describe_folder(folder: Path) -> tuple[str, str]:
    description = ""
    status = "active"
    meta = folder / "project.md"
    if not meta.is_file():
        return description, status
    try:
        text = meta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return description, status
    for line in text.splitlines():
        status_match = re.match(r"^status:\s*(\S+)\s*$", line.strip(), re.I)
        if status_match and status_match.group(1).lower() in {"active", "archived"}:
            status = status_match.group(1).lower()
        objective = re.match(r"^objective:\s*(.+?)\s*$", line.strip(), re.I)
        if objective:
            value = _clean(objective.group(1))
            if value.lower() not in {"", "unspecified"}:
                description = value[:80]
    return description, status


def parse_index(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == INDEX_HEADER or "|" not in stripped:
            continue
        parts = [part.strip() for part in stripped.split("|")]
        if len(parts) != 5:
            rows.append({"invalid": True, "raw": stripped})
            continue
        name, label, aliases, description, status = parts
        rows.append({
            "name": name,
            "label": label,
            "aliases": [item.strip() for item in aliases.split(";") if item.strip()],
            "description": description,
            "status": status,
            "invalid": not name or status not in {"active", "archived"},
        })
    return rows


def format_row(row: dict) -> str:
    if row.get("invalid"):
        return str(row.get("raw", ""))
    aliases = "; ".join(row.get("aliases") or [])
    return f"{row['name']} | {row['label']} | {aliases} | {row.get('description', '')} | {row['status']}"


def render_index(rows: list[dict]) -> str:
    body = "\n".join(format_row(row) for row in rows)
    suffix = "\n" if body else ""
    return f"{INDEX_INTRO}{INDEX_HEADER}\n{body}{suffix}"


def assign_labels(rows: list[dict]) -> None:
    used = {row["label"].upper() for row in rows if not row.get("invalid") and row.get("label")}
    for row in rows:
        if row.get("invalid") or row.get("label"):
            continue
        base = short_label(row["name"])
        label = base
        number = 2
        while label.upper() in used:
            label = f"{base}{number}"[:8]
            number += 1
        row["label"] = label
        used.add(label.upper())


def generated_rows(root: Path) -> list[dict]:
    rows = []
    for name in child_dirs(root):
        description, status = describe_folder(root / name)
        rows.append({
            "name": name,
            "label": "",
            "aliases": [],
            "description": description,
            "status": status,
            "invalid": False,
        })
    assign_labels(rows)
    return rows


def read_index(root: Path) -> list[dict] | None:
    path = root / INDEX_NAME
    if not path.is_file():
        return None
    return parse_index(path.read_text(encoding="utf-8", errors="replace"))


def write_index(root: Path, rows: list[dict]) -> None:
    path = root / INDEX_NAME
    path.write_text(render_index(rows), encoding="utf-8")


def self_check(root: Path, rows: list[dict]) -> list[str]:
    warnings: list[str] = []
    folders = set(child_dirs(root))
    seen: dict[str, dict] = {}
    labels: dict[str, str] = {}
    for row in rows:
        if row.get("invalid"):
            warnings.append(f"Index line is invalid: {row.get('raw', row.get('name', ''))}")
            continue
        if row["name"] in seen:
            warnings.append(f"Duplicate index name: {row['name']}")
        seen[row["name"]] = row
        label = row.get("label", "").upper()
        if label:
            if label in labels:
                warnings.append(f"Duplicate label {row['label']} on {labels[label]} and {row['name']}")
            else:
                labels[label] = row["name"]
        if row.get("status") == "active" and row["name"] not in folders:
            warnings.append(f"Active project {row['name']} has no folder")
        if row.get("status") == "archived" and row["name"] in folders:
            warnings.append(f"Archived project {row['name']} still has a folder")
    for folder in sorted(folders):
        if folder not in seen:
            warnings.append(f"Folder {folder} is not in the index")
    return warnings


def ensure_index(root: Path) -> tuple[list[dict], bool]:
    """Return rows and whether a missing index was created. Do not rewrite a present index."""
    existing = read_index(root)
    if existing is not None:
        return existing, False
    rows = generated_rows(root)
    write_index(root, rows)
    return rows, True


def repair_index(root: Path, rows: list[dict]) -> list[str]:
    """Add lines for folders the index does not name. Do not delete or rewrite existing lines."""
    present = {row["name"] for row in rows if not row.get("invalid")}
    added: list[str] = []
    for name in child_dirs(root):
        if name in present:
            continue
        description, status = describe_folder(root / name)
        rows.append({
            "name": name,
            "label": "",
            "aliases": [],
            "description": description,
            "status": status,
            "invalid": False,
        })
        added.append(name)
    if added:
        assign_labels(rows)
        write_index(root, rows)
    return added


def active_rows(rows: list[dict]) -> list[dict]:
    return [row for row in rows if not row.get("invalid") and row.get("status") == "active"]


def _blank(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().strip('"').strip("'").strip("`").lower() in _BLANK


def _unquote(value: str) -> str:
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'", "`"}:
        return text[1:-1]
    return text


def _add(found: dict[str, list[str]], key: str, value: str) -> None:
    cleaned = _unquote(value).strip()
    if cleaned == "":
        return
    found.setdefault(key.lower(), []).append(cleaned)


def extract_fields(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for line in text.splitlines():
        bullet = re.match(r"^-\s*([^:`]+):\s*(.*?)\s*$", line.strip())
        if bullet:
            _add(found, bullet.group(1), bullet.group(2))
            continue
        field = re.match(r"^([A-Za-z0-9_ ()-]+):\s*(.*?)\s*$", line.strip())
        if field and not line.strip().startswith("#"):
            _add(found, field.group(1), field.group(2))
    return found


def _one(found: dict[str, list[str]], keys: tuple[str, ...]) -> tuple[str | None, bool]:
    values: list[str] = []
    for key in keys:
        values.extend(found.get(key, []))
    distinct = list(dict.fromkeys(values))
    if not distinct:
        return None, False
    if len(distinct) > 1:
        return distinct[0], True
    return distinct[0], False


def _unknown(found: dict[str, list[str]]) -> list[str]:
    lines = []
    for key, values in found.items():
        if key in _KNOWN:
            continue
        for value in values:
            lines.append(f"{key}: {value}")
    return lines


def _section(source: str, project: str, workstream: str | None, focus: str | None, handoff: str | None) -> str:
    lines = [f"## Migrated from {source}", "", f"- active_project: {project}"]
    if workstream and not _blank(workstream):
        lines.append(f"- active_workstream: {workstream}")
    if focus and not _blank(focus):
        lines.append(f"- current_focus: {focus}")
    if handoff and not _blank(handoff):
        lines.append(f"- task_handoff: {handoff}")
    return "\n".join(lines)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def migration_marker(workspace: Path) -> Path:
    return workspace / "bSmart" / "State" / "role-migration.json"


def _read_utf8(path: Path) -> str:
    """Read UTF-8 text. A legacy code page raises UnicodeDecodeError instead of crashing later."""
    return path.read_bytes().decode("utf-8")


def _chmod_writable(path: Path) -> None:
    try:
        os.chmod(path, path.stat().st_mode | stat.S_IWRITE | stat.S_IREAD)
    except OSError:
        pass


def _on_remove_error(func, path, _exc) -> None:
    _chmod_writable(Path(path))
    func(path)


def _rmtree_error_kwargs(version: tuple[int, ...] | None = None) -> dict:
    """3.12+ uses onexc. 3.11 and older only accept onerror."""
    current = sys.version_info if version is None else version
    if current >= (3, 12):
        return {"onexc": _on_remove_error}
    return {"onerror": _on_remove_error}


def _remove_tree(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        _chmod_writable(path)
        path.unlink()
        return
    if not path.exists():
        return
    shutil.rmtree(path, **_rmtree_error_kwargs())


def _swap_tree(source: Path, dest: Path) -> None:
    """Copy source beside dest, then rename into place. Do not delete dest first."""
    parent = dest.parent
    parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging = parent / f".{dest.name}.incoming-{token}"
    previous = parent / f".{dest.name}.previous-{token}"
    if staging.exists() or staging.is_symlink():
        _remove_tree(staging)
    _copy_exact(source, staging)
    replaced = False
    try:
        if dest.exists() or dest.is_symlink():
            _chmod_writable(dest)
            os.replace(dest, previous)
        os.replace(staging, dest)
        replaced = True
    finally:
        if not replaced and (previous.exists() or previous.is_symlink()) and not (dest.exists() or dest.is_symlink()):
            os.replace(previous, dest)
        if staging.exists() or staging.is_symlink():
            _remove_tree(staging)
    if previous.exists() or previous.is_symlink():
        _remove_tree(previous)


def _write_manifest(stamp_root: Path, manifest: dict) -> None:
    (stamp_root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _copy_exact(source: Path, dest: Path) -> None:
    if source.is_symlink():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.is_symlink() or dest.exists():
            dest.unlink()
        os.symlink(os.readlink(source), dest)
        return
    if source.is_dir():
        shutil.copytree(source, dest, symlinks=True, copy_function=shutil.copy2)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)


def migrate_workspace(workspace: Path, backup: Path, projects_root: Path | None = None) -> list[str]:
    """Back up Roles and legacy state, then merge unambiguous handoffs.

    Ambiguous roles are reported and left unread as selection. Nothing here
    writes a shared current-project selector. A marker makes a later run a no-op.
    The manifest is written before any handoff is modified.
    """
    content = workspace / "bSmart"
    roles = content / "Roles"
    legacy = content / "bSmart_State.md"
    marker = migration_marker(workspace)
    if marker.is_file():
        report = ["role_migration: already migrated", f"role_migration: marker {marker}"]
        try:
            saved = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            saved = {}
        report.extend(str(line) for line in saved.get("questions") or [])
        return report
    report = ["role_migration: started"]
    if not roles.exists() and not legacy.is_file():
        report.append("role_migration: nothing to migrate")
        return report

    stamp_root = backup / "roles-migration"
    stamp_root.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"roles": False, "legacy": False, "handoffs": []}
    if roles.exists():
        _copy_exact(roles, stamp_root / "Roles")
        manifest["roles"] = True
        report.append(f"role_migration: backup {stamp_root / 'Roles'}")
    if legacy.is_file():
        _copy_exact(legacy, stamp_root / "bSmart_State.md")
        manifest["legacy"] = True
        report.append(f"role_migration: backup {stamp_root / 'bSmart_State.md'}")

    if projects_root is None:
        script_dir = Path(__file__).absolute().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from bsmart_instance import select_instance_project_root

        projects_root = select_instance_project_root(workspace)

    sources: list[tuple[str, Path]] = []
    if roles.is_dir():
        for path in sorted(roles.glob("*_role.md")):
            if path.name == "current_role.md":
                continue
            sources.append((path.stem[: -len("_role")] if path.stem.endswith("_role") else path.stem, path))
    if legacy.is_file():
        sources.append(("bSmart_State.md", legacy))

    handoff_backup = stamp_root / "handoffs"
    touched: list[dict] = []
    planned: list[dict] = []
    review: list[str] = []
    for source_name, path in sources:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            report.append(f"role_migration: blocked: cannot read {path}: {exc}")
            continue
        found = extract_fields(text)
        project, project_conflict = _one(found, _PROJECT_KEYS)
        workstream, workstream_conflict = _one(found, _WORKSTREAM_KEYS)
        focus, focus_conflict = _one(found, _FOCUS_KEYS)
        handoff, handoff_conflict = _one(found, _HANDOFF_KEYS)
        unknown = _unknown(found)
        label = source_name
        if unknown:
            review.extend([f"## {label}", ""])
            review.extend(f"- {item}" for item in unknown)
            review.append("")
        if project_conflict or workstream_conflict or focus_conflict or handoff_conflict:
            report.append(f"role_migration: question: {label} has conflicting project, workstream, focus, or handoff values. Which value should be kept?")
            continue
        if _blank(project):
            if _blank(focus) and _blank(handoff) and not unknown:
                report.append(f"role_migration: skipped {label} (no project state)")
                continue
            report.append(f"role_migration: question: {label} has focus, handoff, or unknown fields but no project. Where should they go?")
            continue
        if projects_root is None or not projects_root.is_dir():
            report.append(f"role_migration: question: {label} names project {project}, but no projects root is available. Where should the handoff be written?")
            continue
        project_dir = projects_root / project
        if not project_dir.is_dir() or project_dir.is_symlink():
            report.append(f"role_migration: question: {label} names project {project}, which has no folder. Create it, or name the right project?")
            continue
        if workstream and not _blank(workstream):
            stream = project_dir / "workstreams" / workstream
            if not stream.is_dir() or stream.is_symlink():
                report.append(f"role_migration: question: {label} names workstream {workstream} under {project}, which has no folder. Create it, or migrate to the project handoff?")
                continue
            destination = stream / "handoff.md"
            relative = Path(project) / "workstreams" / workstream / "handoff.md"
        else:
            destination = project_dir / "handoff.md"
            relative = Path(project) / "handoff.md"
            workstream = None
        relative_key = relative.as_posix()
        if not any(item["relative"] == relative_key for item in touched):
            stored = handoff_backup / relative
            if destination.is_file():
                stored.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, stored)
            touched.append({"relative": relative_key, "existed": destination.is_file()})
        planned.append({
            "label": label,
            "project": project,
            "workstream": workstream,
            "focus": focus,
            "handoff": handoff,
            "destination": destination,
            "relative": relative_key,
        })

    if review:
        review_text = "# Role fields preserved for review\n\nThese lines were not copied into project handoff files.\n\n" + "\n".join(review)
        (stamp_root / "review.md").write_text(review_text, encoding="utf-8")
        review_path = content / "State" / "role-migration-review.md"
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(review_text, encoding="utf-8")
        report.append(f"role_migration: review {review_path}")

    manifest["handoffs"] = touched
    _write_manifest(stamp_root, manifest)

    for action in planned:
        destination = action["destination"]
        relative_key = action["relative"]
        item = next(entry for entry in touched if entry["relative"] == relative_key)
        try:
            prior = _read_utf8(destination) if destination.is_file() else f"# Handoff\n\nProject: {action['project']}\n"
        except UnicodeDecodeError:
            report.append(
                f"role_migration: question: {action['label']} handoff {relative_key} is not UTF-8. "
                "It was left unchanged. The backup has the original bytes."
            )
            continue
        except OSError as exc:
            report.append(f"role_migration: blocked: cannot read {destination}: {exc}")
            continue
        section = _section(action["label"], action["project"], action["workstream"], action["focus"], action["handoff"])
        if section.strip() not in prior:
            payload = (prior.rstrip() + "\n\n" + section.strip() + "\n").encode("utf-8")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
        if destination.is_file():
            item["written_sha256"] = _sha256_file(destination)
        _write_manifest(stamp_root, manifest)
        report.append(f"role_migration: migrated {action['label']} -> {relative_key}")

    questions = [line for line in report if ": question:" in line]
    blocked = [line for line in report if ": blocked:" in line]
    if questions:
        report.append(f"role_migration: {len(questions)} question(s); those roles were not migrated")
    else:
        report.append("role_migration: complete")
    report.append("role_migration: Roles/ is historical and is not a session selector")
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "marker": "session-projects-0.1.45",
        "backup": str(stamp_root),
        "questions": questions + blocked,
    }, indent=2) + "\n", encoding="utf-8")
    report.append(f"role_migration: marker {marker}")
    return report


def restore_workspace(workspace: Path, backup: Path, projects_root: Path | None = None) -> list[str]:
    """Put Roles and legacy state back. Restore a handoff only when it still matches migration."""
    stamp_root = backup / "roles-migration" if (backup / "roles-migration").is_dir() else backup
    manifest_path = stamp_root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"role migration manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content = workspace / "bSmart"
    report = [f"role_migration: restoring {stamp_root}"]
    roles_dest = content / "Roles"
    if manifest.get("roles"):
        _swap_tree(stamp_root / "Roles", roles_dest)
        report.append(f"role_migration: restored {roles_dest}")
    if manifest.get("legacy"):
        _copy_exact(stamp_root / "bSmart_State.md", content / "bSmart_State.md")
        report.append("role_migration: restored bSmart_State.md")
    if projects_root is None:
        script_dir = Path(__file__).absolute().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        from bsmart_instance import select_instance_project_root

        projects_root = select_instance_project_root(workspace)
    for item in manifest.get("handoffs", []):
        relative = Path(item["relative"])
        if projects_root is None:
            report.append(f"role_migration: blocked: cannot restore handoff without a projects root: {relative.as_posix()}")
            continue
        destination = projects_root / relative
        stored = stamp_root / "handoffs" / relative
        current_hash = _sha256_file(destination) if destination.is_file() else None
        expected = item.get("written_sha256")
        if destination.is_file() and expected and current_hash != expected:
            kept = stamp_root / "handoffs-kept" / relative
            kept.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, kept)
            report.append(f"role_migration: kept {relative.as_posix()} because it changed after migration; copy {kept}")
            continue
        if destination.is_file() and not expected and stored.is_file() and current_hash != _sha256_file(stored):
            report.append(f"role_migration: kept {relative.as_posix()} because migration did not finish writing it")
            continue
        if item.get("existed"):
            if not stored.is_file():
                report.append(f"role_migration: blocked: backup handoff missing: {stored}")
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stored, destination)
        elif destination.is_file():
            _chmod_writable(destination)
            destination.unlink()
        report.append(f"role_migration: restored handoff {relative.as_posix()}")
    marker = migration_marker(workspace)
    if marker.is_file():
        _chmod_writable(marker)
        marker.unlink()
        report.append(f"role_migration: removed marker {marker}")
    report.append("role_migration: restore complete")
    return report
