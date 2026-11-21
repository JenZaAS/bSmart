"""Knowledge layout check, safe fixes, and the one-time migration.

The command line is scripts/bKnowledgeCheck. The rules are in
bSmart_Protocols/knowledge.md. This module only does mechanical work. It
never guesses a topic for a loose note; it lists those notes so the agent
can sort them.

A knowledge root is the instance Library (<content>/Library) or a project's
knowledge/ folder. Every folder below a root is a topic. Each topic has an
index.md (an existing README.md also counts) that lists its notes and its
subtopics. The root index lists topics only. Every change made here is
appended to <root>/CHANGELOG.md.

Standard library only; runs on Linux, Windows, and macOS.
"""

from __future__ import annotations

import datetime as dt
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

INDEX_NAME = "index.md"
README_NAME = "README.md"
CHANGELOG_NAME = "CHANGELOG.md"
# Housekeeping files that may sit in a knowledge root. They are not notes.
ROOT_ALLOWLIST = frozenset({
    "README.md",
    "index.md",
    "CHANGELOG.md",
    "CATEGORIES.md",
    "task-context-routing.md",
})
DEFAULT_TOPICS = ("code", "tools", "general")
DEFAULT_DESCRIPTIONS = {
    "code": "language-agnostic code notes; one subfolder per language, such as code/<language>/",
    "tools": "apps, services, and external references; one subfolder each",
    "general": "last resort when no better topic fits; move notes out when a topic appears",
}
# code/ itself may hold language-agnostic notes. tools/ and general/ hold
# topic subfolders only.
NO_LOOSE_NOTES = frozenset({"tools", "general"})
NOTE_SUFFIXES = frozenset({".md"})
SKIP_DIRS = frozenset({"__pycache__", "node_modules"})
NESTED_ROOT_NAME = "knowledge"
PLACEHOLDER = "TODO: one-line description"
MIGRATION_STATE = "knowledge-migration.yaml"
MIGRATION_VERSION = 1

