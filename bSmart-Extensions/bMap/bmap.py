#!/usr/bin/env python3
"""bMap helper: lint, status, and map finding for local-markdown bMap maps.

Standard library only. Works on Linux, Windows, and macOS.

The checks are inspired by John Goh's wayfinder-maps linter (MIT). This file
is a separate implementation written for bSmart; it copies no code.

Commands:
  bmap.py lint <map-dir | maps-root>     check one map, or a registry and all its maps
  bmap.py status <map-dir>               resolved, claimed, open, and the frontier
  bmap.py find <maps-root> [words...] [--slug SLUG]
                                         find the right map; ask instead of guessing

Exit codes: 0 clean or found, 1 errors found or a question to ask, 2 nothing at that path.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

MAP_FILE = "map.md"
REGISTRY_FILE = "REGISTRY.md"
TICKET_TYPES = ("research", "prototype", "explore", "task")
# Old names for an explore ticket. They are errors, so no map keeps a second name.
OLD_TYPE_NAMES = {"discussion": "explore", "grilling": "explore"}
HUMAN_TYPES = ("explore", "prototype")  # the human decides these, never the agent
TRACKERS = ("local", "github")
REGISTRY_STATUSES = ("active", "paused", "done")
STALE_CLAIM_HOURS = 72
MAX_TICKETS = 12  # per map, out-of-scope tickets not counted
NEAR_LIMIT = 10

RE_TICKET_FILE = re.compile(r"^(\d+)-[A-Za-z0-9._-]+\.md$")
RE_TICKET_LINK = re.compile(r"\(\./tickets/(\d+)-[^)]*\)")
RE_FOG_TITLE = re.compile(r"^\s*[-*]\s+\*\*(.+?)\*\*")
RE_CLEARS = re.compile(r"<clears-with:\s*(\d+)\s*>")
RE_FENCE = re.compile(r"^\s*(```|~~~)")
RE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
RE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# A map may never switch the no-build rule off. Only the human can, in the session.
FORBIDDEN_MAP_KEYS = ("build_allowed", "allow_build", "execution", "build", "mode")
RE_OVERRIDE = re.compile(
    r"carr(?:y|ies)\s+execution|build(?:ing)?\s+(?:is\s+)?(?:allowed|permitted|ok)"
    r"|(?:may|can)\s+(?:write|build|ship)\s+(?:production\s+)?code"
    r"|override\s+(?:the\s+)?(?:plan|no[- ]build)|execution\s+(?:is\s+)?allowed",
    re.IGNORECASE,
)
RE_BUILD_TITLE = re.compile(r"^(build|implement|code|deploy|ship|write the code|refactor)\b", re.IGNORECASE)
STOPWORDS = {"the", "and", "for", "with", "map", "plan", "our", "that", "this", "into", "from", "about"}


@dataclass
class Diagnostic:
    level: str  # "error" or "warn"
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.path}: {self.message}"


@dataclass
class Doc:
    meta: dict
    has_frontmatter: bool
    title: str
    sections: dict  # heading -> list of raw lines (fences kept)
    section_order: list


@dataclass
class Ticket:
    num: int
    path: Path
    doc: Doc
    type: str = ""
    raw_type: str = ""
    blocked_by: list = field(default_factory=list)
    undermined_by: list = field(default_factory=list)
    claimed_by: str = ""
    claimed_at: str = ""
    decided_by: str = ""
    status: str = "open"

    @property
    def title(self) -> str:
        return self.doc.title

    @property
    def closed(self) -> bool:
        return self.status in ("resolved", "out_of_scope")


# ---------------------------------------------------------------- parsing


def _parse_value(raw: str):
    value = raw.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].strip()
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
    return value.strip("'\"")


def parse_doc(text: str) -> Doc:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    meta: dict = {}
    has_frontmatter = False
    start = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                has_frontmatter = True
                for line in lines[1:index]:
                    if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
                        continue
                    key, _, value = line.partition(":")
                    meta[key.strip()] = _parse_value(value)
                start = index + 1
                break
    title = ""
    sections: dict = {}
    order: list = []
    current = None
    in_fence = False
    for line in lines[start:]:
        if RE_FENCE.match(line):
            in_fence = not in_fence
            if current is not None:
                sections[current].append(line)
            continue
        if not in_fence:
            if line.startswith("# ") and not title:
                title = line[2:].strip()
                current = None
                continue
            if line.startswith("## "):
                current = line[3:].strip().rstrip("#").strip()
                if current not in sections:
                    sections[current] = []
                    order.append(current)
                continue
        if current is not None:
            sections[current].append(line)
    return Doc(meta, has_frontmatter, title, sections, order)


def has_prose(lines) -> bool:
    text = RE_COMMENT.sub("", "\n".join(lines or []))
    return bool(text.strip())


def section_text(doc: Doc, name: str) -> list:
    """Section lines outside fences and comments, for structural scans."""
    out = []
    in_fence = False
    for line in doc.sections.get(name, []):
        if RE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    text = RE_COMMENT.sub("", "\n".join(out))
    return text.split("\n")


def _as_list(value) -> list:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    return [value]


def _nums(values, diags, path, key) -> list:
    out = []
    for item in _as_list(values):
        try:
            out.append(int(str(item)))
        except ValueError:
            diags.append(Diagnostic("error", path, f"{key} entry {item!r} is not a ticket number"))
    return out


@dataclass
class MapData:
    root: Path
    doc: Doc
    tickets: list
    diags: list

    def by_num(self, num: int):
        for ticket in self.tickets:
            if ticket.num == num:
                return ticket
        return None


def load_map(root: Path) -> MapData | None:
    map_path = root / MAP_FILE
    if not map_path.is_file():
        return None
    diags: list = []
    doc = parse_doc(map_path.read_text(encoding="utf-8", errors="replace"))
    tickets = []
    tickets_dir = root / "tickets"
    if tickets_dir.is_dir():
        for path in sorted(tickets_dir.iterdir()):
            if not path.is_file() or path.suffix != ".md":
                continue
            match = RE_TICKET_FILE.match(path.name)
            rel = path.relative_to(root).as_posix()
            if not match:
                diags.append(Diagnostic("error", rel, "ticket file name must be NN-<slug>.md"))
                continue
            tdoc = parse_doc(path.read_text(encoding="utf-8", errors="replace"))
            ticket = Ticket(int(match.group(1)), path, tdoc)
            raw_type = str(tdoc.meta.get("type", "")).strip().lower()
            ticket.raw_type = raw_type
            ticket.type = raw_type
            ticket.blocked_by = _nums(tdoc.meta.get("blocked_by"), diags, rel, "blocked_by")
            ticket.undermined_by = _nums(tdoc.meta.get("undermined_by"), diags, rel, "undermined_by")
            ticket.claimed_by = str(tdoc.meta.get("claimed_by", "") or "")
            ticket.claimed_at = str(tdoc.meta.get("claimed_at", "") or "")
            ticket.decided_by = str(tdoc.meta.get("decided_by", "") or "")
            answered = has_prose(tdoc.sections.get("Answer"))
            ruled_out = has_prose(tdoc.sections.get("Ruled out"))
            if answered and not ruled_out:
                ticket.status = "resolved"
            elif ruled_out and not answered:
                ticket.status = "out_of_scope"
            elif answered and ruled_out:
                ticket.status = "resolved"  # reported as an error by lint
            elif ticket.claimed_by:
                ticket.status = "claimed"
            tickets.append(ticket)
    return MapData(root, doc, tickets, diags)


def frontier(data: MapData) -> list:
    out = []
    for ticket in sorted(data.tickets, key=lambda t: t.num):
        if ticket.status != "open":
            continue
        blockers = [data.by_num(b) for b in ticket.blocked_by]
        if all(b is not None and b.status == "resolved" for b in blockers):
            out.append(ticket)
    return out


# ---------------------------------------------------------------- lint


def _parse_time(value: str):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or "T" not in value:
        return None
    return parsed


def find_cycles(data: MapData) -> list:
    color: dict = {}
    stack: list = []
    found: list = []

    def visit(num: int) -> None:
        color[num] = 1
        stack.append(num)
        ticket = data.by_num(num)
        for blocker in (ticket.blocked_by if ticket else []):
            if data.by_num(blocker) is None or blocker == num:
                continue
            state = color.get(blocker, 0)
            if state == 0:
                visit(blocker)
            elif state == 1:
                cycle = stack[stack.index(blocker):] + [blocker]
                found.append(" -> ".join(f"{n:02d}" for n in cycle))
        stack.pop()
        color[num] = 2

    for ticket in sorted(data.tickets, key=lambda t: t.num):
        if color.get(ticket.num, 0) == 0:
            visit(ticket.num)
    return found


def lint_map(data: MapData, now: datetime | None = None, max_tickets: int = MAX_TICKETS,
             stale_hours: int = STALE_CLAIM_HOURS) -> list:
    now = now or datetime.now(timezone.utc)
    diags = list(data.diags)
    root = data.root
    mp = MAP_FILE

    def add(level: str, path: str, message: str) -> None:
        diags.append(Diagnostic(level, path, message))

    meta = data.doc.meta
    slug = str(meta.get("slug", ""))
    if not slug:
        add("error", mp, "no slug in the map frontmatter")
    elif slug != root.name:
        add("error", mp, f"slug {slug!r} does not match the folder name {root.name!r}")
    elif not RE_SLUG.match(slug):
        add("error", mp, f"slug {slug!r} must be lowercase words joined by '-'")
    tracker = str(meta.get("tracker", ""))
    if tracker not in TRACKERS:
        add("error", mp, f"tracker {tracker!r} is not one of {', '.join(TRACKERS)}")
    for key in FORBIDDEN_MAP_KEYS:
        if key in meta:
            add("error", mp, f"frontmatter key {key!r} is not allowed: a map cannot switch off the no-build rule")
    if not has_prose(data.doc.sections.get("Destination")):
        add("error", mp, "no Destination: every session starts from it")
    notes = "\n".join(section_text(data.doc, "Notes"))
    if RE_OVERRIDE.search(notes):
        add("error", mp, "Notes try to allow building during planning; this is void, only the human can allow it in a session")

    seen: dict = {}
    counted = 0
    claimed_now = []
    for ticket in data.tickets:
        rel = ticket.path.relative_to(root).as_posix()
        if ticket.num in seen:
            add("error", rel, f"duplicate ticket number {ticket.num:02d} (also {seen[ticket.num]})")
        seen[ticket.num] = rel
        if ticket.status != "out_of_scope":
            counted += 1
        if not ticket.doc.has_frontmatter:
            add("error", rel, "no frontmatter block")
        if not ticket.title:
            add("error", rel, "no '# ' title: tickets are referred to by name")
        if ticket.raw_type in OLD_TYPE_NAMES:
            add("error", rel, f"type {ticket.raw_type!r} is an old name; write {OLD_TYPE_NAMES[ticket.raw_type]!r}")
        elif ticket.type not in TICKET_TYPES:
            add("error", rel, f"type {ticket.raw_type!r} is not one of {', '.join(TICKET_TYPES)}")
        stored = str(ticket.doc.meta.get("status", "")).strip()
        if stored:
            if stored != ticket.status:
                add("error", rel, f"stored status {stored!r} disagrees with the derived status {ticket.status!r}; delete the field")
            else:
                add("warn", rel, "status is derived from the body; delete the status field")
        if not has_prose(ticket.doc.sections.get("Question")):
            add("error", rel, "no Question")
        if "Answer" in ticket.doc.sections and "Ruled out" in ticket.doc.sections:
            add("error", rel, "has both Answer and Ruled out")
        for heading in ("Answer", "Ruled out"):
            if heading in ticket.doc.sections and not has_prose(ticket.doc.sections[heading]):
                add("error", rel, f"empty '## {heading}' heading: write the prose or remove the heading")
        if ticket.status == "resolved" and ticket.type in HUMAN_TYPES and not ticket.decided_by:
            add("error", rel, f"resolved {ticket.type} ticket has no decided_by: the human makes this decision")
        if ticket.type == "task" and RE_BUILD_TITLE.match(ticket.title or ""):
            add("warn", rel, "task title reads like a build step; tasks only unblock decisions")
        if ticket.closed:
            if ticket.claimed_by or ticket.claimed_at:
                add("warn", rel, "closed but still claimed; clear claimed_by and claimed_at")
        elif ticket.claimed_by or ticket.claimed_at:
            if ticket.type != "research":
                claimed_now.append(ticket)
            if not ticket.claimed_by:
                add("warn", rel, "claimed_at without claimed_by")
            if not ticket.claimed_at:
                add("warn", rel, "claimed without claimed_at: a stale claim cannot be seen")
            else:
                at = _parse_time(ticket.claimed_at)
                if at is None:
                    add("error", rel, f"claimed_at {ticket.claimed_at!r} is not an ISO 8601 time with a time zone")
                elif now - at > timedelta(hours=stale_hours):
                    hours = int((now - at).total_seconds() // 3600)
                    add("warn", rel, f"claim is {hours}h old (over {stale_hours}h): likely a dead session, say so before taking or skipping it")
        for blocker in ticket.blocked_by:
            dep = data.by_num(blocker)
            if blocker == ticket.num:
                add("error", rel, "blocked_by itself")
            elif dep is None:
                add("error", rel, f"blocked_by {blocker:02d}, which does not exist")
            elif dep.status == "out_of_scope":
                add("warn", rel, f"blocked_by {blocker:02d}, which is out of scope: this ticket can never unblock")
        for other in ticket.undermined_by:
            if data.by_num(other) is None:
                add("error", rel, f"undermined_by {other:02d}, which does not exist")

    if len(claimed_now) > 1:
        names = ", ".join(f"{t.num:02d}" for t in claimed_now)
        add("warn", mp, f"several non-research tickets claimed at once ({names}): one ticket per session")
    if counted > max_tickets:
        add("error", mp, f"{counted} tickets, over the limit of {max_tickets}: split the destination into a second map")
    elif counted >= min(NEAR_LIMIT, max_tickets):
        add("warn", mp, f"{counted} tickets, near the limit of {max_tickets}")

    for cycle in find_cycles(data):
        add("error", mp, f"blocked_by cycle: {cycle}")

    listed: dict = {}
    for line in section_text(data.doc, "Decisions so far"):
        for match in RE_TICKET_LINK.finditer(line):
            num = int(match.group(1))
            listed[num] = listed.get(num, 0) + 1
            ticket = data.by_num(num)
            if ticket is None:
                add("error", mp, f"Decisions so far links ticket {num:02d}, which does not exist")
            elif ticket.status == "out_of_scope":
                add("error", mp, f"Decisions so far lists {num:02d}, which is out of scope")
            elif ticket.status != "resolved":
                add("error", mp, f"Decisions so far lists {num:02d}, which is {ticket.status}, not resolved")
    for num, count in listed.items():
        if count > 1:
            add("warn", mp, f"Decisions so far lists ticket {num:02d} {count} times")
    scoped = set()
    for line in section_text(data.doc, "Out of scope"):
        for match in RE_TICKET_LINK.finditer(line):
            scoped.add(int(match.group(1)))
    for ticket in data.tickets:
        rel = ticket.path.relative_to(root).as_posix()
        if ticket.status == "resolved" and ticket.num not in listed:
            add("error", rel, "resolved but missing from the map's Decisions so far")
        if ticket.status == "out_of_scope" and ticket.num not in scoped:
            add("error", rel, "out of scope but missing from the map's Out of scope list")

    live = {t.title.lower(): t for t in data.tickets if not t.closed and t.title}
    for line in section_text(data.doc, "Not yet specified"):
        if not re.match(r"^\s*[-*]\s+", line):
            continue
        title_match = RE_FOG_TITLE.match(line)
        if not title_match:
            add("warn", mp, "fog item has no bold title")
            continue
        fog_title = title_match.group(1).strip().rstrip(".").strip()
        if fog_title.lower() in live:
            add("error", mp, f"fog item {fog_title!r} duplicates a live ticket")
        clears = RE_CLEARS.search(line)
        if clears:
            num = int(clears.group(1))
            dep = data.by_num(num)
            if dep is None:
                add("error", mp, f"fog item {fog_title!r} clears-with {num:02d}, which does not exist")
            elif dep.status == "resolved":
                add("error", mp, f"fog item {fog_title!r} clears-with {num:02d}, already resolved: make it a ticket or strike it")
    return diags


# ---------------------------------------------------------------- registry


@dataclass
class RegistryRow:
    slug: str
    destination: str
    status: str
    last_worked: str
    aliases: list


def parse_registry(text: str) -> list:
    rows = []
    in_fence = False
    for line in RE_COMMENT.sub("", text).split("\n"):
        if RE_FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or set("".join(cells)) <= set("-: "):
            continue
        slug = cells[0].strip("`")
        if slug.lower() == "slug" or slug.startswith("<"):
            continue
        aliases = []
        if len(cells) > 4 and cells[4] not in ("", "-"):
            aliases = [a.strip().strip("`").lower() for a in cells[4].split(",") if a.strip()]
        rows.append(RegistryRow(slug, cells[1], cells[2].lower(), cells[3], aliases))
    return rows


def lint_registry(maps_root: Path) -> list:
    diags = []
    reg = maps_root / REGISTRY_FILE
    rows = parse_registry(reg.read_text(encoding="utf-8", errors="replace"))
    names: dict = {}
    for row in rows:
        for name in [row.slug] + row.aliases:
            if name in names:
                diags.append(Diagnostic("error", REGISTRY_FILE, f"name {name!r} is used twice ({names[name]} and {row.slug})"))
            names[name] = row.slug
        if row.status not in REGISTRY_STATUSES:
            diags.append(Diagnostic("error", REGISTRY_FILE, f"{row.slug}: status {row.status!r} is not active, paused, or done"))
        try:
            date.fromisoformat(row.last_worked)
        except ValueError:
            diags.append(Diagnostic("error", REGISTRY_FILE, f"{row.slug}: last worked {row.last_worked!r} is not YYYY-MM-DD"))
        if not (maps_root / row.slug / MAP_FILE).is_file():
            diags.append(Diagnostic("error", REGISTRY_FILE, f"{row.slug}: no {row.slug}/{MAP_FILE}"))
    listed = {row.slug for row in rows}
    for child in sorted(maps_root.iterdir()):
        if child.is_dir() and (child / MAP_FILE).is_file() and child.name not in listed:
            diags.append(Diagnostic("error", REGISTRY_FILE, f"map {child.name!r} is missing from the registry"))
    for row in rows:
        data = load_map(maps_root / row.slug)
        if data and row.status == "done" and any(not t.closed for t in data.tickets):
            diags.append(Diagnostic("warn", REGISTRY_FILE, f"{row.slug} is marked done but has open tickets"))
    return diags


# ---------------------------------------------------------------- find


@dataclass
class FindResult:
    result: str  # found | ask | none
    slug: str = ""
    reason: str = ""
    candidates: list = field(default_factory=list)


def _words(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) >= 3 and w not in STOPWORDS}


def find_map(rows: list, words: list | None = None, slug: str | None = None) -> FindResult:
    """Steps 1-4 of the map-finding order. Step 5 (other projects) is the caller's choice."""
    words = words or []
    open_rows = [r for r in rows if r.status in ("active", "paused")]
    short_list = [r.slug for r in sorted(open_rows, key=lambda r: r.last_worked, reverse=True)]
    if slug:
        wanted = slug.strip().lower()
        for row in rows:
            if wanted == row.slug or wanted in row.aliases:
                return FindResult("found", row.slug, "exact slug or alias")
        return FindResult("ask", reason=f"no map named {slug!r} here", candidates=short_list)
    active = [r for r in rows if r.status == "active"]
    wanted_words = _words(" ".join(words))
    if len(active) == 1:
        only = active[0]
        if not wanted_words:
            return FindResult("found", only.slug, "the only active map")
        mine = _words(" ".join([only.slug, only.destination] + only.aliases))
        others = [r for r in rows if r is not only and wanted_words & _words(" ".join([r.slug, r.destination] + r.aliases))]
        if wanted_words & mine or not others:
            return FindResult("found", only.slug, "the only active map")
    if not rows:
        return FindResult("none", reason="no maps in this registry")
    if not wanted_words:
        return FindResult("ask", reason=f"{len(active)} active maps; which one?", candidates=short_list)
    scored = []
    for row in rows:
        hay = _words(" ".join([row.slug, row.destination] + row.aliases))
        score = len(wanted_words & hay)
        if score:
            scored.append((score, row))
    if not scored:
        return FindResult("ask", reason="no map matches those words", candidates=short_list)
    best = max(score for score, _ in scored)
    top = [row for score, row in scored if score == best]
    if len(top) == 1:
        return FindResult("found", top[0].slug, "best match on name and destination")
    top.sort(key=lambda r: r.last_worked, reverse=True)
    if top[0].last_worked != top[1].last_worked:
        return FindResult("found", top[0].slug, f"most recent of {len(top)} equal matches",
                          [r.slug for r in top])
    return FindResult("ask", reason="several maps match equally", candidates=[r.slug for r in top])


