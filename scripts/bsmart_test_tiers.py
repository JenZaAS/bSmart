"""Test tiers: tags, pass/fail history, and automatic tier moves (standard library only).

Rules: bSmart_Protocols/test-tiers.md. The project's code repo keeps a tag manifest
(default `test-tiers.txt`); the instance keeps settings and history under
`<content-root>/State/test-tiers/`. Nothing here is project-specific.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

LIKELIHOODS = ("main", "edge")
SEVERITIES = ("high", "med", "low")
TIERS = ("normal", "special")
UNTAGGED = "?/?"
DEFAULTS = {
    "demote_after_runs": 100,
    "demote_after_weeks": 4,
    "special_every_days": 14,
    "retire_after_special_runs": 100,
    "retire_after_weeks": 26,
    "slow_seconds": 2.0,
    "main_branch": "main",
    "keep_months": 12,
    "pause_after_days": 60,
}
INLINE_TAG = re.compile(r"\s*\[(main|edge)/(high|med|low)(?:\s+fix\s+(#?[\w-]*\d[\w-]*))?\]\s*$", re.I)


class UsageError(Exception):
    pass


# ------------------------------------------------------------------ helpers

def today() -> dt.date:
    return dt.date.today()


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def split_inline_tag(name: str) -> tuple[str, str | None, str | None]:
    """'does x [main/high fix #37]' -> ('does x', 'main/high', '#37')."""
    m = INLINE_TAG.search(name)
    if not m:
        return name.strip(), None, None
    fix = m.group(3)
    if fix and not fix.startswith("#"):
        fix = "#" + fix
    return name[: m.start()].strip(), f"{m.group(1).lower()}/{m.group(2).lower()}", fix


def norm_path(p: str) -> str:
    p = (p or "").replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


# ------------------------------------------------------------------ manifest

class Entry:
    __slots__ = ("tier", "tag", "fix", "pattern", "line")

    def __init__(self, tier: str, tag: str, fix: str | None, pattern: str, line: int = 0):
        self.tier, self.tag, self.fix, self.pattern, self.line = tier, tag, fix, pattern, line

    @property
    def likelihood(self) -> str:
        return self.tag.split("/")[0]

    @property
    def severity(self) -> str:
        return self.tag.split("/")[-1]

    @property
    def is_glob(self) -> bool:
        return any(c in self.pattern for c in "*?[")

    @property
    def protected(self) -> bool:
        """High severity and bug-fix tests never leave the normal tier."""
        return self.severity == "high" or bool(self.fix)

    def render(self) -> str:
        return f"{self.tier:<8} {self.tag:<10} {(self.fix or '-'):<8} {self.pattern}"


HEADER = """# Test tiers manifest (bSmart_Protocols/test-tiers.md)
# One line per test or glob: <tier> <likelihood>/<severity> <fix or -> <test id>
#   tier: normal | special     likelihood: main | edge     severity: high | med | low
#   fix: #<issue or PR> when the test guards a found or reported bug, else -
#   test id: <file>::<test name> as the runner reports it; * and ? match like file globs
# Exact ids win over globs; the first matching glob wins. Untagged: ?/?
"""


def parse_manifest(text: str) -> tuple[list[Entry], list[str]]:
    entries, problems = [], []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 3)
        if len(parts) < 4:
            problems.append(f"line {n}: needs <tier> <tag> <fix or -> <test id>")
            continue
        tier, tag, fix, pattern = parts
        entries.append(Entry(tier.lower(), tag.lower(), None if fix == "-" else fix, pattern.strip(), n))
    return entries, problems


def read_manifest(path: Path) -> tuple[list[Entry], list[str]]:
    if not path.is_file():
        return [], []
    return parse_manifest(path.read_text(encoding="utf-8-sig"))


def write_manifest(path: Path, entries: list[Entry]) -> None:
    body = "\n".join(e.render() for e in sorted(entries, key=lambda e: (e.is_glob, e.pattern)))
    write_text_atomic(path, HEADER + "\n" + body + "\n")


def tag_problems(e: Entry) -> list[str]:
    out = []
    if e.tier not in TIERS:
        out.append(f"bad_tier line {e.line}: {e.tier}")
    if e.tag == UNTAGGED:
        out.append(f"untagged: {e.pattern}")
    else:
        parts = e.tag.split("/")
        if len(parts) != 2 or parts[0] not in LIKELIHOODS or parts[1] not in SEVERITIES:
            out.append(f"bad_tag line {e.line}: {e.tag}")
    if e.fix and not re.fullmatch(r"#[\w-]*\d[\w-]*", e.fix):
        out.append(f"bad_fix line {e.line}: {e.fix} (use #<number>)")
    if e.tier == "special" and e.tag != UNTAGGED and e.protected:
        out.append(f"protected_in_special: {e.pattern} (high and fix tests stay normal)")
    return out


def lookup(entries: list[Entry], test_id: str) -> Entry | None:
    for e in entries:
        if not e.is_glob and e.pattern == test_id:
            return e
    for e in entries:
        if e.is_glob and fnmatch.fnmatchcase(test_id, e.pattern):
            return e
    return None


# ------------------------------------------------------------------ run reports

def read_reports(paths: list[Path]) -> dict[str, dict]:
    """JUnit XML or a JSON list [{"id", "result": pass|fail|skip, "seconds"}] -> {id: result}."""
    out: dict[str, dict] = {}
    for path in paths:
        text = Path(path).read_text(encoding="utf-8-sig")
        if text.lstrip().startswith(("[", "{")):
            data = json.loads(text)
            for row in data if isinstance(data, list) else data.get("tests", []):
                tid, _, _ = split_inline_tag(str(row["id"]))
                out[tid] = {"result": row.get("result", "pass"), "seconds": float(row.get("seconds", 0) or 0),
                            "raw_name": str(row["id"])}
            continue
        root = ET.fromstring(text)
        for case in root.iter("testcase"):
            raw = case.get("name", "")
            name, _, _ = split_inline_tag(raw)
            where = norm_path(case.get("file") or "") or case.get("classname", "")
            tid = f"{where}::{name}" if where else name
            result = "pass"
            for child in case:
                tag = child.tag.lower()
                if tag in ("failure", "error"):
                    result = "fail"
                elif tag == "skipped" and result == "pass":
                    result = "skip"
            out[tid] = {"result": result, "seconds": float(case.get("time") or 0), "raw_name": raw}
    return out


# ------------------------------------------------------------------ instance store

def store_dir(content_root: Path, project: str, repo: str) -> Path:
    safe = lambda s: re.sub(r"[^\w.-]+", "_", s)  # noqa: E731
    return Path(content_root) / "State" / "test-tiers" / safe(project) / safe(repo)


def load_settings(content_root: Path, project: str) -> dict:
    s = dict(DEFAULTS)
    path = Path(content_root) / "State" / "test-tiers" / "settings.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        s.update({k: v for k, v in data.items() if k in DEFAULTS})
        s.update({k: v for k, v in (data.get("projects", {}).get(project) or {}).items() if k in DEFAULTS})
    return s


def load_history(folder: Path) -> dict:
    path = folder / "history.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {"version": 1, "last_special": None, "main": None, "paused": None, "tests": {}}


def save_history(folder: Path, hist: dict) -> None:
    write_text_atomic(folder / "history.json", json.dumps(hist, indent=1, sort_keys=True) + "\n")


def record_run(folder: Path, results: dict[str, dict], tier: str, sha: str, branch: str,
               settings: dict, when: dt.date | None = None) -> dict:
    """Add one run's results to the history; return a short summary.

    Also the activity check: a first run notes that tiering was set up, and a
    run on a new commit after a pause re-activates the special tier.
    """
    when = when or today()
    day = when.isoformat()
    notes = []
    if not (folder / "history.json").is_file():
        notes.append("set up: test tiers history started for this repo")
    hist = load_history(folder)
    paused = hist.get("paused")
    if paused and paused.get("sha") != sha:
        notes.append(f"re-activated: work resumed after a pause since {paused.get('since')}")
        hist["paused"] = None
    if branch == settings["main_branch"] and (hist.get("main") or {}).get("sha") != sha:
        hist["main"] = {"sha": sha, "changed": day}
    tests = hist["tests"]
    counts = {"pass": 0, "fail": 0, "skip": 0}
    failing, new_failures = [], []
    for tid, r in results.items():
        res = r["result"] if r["result"] in counts else "fail"
        counts[res] += 1
        if res == "skip":
            continue
        t = tests.setdefault(tid, {"runs": 0, "fails": 0, "streak": 0, "streak_since": None,
                                   "special_streak": 0, "special_since": None, "last": None,
                                   "last_fail": None, "max_seconds": 0.0})
        t["runs"] += 1
        t["prev"] = t.get("last")
        t["last"] = res
        t["last_seconds"] = r.get("seconds", 0.0)
        t["max_seconds"] = max(t.get("max_seconds", 0.0), r.get("seconds", 0.0))
        if res == "pass":
            if t["streak"] == 0:
                t["streak_since"] = day
            t["streak"] += 1
            if tier in ("special", "all"):
                if t["special_streak"] == 0:
                    t["special_since"] = day
                t["special_streak"] += 1
        else:
            failing.append(tid)
            if t["runs"] == 1 or t.get("prev") != "fail":
                new_failures.append(tid)
            t["fails"] += 1
            t["last_fail"] = day
            t["streak"], t["streak_since"] = 0, None
            t["special_streak"], t["special_since"] = 0, None
    if tier in ("special", "all") and branch == settings["main_branch"]:
        hist["last_special"] = {"sha": sha, "date": day}
    save_history(folder, hist)
    timed = sorted(((r.get("seconds", 0.0), tid) for tid, r in results.items()), reverse=True)
    run = {"date": day, "sha": sha, "branch": branch, "tier": tier, **counts,
           "seconds": round(sum(x for x, _ in timed), 2), "failing": failing[:50],
           "new_failures": sorted(new_failures), "slowest": [[tid, round(x, 2)] for x, tid in timed[:3]],
           "notes": notes}
    runs = folder / "runs.jsonl"
    keep_after = (when - dt.timedelta(days=31 * int(settings["keep_months"]))).isoformat()
    old = runs.read_text(encoding="utf-8").splitlines() if runs.is_file() else []
    kept = [ln for ln in old if ln.strip() and json.loads(ln).get("date", "") >= keep_after]
    write_text_atomic(runs, "\n".join(kept + [json.dumps(run)]) + "\n")
    return run


def special_due(folder: Path, sha: str, branch: str, settings: dict,
                when: dt.date | None = None, commit_date: str | None = None) -> tuple[bool, str]:
    """Special tier: only on main, only if main changed, at most every special_every_days.

    Pauses when main has not changed for pause_after_days; the pause is written
    to the history and the special log once, never silently.
    """
    when = when or today()
    if branch != settings["main_branch"]:
        return False, f"not on {settings['main_branch']}"
    hist = load_history(folder)
    if hist.get("paused") and hist["paused"].get("sha") == sha:
        return False, f"paused (inactive): {settings['main_branch']} unchanged since {hist['paused'].get('changed')}"
    main = hist.get("main") or {}
    changed = commit_date or (main.get("changed") if main.get("sha") == sha else None)
    if changed:
        idle = (when - dt.date.fromisoformat(changed[:10])).days
        if idle >= int(settings["pause_after_days"]):
            hist["paused"] = {"since": when.isoformat(), "sha": sha, "changed": changed[:10]}
            save_history(folder, hist)
            why = (f"paused (inactive): {settings['main_branch']} unchanged since {changed[:10]} ({idle} days); "
                   f"special runs resume when work resumes")
            append_log_line(folder, "special", f"- {when.isoformat()} {why}\n", settings, when)
            return False, why
    last = hist.get("last_special")
    if not last:
        return True, "no special run recorded yet"
    if last.get("sha") == sha:
        return False, f"{settings['main_branch']} unchanged since the last special run ({last.get('date')})"
    age = (when - dt.date.fromisoformat(last["date"])).days
    if age < int(settings["special_every_days"]):
        return False, f"last special run {age} days ago (every {settings['special_every_days']} days)"
    return True, f"{settings['main_branch']} changed and the last special run was {age} days ago"


# ------------------------------------------------------------------ run log

LOG_HEADER = """# Test tiers run log: {tier} tier (bSmart_Protocols/test-tiers.md)
# One entry per run, newest last: date commit branch | pass fail skip | duration | new failures | moves | slowest
# Instance only. Kept for keep_months.