LINK = re.compile(r"\[([^\]]*)\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

KIND_HINTS = {
    "root_file": "note directly in a knowledge root; move it into a topic folder (your call)",
    "default_root_file": "note directly in tools/ or general/; move it into a topic subfolder (your call)",
    "nested_root": "knowledge/ folder inside a knowledge root; its content belongs in the root (--migrate moves it)",
    "missing_index": "topic folder without index.md or README.md (--fix creates index.md)",
    "unindexed": "not listed in its folder's index (--fix adds a line with a placeholder)",
    "broken_link": "index link to a missing file (--fix removes it)",
    "general_note": "note under general/; recategorise it when a better topic fits",
    "placeholder": "index line still has the placeholder description; write one line",
}
FIXABLE = frozenset({"missing_index", "unindexed", "broken_link"})
# Advisory findings are listed but do not change the exit code or the startup line:
# a note may stay in general/ when no better topic exists yet.
ADVISORY = frozenset({"general_note"})


@dataclass
class Finding:
    kind: str
    root: Path
    path: Path

    @property
    def rel(self) -> str:
        try:
            value = self.path.relative_to(self.root).as_posix()
        except ValueError:
            value = self.path.as_posix()
        if self.path.is_dir() and value != ".":
            value += "/"
        return value

    @property
    def fixable(self) -> bool:
        return self.kind in FIXABLE

    @property
    def advisory(self) -> bool:
        return self.kind in ADVISORY


@dataclass
class RootReport:
    label: str
    root: Path
    findings: list[Finding] = field(default_factory=list)
    changes: list[str] = field(default_factory=list)
    partial: bool = False

    @property
    def problems(self) -> list[Finding]:
        return [f for f in self.findings if not f.advisory]


class Budget:
    """Stop walking after a time or entry limit, so a slow disk cannot stall startup."""

    def __init__(self, seconds: float | None = None, entries: int | None = None):
        self.deadline = time.monotonic() + seconds if seconds else None
        self.entries_left = entries
        self.exhausted = False

    def spend(self, count: int = 1) -> bool:
        if self.exhausted:
            return False
        if self.entries_left is not None:
            self.entries_left -= count
            if self.entries_left < 0:
                self.exhausted = True
        if self.deadline is not None and time.monotonic() > self.deadline:
            self.exhausted = True
        return not self.exhausted


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def hidden(name: str) -> bool:
    return name.startswith(".") or name in SKIP_DIRS


def list_dir(path: Path, budget: Budget | None = None) -> tuple[list[Path], list[Path]]:
    """(subfolders, files), sorted, hidden entries left out."""
    dirs: list[Path] = []
    files: list[Path] = []
    try:
        with os.scandir(path) as entries:
            for entry in entries:
                if hidden(entry.name):
                    continue
                if budget is not None:
                    budget.spend()
                try:
                    if entry.is_dir(follow_symlinks=False):
                        dirs.append(Path(entry.path))
                    elif entry.is_file():
                        files.append(Path(entry.path))
                except OSError:
                    continue
    except OSError:
        return [], []
    return sorted(dirs, key=lambda p: p.name.lower()), sorted(files, key=lambda p: p.name.lower())


def is_note(path: Path) -> bool:
    return path.suffix.lower() in NOTE_SUFFIXES and path.name not in (INDEX_NAME, README_NAME)


def index_files(folder: Path) -> list[Path]:
    return [p for p in (folder / INDEX_NAME, folder / README_NAME) if p.is_file()]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def is_topic(folder: Path, budget: Budget | None = None) -> bool:
    """A folder is a topic when it has an index, a note, or a subfolder.

    A folder of attachments only (images, PDFs) is not a topic and needs no index.
    """
    dirs, files = list_dir(folder, budget)
    if dirs:
        return True
    return any(p.suffix.lower() in NOTE_SUFFIXES for p in files)


def mentioned(text: str, name: str, folder: bool) -> bool:
    """True when an index already lists this child, as a link or by name."""
    escaped = re.escape(name)
    if folder:
        pattern = rf"(?:^|[\s(\[`'\"/])(?:\./)?{escaped}(?:/|\)|`)"
    else:
        pattern = rf"(?:^|[\s(\[`'\"/])(?:\./)?{escaped}(?:$|[\s)\]`'\"#?,;:])"
    return re.search(pattern, text, re.MULTILINE) is not None


def link_targets(text: str) -> list[tuple[int, str, str]]:
    """(line number, full match, target) for each relative link."""
    found = []
    for number, line in enumerate(text.splitlines()):
        for match in LINK.finditer(line):
            target = match.group(2)
            if target.startswith(("#", "/", "\\")) or SCHEME.match(target):
                continue
            found.append((number, match.group(0), target))
    return found


def resolve_target(folder: Path, target: str) -> Path:
    clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
    return folder / clean


def broken_links(index: Path) -> list[str]:
    folder = index.parent
    return [target for _, _, target in link_targets(read_text(index))
            if target.split("#", 1)[0] and not resolve_target(folder, target).exists()]


def check_root(root: Path, label: str, budget: Budget | None = None) -> RootReport:
    report = RootReport(label=label, root=root)
    if not root.is_dir():
        return report
    findings = report.findings

    def visit(folder: Path, depth: int) -> None:
        if budget is not None and budget.exhausted:
            report.partial = True
            return
        dirs, files = list_dir(folder, budget)
        topics = [d for d in dirs if is_topic(d, budget)]
        rel_parts = folder.relative_to(root).parts
        if depth == 0:
            for path in files:
                if path.name not in ROOT_ALLOWLIST:
                    findings.append(Finding("root_file", root, path))
            for d in dirs:
                if d.name == NESTED_ROOT_NAME:
                    findings.append(Finding("nested_root", root, d))
        elif depth == 1 and folder.name in NO_LOOSE_NOTES:
            for path in files:
                if is_note(path):
                    findings.append(Finding("default_root_file", root, path))
        if len(rel_parts) > 1 and rel_parts[0] == "general":
            for path in files:
                if is_note(path):
                    findings.append(Finding("general_note", root, path))
        indexes = index_files(folder)
        if depth > 0 or topics:
            if not indexes:
                if depth == 0 or is_topic(folder, budget):
                    findings.append(Finding("missing_index", root, folder))
            else:
                text = "\n".join(read_text(p) for p in indexes)
                children: list[tuple[Path, bool]] = [
                    (d, True) for d in topics if not (depth == 0 and d.name == NESTED_ROOT_NAME)]
                if depth > 0:
                    children += [(p, False) for p in files if is_note(p)]
                for child, is_folder in children:
                    if not mentioned(text, child.name, is_folder):
                        findings.append(Finding("unindexed", root, child))
                for index in indexes:
                    for target in broken_links(index):
                        findings.append(Finding("broken_link", root, index.parent / target.split("#", 1)[0]))
                    if PLACEHOLDER in read_text(index):
                        findings.append(Finding("placeholder", root, index))
        for d in dirs:
            if d.name == NESTED_ROOT_NAME and depth == 0:
                continue
            visit(d, depth + 1)

    visit(root, 0)
    if budget is not None and budget.exhausted:
        report.partial = True
    return report


# ---------------------------------------------------------------- fixes

def template_text(system_root: Path | None, name: str) -> str | None:
    if system_root is None:
        return None
    path = system_root / "bSmart_Templates" / name
    return read_text(path) if path.is_file() else None


ENTRIES_MARKER = "<!-- entries -->"


def render_index(system_root: Path | None, top: bool, title: str, readme: bool) -> str:
    name = "knowledge-index.template.md" if top else "knowledge-topic-index.template.md"
    text = template_text(system_root, name)
    if text and ENTRIES_MARKER in text:
        head = text.split(ENTRIES_MARKER, 1)[0].replace("<topic>", title).rstrip() + "\n"
    elif top:
        head = (f"# {title} index\n\nTopics only, one line each. Each topic has its own index.md.\n"
                "Rules: bSmart_Protocols/knowledge.md.\n")
    else:
        head = f"# {title}\n\nOne line per note or subtopic.\n"
    if readme:
        head += f"\nOverview: [{README_NAME}]({README_NAME})\n"
    return head + "\n"


def entry_line(child: Path, is_folder: bool, top: bool) -> str:
    if is_folder:
        target = f"{child.name}/{INDEX_NAME}"
        if not (child / INDEX_NAME).is_file() and (child / README_NAME).is_file():
            target = f"{child.name}/{README_NAME}"
        description = DEFAULT_DESCRIPTIONS.get(child.name) if top else None
        return f"- [{child.name}/]({target}) - {description or PLACEHOLDER}"
    return f"- [{child.stem}]({child.name}) - {PLACEHOLDER}"


def append_log(root: Path, lines: list[str], source: str) -> None:
    if not lines:
        return
    log = root / CHANGELOG_NAME
    stamp = utc_stamp()
    header = "" if log.is_file() else (
        "# Knowledge change log\n\n"
        "Every change to this knowledge tree by bKnowledgeCheck or an agent's cleanup, newest last.\n\n"
    )
    with log.open("a", encoding="utf-8", newline="\n") as handle:
        if header:
            handle.write(header)
        for line in lines:
            handle.write(f"- {stamp} {source}: {line}\n")


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def remove_broken_links(index: Path, root: Path, changes: list[str]) -> None:
    """index.md: drop list lines whose link is broken. README.md: keep the text, drop the link."""
    text = read_text(index)
    lines = text.splitlines(keepends=True)
    folder = index.parent
    changed = False
    out: list[str] = []
    for line in lines:
        new = line
        drop = False
        for match in list(LINK.finditer(line)):
            target = match.group(2)
            if target.startswith(("#", "/", "\\")) or SCHEME.match(target) or not target.split("#", 1)[0]:
                continue
            if resolve_target(folder, target).exists():
                continue
            changes.append(f"removed broken link {target} from {rel(root, index)}")
            changed = True
            if index.name == INDEX_NAME and LIST_ITEM.match(line):
                drop = True
                break
            new = new.replace(match.group(0), match.group(1))
        if not drop:
            out.append(new)
    if changed:
        index.write_text("".join(out), encoding="utf-8", newline="")


def fix_root(root: Path, system_root: Path | None, source: str = "bKnowledgeCheck --fix") -> list[str]:
    """Safe mechanical fixes only. Returns the change lines, also logged."""
    changes: list[str] = []
    if not root.is_dir():
        return changes

    def visit(folder: Path, depth: int) -> None:
        dirs, files = list_dir(folder)
        for d in dirs:
            if d.name == NESTED_ROOT_NAME and depth == 0:
                continue
            visit(d, depth + 1)  # children first, so their index exists before the parent links it
        topics = [d for d in dirs if is_topic(d) and not (d.name == NESTED_ROOT_NAME and depth == 0)]
        notes = [p for p in files if is_note(p)] if depth > 0 else []
        if depth > 0 and not topics and not notes and not index_files(folder):
            return  # attachments only, or empty: not a topic
        if depth == 0 and not topics and not index_files(folder):
            return  # empty root: nothing to index yet
        index = folder / INDEX_NAME
        readme = folder / README_NAME
        if not index.is_file() and not readme.is_file():
            title = "Knowledge" if depth == 0 else folder.name
            index.write_text(render_index(system_root, depth == 0, title, False), encoding="utf-8", newline="\n")
            changes.append(f"created {rel(root, index)}")
        for existing in index_files(folder):
            remove_broken_links(existing, root, changes)
        text = "\n".join(read_text(p) for p in index_files(folder))
        missing = [(d, True) for d in topics if not mentioned(text, d.name, True)]
        missing += [(p, False) for p in notes if not mentioned(text, p.name, False)]
        if not missing:
            return
        if not index.is_file():
            # Leave a hand-written README.md alone; the new index.md points to it.
            title = "Knowledge" if depth == 0 else folder.name
            index.write_text(render_index(system_root, depth == 0, title, True), encoding="utf-8", newline="\n")
            changes.append(f"created {rel(root, index)} (points to {README_NAME})")
        body = read_text(index)
        if body and not body.endswith("\n"):
            body += "\n"
        for child, is_folder in missing:
            body += entry_line(child, is_folder, depth == 0) + "\n"
            changes.append(f"indexed {rel(root, child)}{'/' if is_folder else ''} in {rel(root, index)}")
        index.write_text(body, encoding="utf-8", newline="\n")

    visit(root, 0)
    append_log(root, changes, source)
    return changes


# ------------------------------------------------------------- migration

def move_up_nested(root: Path, changes: list[str], conflicts: list[str]) -> None:
    """Move <root>/knowledge/* into <root>. Never overwrite; report conflicts."""
    nested = root / NESTED_ROOT_NAME
    if not nested.is_dir():
        return

    def merge(src: Path, dst: Path) -> None:
        for item in sorted(src.iterdir(), key=lambda p: p.name):
            target = dst / item.name
            if not target.exists():
                item.rename(target)
                changes.append(f"moved {rel(root, item)} to {rel(root, target)}")
            elif item.is_dir() and target.is_dir():
                merge(item, target)
            elif item.is_file() and target.is_file() and item.read_bytes() == target.read_bytes():
                item.unlink()
                changes.append(f"removed duplicate {rel(root, item)} (same as {rel(root, target)})")
            else:
                conflicts.append(rel(root, item))
        try:
            src.rmdir()
        except OSError:
            pass

    merge(nested, root)


def ensure_defaults(root: Path, system_root: Path | None, changes: list[str]) -> None:
    for name in DEFAULT_TOPICS:
        folder = root / name
        if not folder.exists():
            folder.mkdir(parents=True)
            changes.append(f"created {name}/")
        if folder.is_dir() and not index_files(folder):
            (folder / INDEX_NAME).write_text(render_index(system_root, False, name, False),
                                             encoding="utf-8", newline="\n")
            changes.append(f"created {name}/{INDEX_NAME}")


def migrate_root(root: Path, label: str, system_root: Path | None) -> tuple[list[str], list[str], RootReport]:
    changes: list[str] = []
    conflicts: list[str] = []
    move_up_nested(root, changes, conflicts)
    ensure_defaults(root, system_root, changes)
    append_log(root, changes, "knowledge migration")
    changes += fix_root(root, system_root, "knowledge migration")
    report = check_root(root, label)
    return changes, conflicts, report


def state_path(content_root: Path) -> Path:
    return content_root / "State" / MIGRATION_STATE


def read_state(content_root: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in read_text(state_path(content_root)).splitlines():
        if ":" in line and not line.startswith((" ", "-", "#")):
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data


def migration_done(content_root: Path) -> bool:
    state = read_state(content_root)
    return state.get("status") == "done" and state.get("version", "") == str(MIGRATION_VERSION)


def write_state(content_root: Path, status: str, pending: list[str]) -> None:
    path = state_path(content_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"version: {MIGRATION_VERSION}",
        f"status: {status}",
        f"updated: {utc_stamp()}",
        "pending:" if pending else "pending: []",
    ]
    lines += [f"  - {item}" for item in pending]
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


# ------------------------------------------------------------- discovery

def knowledge_roots(content_root: Path | None, projects_root: Path | None,
                    project: str | None = None, budget: Budget | None = None) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    if content_root is not None and project is None:
        library = content_root / "Library"
        if library.is_dir():
            roots.append(("library", library))
    if projects_root is not None and projects_root.is_dir():
        if project:
            candidate = projects_root / project / "knowledge"
            if candidate.is_dir():
                roots.append((f"project {project}", candidate))
        else:
            dirs, _ = list_dir(projects_root, budget)
            for d in dirs:
                candidate = d / "knowledge"
                if candidate.is_dir():
                    roots.append((f"project {d.name}", candidate))
    return roots