# ---------------------------------------------------------------- CLI


def _print_diags(diags: list) -> int:
    errors = sum(1 for d in diags if d.level == "error")
    for diag in diags:
        print(diag)
    warns = len(diags) - errors
    print(f"bmap lint: {errors} error(s), {warns} warning(s)")
    return 1 if errors else 0


def cmd_lint(path: Path, now: datetime | None, max_tickets: int) -> int:
    if (path / MAP_FILE).is_file():
        data = load_map(path)
        return _print_diags(lint_map(data, now, max_tickets))
    if (path / REGISTRY_FILE).is_file():
        diags = lint_registry(path)
        for row in parse_registry((path / REGISTRY_FILE).read_text(encoding="utf-8", errors="replace")):
            data = load_map(path / row.slug)
            if data:
                for diag in lint_map(data, now, max_tickets):
                    diags.append(Diagnostic(diag.level, f"{row.slug}/{diag.path}", diag.message))
        return _print_diags(diags)
    print(f"bmap: no {MAP_FILE} or {REGISTRY_FILE} at {path}")
    return 2


def cmd_status(path: Path) -> int:
    data = load_map(path)
    if data is None:
        print(f"bmap: no {MAP_FILE} at {path}")
        return 2
    counts = {key: 0 for key in ("resolved", "claimed", "open", "out_of_scope")}
    for ticket in data.tickets:
        counts[ticket.status] += 1
    print(data.doc.meta.get("slug", path.name))
    print(f"{counts['resolved']} resolved, {counts['claimed']} claimed, {counts['open']} open, {counts['out_of_scope']} out of scope")
    front = frontier(data)
    print("Frontier (take the first, one per session):" if front else "Frontier: empty")
    for ticket in front:
        print(f"  {ticket.num:02d}  {ticket.title}  [{ticket.type}]")
    undermined = [t for t in data.tickets if t.status == "resolved" and t.undermined_by]
    for ticket in undermined:
        by = ", ".join(f"{n:02d}" for n in ticket.undermined_by)
        print(f"Undermined: {ticket.num:02d} {ticket.title} (by {by})")
    return 0