"""


def log_path(folder: Path, tier: str) -> Path:
    """One log per tier; a full run (`all`) goes in the special log, marked `all`."""
    return folder / f"log-{'normal' if tier == 'normal' else 'special'}.md"


def format_log_entry(run: dict, moves: dict | None = None) -> str:
    def ids(items, limit=5):
        items = list(items)
        more = f" +{len(items) - limit}" if len(items) > limit else ""
        return ", ".join(items[:limit]) + more if items else "none"
    moves = moves or {"to_normal": [], "to_special": []}
    head = f"- {run['date']} {run['sha'][:10]} {run['branch']}" + (" (all)" if run["tier"] == "all" else "")
    slow = ", ".join(f"{tid} {sec}s" for tid, sec in run.get("slowest", [])) or "none"
    return (f"{head} | {run['pass']} pass, {run['fail']} fail, {run['skip']} skip | {run.get('seconds', 0)}s\n"
            f"  new failures: {ids(run.get('new_failures', []))}\n"
            f"  to normal: {len(moves['to_normal'])} ({ids(moves['to_normal'])}); "
            f"to special: {len(moves['to_special'])} ({ids(moves['to_special'])})\n"
            f"  slowest: {slow}\n"
            + "".join(f"  note: {n}\n" for n in run.get("notes", [])))


def _log_entries(path: Path) -> list[str]:
    entries: list[str] = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
            if line.startswith("- "):
                entries.append(line)
            elif line.startswith("  ") and entries:
                entries[-1] += line
    return entries


def append_log_line(folder: Path, tier: str, entry: str, settings: dict, when: dt.date | None = None) -> Path:
    """Append one entry (a '- <date> ...' block) to a tier log, dropping entries past keep_months."""
    when = when or today()
    path = log_path(folder, tier)
    keep_after = (when - dt.timedelta(days=31 * int(settings["keep_months"]))).isoformat()
    kept = [e for e in _log_entries(path) if e[2:12] >= keep_after]
    name = "normal" if tier == "normal" else "special"
    write_text_atomic(path, LOG_HEADER.format(tier=name) + "".join(kept) + entry)
    return path


def add_log_note(folder: Path, tier: str, text: str) -> Path:
    """Add '  note: <text>' to the newest entry of a tier log (for example the issue link)."""
    path = log_path(folder, tier)
    entries = _log_entries(path)
    if not entries:
        raise UsageError(f"no entries in {path}")
    entries[-1] += f"  note: {text}\n"
    name = "normal" if tier == "normal" else "special"
    write_text_atomic(path, LOG_HEADER.format(tier=name) + "".join(entries))
    return path


def append_log(folder: Path, run: dict, moves: dict | None, settings: dict,
               when: dt.date | None = None) -> Path:
    return append_log_line(folder, run["tier"], format_log_entry(run, moves), settings, when)


# ------------------------------------------------------------------ gate and issue

def gate(entries: list[Entry], results: dict[str, dict]) -> tuple[list[str], list[str]]:
    """(blocking, not blocking) failures. Only normal-tier failures block a release or merge;
    a test that is untagged or not in the manifest counts as normal."""
    blocking, later = [], []
    for tid, r in sorted(results.items()):
        if r["result"] != "fail":
            continue
        e = lookup(entries, tid)
        (later if e is not None and e.tier == "special" else blocking).append(tid)
    return blocking, later


def special_failures(run: dict, entries: list[Entry]) -> list[str]:
    if run["tier"] == "special":
        return list(run.get("failing", []))
    if run["tier"] == "all":
        return [t for t in run.get("failing", []) if (lookup(entries, t) or Entry("normal", UNTAGGED, None, t)).tier == "special"]
    return []


def issue_body(run: dict, entries: list[Entry], repo: str) -> str:
    """Ready-made issue text for special-tier failures, to fix in the next version."""
    fails = special_failures(run, entries)
    lines = [f"Special-tier test failures on {run['branch']} at {run['sha'][:10]} ({run['date']})", "",
             f"Repo: {repo}. Found by the special tier (bSmart_Protocols/test-tiers.md). This does not block",
             "a release; fix it in the next version. The failing tests are back in the normal tier.", "",
             "| Test | Tags |", "|---|---|"]
    for tid in fails:
        e = lookup(entries, tid)
        tags = f"{e.tag}{' ' + e.fix if e and e.fix else ''}" if e else "not in manifest"
        lines.append(f"| `{tid}` | {tags} |")
    lines += ["", f"Run: {run['pass']} pass, {run['fail']} fail, {run['skip']} skip."]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ review

def _weeks_since(day: str | None, when: dt.date) -> float:
    if not day:
        return 0.0
    return (when - dt.date.fromisoformat(day)).days / 7.0


def review(entries: list[Entry], hist: dict, settings: dict, when: dt.date | None = None) -> dict:
    """Tier moves (automatic) and suggestions (never applied)."""
    when = when or today()
    tests = hist.get("tests", {})
    up, down, retire, flaky, untagged = [], [], [], [], []
    for tid, t in sorted(tests.items()):
        e = lookup(entries, tid)
        if e is None or e.tag == UNTAGGED:
            untagged.append(tid)
            continue
        if e.tier == "special" and t.get("last") == "fail":
            up.append(tid)
            continue
        if (e.tier == "normal" and not e.protected and t["streak"] >= int(settings["demote_after_runs"])
                and _weeks_since(t["streak_since"], when) >= float(settings["demote_after_weeks"])):
            down.append(tid)
        if (e.tier == "special" and (e.severity == "low" or e.tag == "edge/med") and not e.fix
                and t["special_streak"] >= int(settings["retire_after_special_runs"])
                and _weeks_since(t["special_since"], when) >= float(settings["retire_after_weeks"])):
            retire.append(tid)
        if t.get("fails", 0) >= 2 and t.get("last") == "pass":
            flaky.append(tid)
    return {"to_normal": up, "to_special": down, "remove_suggestions": retire,
            "flaky": flaky, "untagged": untagged}


def apply_moves(entries: list[Entry], moves: dict) -> list[Entry]:
    """Set the tier of moved tests; a test matched by a glob gets its own exact line."""
    out = list(entries)
    for tid, tier in [(t, "normal") for t in moves["to_normal"]] + [(t, "special") for t in moves["to_special"]]:
        e = lookup(out, tid)
        if e is None:
            continue
        if e.is_glob:
            out.append(Entry(tier, e.tag, e.fix, tid))
        else:
            e.tier = tier
    return out


def place(entries: list[Entry], results: dict[str, dict] | None, settings: dict) -> list[Entry]:
    """One-time first tiers from the tags: special = edge or low, or slow, unless high or fix."""
    slow = float(settings["slow_seconds"])
    for e in entries:
        if e.tag == UNTAGGED:
            continue
        if e.protected:
            e.tier = "normal"
            continue
        secs = 0.0
        if results:
            secs = max([r["seconds"] for tid, r in results.items()
                        if tid == e.pattern or (e.is_glob and fnmatch.fnmatchcase(tid, e.pattern))] or [0.0])
        e.tier = "special" if (e.likelihood == "edge" or e.severity == "low" or secs > slow) else "normal"
    return entries


def report_markdown(moves: dict, applied: bool) -> str:
    lines = ["# Test tiers review", ""]
    def section(title, items, note=""):
        lines.append(f"## {title} ({len(items)})")
        if note:
            lines.append(note)
        lines.extend(f"- `{t}`" for t in items[:200])
        if len(items) > 200:
            lines.append(f"- ... and {len(items) - 200} more")
        lines.append("")
    done = "moved" if applied else "to move (run with --apply)"
    section("Back to normal", moves["to_normal"], f"Special tests that failed: {done}.")
    section("To special", moves["to_special"], f"Long pass streak, not high, no fix: {done}.")
    section("Removal suggestions", moves["remove_suggestions"], "Suggestions only. Nothing is deleted.")
    section("Possibly flaky", moves["flaky"], "Failed at least twice but pass now.")
    section("Untagged or not in the manifest", moves["untagged"])
    return "\n".join(lines)