def cmd_find(path: Path, words: list, slug: str | None) -> int:
    reg = path / REGISTRY_FILE
    if not reg.is_file():
        print(f"bmap: no {REGISTRY_FILE} at {path}")
        return 2
    result = find_map(parse_registry(reg.read_text(encoding="utf-8", errors="replace")), words, slug)
    print(f"result: {result.result}")
    if result.slug:
        print(f"slug: {result.slug}")
        print(f"path: {(path / result.slug / MAP_FILE).as_posix()}")
    print(f"reason: {result.reason}")
    if result.candidates:
        print("candidates: " + ", ".join(result.candidates))
    return 0 if result.result == "found" else 1


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="bMap lint, status, and map finding.")
    sub = parser.add_subparsers(dest="command", required=True)
    lint = sub.add_parser("lint", help="check a map folder, or a maps folder with REGISTRY.md")
    lint.add_argument("path")
    lint.add_argument("--now", help="ISO 8601 time to judge claims against (tests)")
    lint.add_argument("--max-tickets", type=int, default=MAX_TICKETS)
    status = sub.add_parser("status", help="show progress and the frontier of one map")
    status.add_argument("path")
    find = sub.add_parser("find", help="find a map in a maps folder")
    find.add_argument("path")
    find.add_argument("words", nargs="*")
    find.add_argument("--slug")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    path = Path(args.path)
    if args.command == "lint":
        now = _parse_time(args.now) if args.now else None
        return cmd_lint(path, now, args.max_tickets)
    if args.command == "status":
        return cmd_status(path)
    return cmd_find(path, args.words, args.slug)


if __name__ == "__main__":
    sys.exit(main())
