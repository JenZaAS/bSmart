#!/usr/bin/env python3
"""bImprove: the coach loop's mechanical parts (standard library only).

Subcommands:
  config   check the instance settings (models, command template, caps)
  run      run a phase of a test kit N times, each in a fresh instance copy
  grade    grade finished runs against an answer key
  guard    snapshot or verify sha256 hashes of protected files
  diff     write an old-vs-new side-by-side HTML diff and print the word delta
  leak     scan files for denylisted terms (instance-local denylist)
  case     run a whole case: baseline, coach rounds, checker, outcome
  regress  rerun a case with the live MDs (no coach) and compare with its last score
  history  list the score history of the instance (State/bimprove-history.jsonl)
  card     print the end-of-run approval card (job size) for a case
  pr-text  draft the neutral PR text for an approved change (never pushes)

Rules live in improve.md. It works on any bSmart MD: a case (kit) names its
target MD files, a prompt, and an answer key. Models are never hard-coded:
they come from the instance settings ("roles") or the instance's shared
role-model file (improve_worker, coach, checker). The agent CLI is called
through the instance's command template.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROLES = ("improve_worker", "coach", "checker")
HOUSEKEEPING = {"index.md", "readme.md", "changelog.md", "categories.md", "task-context-routing.md"}
DEFAULT_QUOTA_PATTERNS = [
    "usage limit", "rate limit", "quota", "insufficient_quota", "429", "purchase more credits",
    "upgrade your plan",
]
DEFAULT_ENV_PATTERNS = ["blocked by policy", "sandbox denied", "access is denied"]
EXIT_OK, EXIT_FINDINGS, EXIT_CONFIG, EXIT_QUOTA, EXIT_GUARD = 0, 1, 2, 3, 4


class ConfigError(Exception):
    pass


class QuotaStop(Exception):
    pass


# ---------------------------------------------------------------- helpers

def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def norm(path: str) -> str:
    """Forward slashes; runs of slashes (CLI logs often double backslashes) become one."""
    return re.sub(r"(?<!:)/{2,}", "/", path.replace("\\", "/"))


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path: Path, data) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def words(text: str) -> int:
    return len(text.split())


def match_any(rel: str, globs) -> bool:
    rel = norm(rel)
    for g in globs or []:
        g = norm(g)
        if fnmatch.fnmatch(rel, g) or (g.endswith("/**") and rel.startswith(g[:-3] + "/")):
            return True
    return False


def is_note(rel: str) -> bool:
    return rel.lower().endswith(".md") and Path(rel).name.lower() not in HOUSEKEEPING


# ------------------------------------------------------------- settings

def parse_role_models(path: Path) -> dict:
    """Read role_models from bswarm-role-models.yaml (flat key: value subset)."""
    out: dict = {}
    if not path.is_file():
        return out
    in_block = False
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith((" ", "\t")):
            in_block = line.strip() == "role_models:"
            continue
        if in_block and ":" in line:
            key, value = line.strip().split(":", 1)
            out[key.strip()] = value.strip().strip("'\"")
    return out


def role_model(value: str | None):
    """'<model> high' -> ('<model>', 'high'); unset/empty -> (None, None)."""
    parts = (value or "").split()
    if not parts or parts[0].lower() in {"unset", "none", "null", "~"}:
        return None, None
    return parts[0], (parts[1] if len(parts) > 1 else "")


def load_settings(instance: Path) -> dict:
    """Instance settings: State/bimprove-settings.json + role models."""
    state = instance / "State"
    settings_path = state / "bimprove-settings.json"
    if not settings_path.is_file():
        raise ConfigError(f"missing {settings_path} (copy templates/bimprove-settings.template.json)")
    settings = read_json(settings_path)
    roles = parse_role_models(state / settings.get("role_models_file", "bswarm-role-models.yaml"))
    roles.update({k: v for k, v in (settings.get("roles") or {}).items()
                  if k in ROLES and role_model(v)[0]})
    models = {}
    for role in ROLES:
        model, effort = role_model(roles.get(role))
        models[role] = {"model": model, "effort": effort or settings.get("default_effort", "")}
    settings["models"] = models
    settings["_instance"] = str(instance)
    deny = state / "bimprove-denylist.txt"
    settings["_denylist"] = str(deny) if deny.is_file() else ""
    return settings


def check_settings(settings: dict, need=ROLES) -> list[str]:
    problems = []
    cmd = settings.get("command")
    if not isinstance(cmd, list) or not cmd:
        problems.append("command: must be a non-empty list (the agent CLI command template)")
    elif "{model}" not in " ".join(cmd):
        problems.append("command: must contain {model}; models are never hard-coded")
    for role in need:
        if not settings["models"].get(role, {}).get("model"):
            problems.append(f"{role}: no model set (settings \"roles\" or the role-model file; no default)")
    m = {r: settings["models"][r]["model"] for r in ROLES}
    if m.get("checker") and m["checker"] in {m.get("improve_worker"), m.get("coach")}:
        problems.append("checker: must be a different model from improve_worker and coach")
    if not isinstance(settings.get("token_cap_case"), int) or settings["token_cap_case"] <= 0:
        problems.append("token_cap_case: set a positive token cap")
    return problems


# ---------------------------------------------------------------- denylist

def load_denylist(path: str | Path | None, extra=None) -> tuple[list[str], list[str]]:
    terms, allow = [], []
    if path and Path(path).is_file():
        for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            (allow if line.startswith("!") else terms).append(line.lstrip("!").strip())
    terms.extend(extra or [])
    return [t for t in terms if t], [a for a in allow if a]


def leak_hits(text: str, terms, allow) -> list[str]:
    hits = []
    low = norm(text).lower()
    for a in allow:
        low = low.replace(norm(a).lower(), " ")
    for term in terms:
        t = norm(term).lower()
        if "/" in t:
            found = t in low
        else:
            found = re.search(r"(?<![\w-])" + re.escape(t) + r"(?![\w-])", low) is not None
        if found:
            hits.append(term)
    return hits


def scan_leaks(root: Path, globs, terms, allow) -> list[dict]:
    found = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        rel = norm(str(path.relative_to(root)))
        if globs and not match_any(rel, globs):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for no, line in enumerate(lines, 1):
            for term in leak_hits(line, terms, allow):
                found.append({"file": rel, "line": no, "term": term})
    return found


# ---------------------------------------------------------------- the CLI

def build_command(template, values: dict) -> list[str]:
    out = []
    for part in template:
        for key, val in values.items():
            part = part.replace("{" + key + "}", str(val))
        if part == "":
            continue
        out.append(part)
    exe = shutil.which(out[0])
    if exe:  # resolves codex.cmd on Windows
        out[0] = exe
    return out


def child_env(settings: dict) -> dict:
    env = dict(os.environ)
    for name in settings.get("strip_env", ["OPENAI_API_KEY", "CODEX_API_KEY"]):
        env.pop(name, None)
    return env


def popen_kwargs() -> dict:
    """Background-friendly: no console window, lower priority."""
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        flags |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000)
        return {"creationflags": flags}

    def lower():
        try:
            os.nice(10)
        except OSError:
            pass
    return {"preexec_fn": lower}


def call_agent(settings: dict, role: str, workdir: Path, prompt: str, log_dir: Path,
               sandbox: str = "workspace-write") -> dict:
    """Run one agent call; return parsed events, tokens, final message."""
    model = settings["models"][role]["model"]
    effort = settings["models"][role]["effort"]
    log_dir.mkdir(parents=True, exist_ok=True)
    last = log_dir / "last-message.txt"
    values = {"model": model, "effort": effort, "workdir": str(workdir), "sandbox": sandbox,
              "last_message_file": str(last)}
    cmd = build_command(settings["command"], values)
    started = time.time()
    with open(log_dir / "events.jsonl", "wb") as out, open(log_dir / "stderr.txt", "wb") as err:
        try:
            proc = subprocess.run(cmd, input=prompt.encode("utf-8"), stdout=out, stderr=err,
                                  cwd=str(workdir), env=child_env(settings),
                                  timeout=settings.get("timeout_seconds", 1200), **popen_kwargs())
            code = proc.returncode
        except subprocess.TimeoutExpired:
            code = "timeout"
    seconds = round(time.time() - started, 1)
    events = parse_events((log_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace"))
    stderr = (log_dir / "stderr.txt").read_text(encoding="utf-8", errors="replace")
    final = last.read_text(encoding="utf-8", errors="replace") if last.is_file() else events["final"]
    patterns = settings.get("quota_stop_patterns", DEFAULT_QUOTA_PATTERNS)
    failure_text = (" ".join(events["errors"]) + " " + (stderr if code not in (0,) else "")).lower()
    quota = bool(failure_text.strip()) and any(p.lower() in failure_text for p in patterns)
    env_pats = settings.get("environment_stop_patterns", DEFAULT_ENV_PATTERNS)
    env_blocked = any(p.lower() in stderr.lower() for p in env_pats)
    result = {"env_blocked": env_blocked, "role": role, "model": model, "effort": effort, "exit": code, "seconds": seconds,
              "tokens": events["tokens"], "final": final, "quota_stop": quota,
              "commands": events["commands"], "web_searches": events["web_searches"]}
    write_json(log_dir / "call.json", result)
    return result


def parse_events(text: str) -> dict:
    tokens = {"input": 0, "cached": 0, "output": 0, "total": 0}
    commands, errors, seen = [], [], set()
    final, web = "", 0
    for raw in text.splitlines():
        try:
            ev = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        usage = ev.get("usage")
        if isinstance(usage, dict):
            tokens["input"] += int(usage.get("input_tokens", 0) or 0)
            tokens["cached"] += int(usage.get("cached_input_tokens", 0) or 0)
            tokens["output"] += int(usage.get("output_tokens", 0) or 0)
        etype = str(ev.get("type", ""))
        if etype in {"error", "turn.failed"}:
            errors.append(json.dumps(ev))
        item = ev.get("item")
        if isinstance(item, dict):
            itype = str(item.get("type", ""))
            key = (item.get("id"), itype)
            if itype == "agent_message" and item.get("text"):
                final = item["text"]
            if "web_search" in itype and key not in seen:
                web += 1
            if itype == "command_execution" and item.get("command") and key not in seen:
                commands.append(str(item["command"]))
            if item.get("id") is not None:
                seen.add(key)
    tokens["total"] = tokens["input"] + tokens["output"]
    return {"tokens": tokens, "commands": commands, "errors": errors, "final": final,
            "web_searches": web}


# ---------------------------------------------------------------- the kit

PHASE_KEYS = ("prompt", "answer_key", "overlay", "regression_phases",
              "estimate_tokens_per_run", "estimate_minutes_per_run")


def load_kit(kit: Path) -> dict:
    """Read kit.json. A one-phase case may put prompt/answer_key at the top."""
    data = read_json(kit / "kit.json")
    data["_dir"] = str(kit)
    if "phases" not in data:
        if "prompt" not in data or "answer_key" not in data:
            raise ConfigError(f"{kit / 'kit.json'}: needs prompt and answer_key (or phases)")
        data["phases"] = {"main": {k: data[k] for k in PHASE_KEYS if k in data}}
    targets = data.get("targets") or ([data["target_md"]] if data.get("target_md") else [])
    if not targets:
        raise ConfigError(f"{kit / 'kit.json'}: needs targets (the MD files the coach may change)")
    data["targets"] = [norm(t) for t in targets]
    data["target_md"] = data["targets"][0]
    return data


def kit_phase(kit: dict, phase: str | None) -> str:
    if not phase:
        return next(iter(kit["phases"]))
    if phase not in kit["phases"]:
        raise ConfigError(f"unknown phase {phase}; kit has {', '.join(kit['phases'])}")
    return phase


def snapshot(root: Path) -> dict:
    out = {}
    for path in Path(root).rglob("*"):
        if path.is_file():
            out[norm(str(path.relative_to(root)))] = sha256_file(path)
    return out


def make_instance(kit: dict, phase: str, system: Path, target: str, md_file: Path | None,
                  dest: Path) -> None:
    """Fresh clean instance: kit instance + phase overlay + needed system files."""
    kit_dir = Path(kit["_dir"])
    if dest.exists():
        raise FileExistsError(f"{dest} exists; every run needs a fresh folder")
    shutil.copytree(kit_dir / kit.get("instance_dir", "instance"), dest)
    overlay = kit["phases"][phase].get("overlay")
    if overlay:
        shutil.copytree(kit_dir / overlay, dest, dirs_exist_ok=True)
    sys_dest = dest / kit.get("system_dir", "bSmart-System")
    for rel in dict.fromkeys(list(kit.get("targets", [])) + list(kit.get("system_files", []))):
        src = Path(system) / rel
        if src.is_file():
            (sys_dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, sys_dest / rel)
    # md_file: one candidate file for `target`, or a {target: file} map
    overrides = md_file if isinstance(md_file, dict) else ({target: md_file} if md_file is not None else {})
    for rel, src in overrides.items():
        (sys_dest / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, sys_dest / rel)


def file_reads(commands, files, workdir: Path) -> list[str]:
    """Known files named in shell commands, in order (best effort)."""
    wd = norm(str(workdir)).lower().rstrip("/") + "/"
    names = sorted(files, key=len, reverse=True)
    reads = []
    for cmd in commands:
        text = re.sub(r"(?<![.\w])\./", "", norm(cmd).lower().replace(wd, ""))
        taken, found = [], []
        for rel in names:
            for m in re.finditer(re.escape(rel.lower()), text):
                if any(s <= m.start() < e for s, e in taken):
                    continue
                before = text[m.start() - 1] if m.start() > 0 else " "
                if before.isalnum() or before in "-_./":
                    continue
                taken.append((m.start(), m.end()))
                found.append((m.start(), rel))
        reads += [rel for _, rel in sorted(found)]
    return reads


# The CLI's own shell launcher, e.g. "C:\\Program Files\\PowerShell\\7\\pwsh.exe" -Command ...
SHELL_WRAPPER = re.compile(
    r"""^\s*(?:"[^"]*?(?:pwsh|powershell|cmd|bash|sh|zsh)(?:\.exe)?"|\S*?(?:pwsh|powershell|cmd|bash|sh|zsh)(?:\.exe)?)"""
    r"""(?:\s+-\w+)*?\s+(?:-command|-c|/c|-lc)\s+""", re.I)


def outside_paths(commands, workdir: Path) -> list[str]:
    """Absolute paths outside the run folder that commands touched (contamination)."""
    wd = norm(str(workdir)).lower()
    found = []
    for cmd in commands:
        cmd = SHELL_WRAPPER.sub("", cmd, count=1)
        for m in re.finditer(r"((?<![\w/:])[a-zA-Z]:[\\/][^\s'\"|;]+|(?<![\w.:/])/(?:home|users|workspace|mnt|e|c)/[^\s'\"|;]+)", cmd):
            p = norm(m.group(1)).lower()
            if not p.startswith(wd):
                found.append(m.group(1))
    return found


def run_once(kit: dict, phase: str, settings: dict, system: Path, target: str, md_file,
             run_dir: Path) -> dict:
    work = run_dir / "work"
    make_instance(kit, phase, system, target, md_file, work)
    before = snapshot(work)
    prompt = (Path(kit["_dir"]) / kit["phases"][phase]["prompt"]).read_text(encoding="utf-8")
    call = call_agent(settings, "improve_worker", work, prompt, run_dir / "log")
    after = snapshot(work)
    created = sorted(k for k in after if k not in before)
    modified = sorted(k for k in after if k in before and after[k] != before[k])
    reads = list(dict.fromkeys(file_reads(call["commands"], list(before), work)))
    record = {"phase": phase, "run_dir": str(run_dir), "exit": call["exit"],
              "seconds": call["seconds"], "tokens": call["tokens"], "model": call["model"],
              "created": created, "modified": modified, "reads": reads,
              "outside": outside_paths(call["commands"], work),
              "web_searches": call["web_searches"], "final": call["final"],
              "quota_stop": call["quota_stop"], "env_blocked": call["env_blocked"]}
    write_json(run_dir / "run.json", record)
    return record


def run_phase(kit: dict, phase: str, settings: dict, system: Path, target: str, md_file,
              out: Path, runs: int, spent: dict) -> list[dict]:
    """Run `runs` fresh runs, at most `parallel` at a time, under the token cap."""
    cap = settings["token_cap_case"]
    per_run = kit["phases"][phase].get("estimate_tokens_per_run", 0)
    jobs = max(1, min(int(settings.get("parallel", 2)), 2))
    results, pending = [], list(range(1, runs + 1))
    out.mkdir(parents=True, exist_ok=True)
    while pending:
        batch = pending[:jobs]
        pending = pending[jobs:]
        avg = max(per_run, (spent["total"] // max(1, spent["runs"])) if spent["runs"] else 0)
        if spent["total"] + avg * len(batch) > cap:
            raise QuotaStop(f"token cap {cap} would be passed (spent {spent['total']})")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as pool:
            futures = [pool.submit(run_once, kit, phase, settings, system, target, md_file,
                                   out / f"run{n}") for n in batch]
            batch_results = [f.result() for f in futures]
        for r in batch_results:
            spent["total"] += r["tokens"]["total"]
            spent["runs"] += 1
            results.append(r)
        if any(r["quota_stop"] for r in batch_results):
            raise QuotaStop("the agent CLI reported a plan or rate limit")
    return results


# ---------------------------------------------------------------- grading

def _new_notes(run: dict, globs) -> list[str]:
    return [p for p in run["created"] if match_any(p, globs) and is_note(p)]


def grade_row(row: dict, run: dict, work: Path, terms, allow) -> str:
    """Return 'pass', 'fail', or 'judged' for one script row."""
    check = row["check"]
    ign = row.get("ignore_reads", [])
    reads = [r for r in run["reads"] if not match_any(r, ign)]
    changed = run["created"] + run["modified"]
    text = lambda p: (work / p).read_text(encoding="utf-8", errors="replace")  # noqa: E731
    if check == "judged":
        return "judged"
    if check == "must_write":
        for p in _new_notes(run, row["paths"]) + [m for m in run["modified"] if match_any(m, row["paths"]) and is_note(m)]:
            body = text(p).lower()
            if all(s.lower() in body for s in row.get("contains_all", [])):
                return "pass"
        return "fail"
    if check == "indexed":
        for p in _new_notes(run, row["paths"]):
            idx = work / Path(p).parent / "index.md"
            if not idx.is_file() or Path(p).name not in idx.read_text(encoding="utf-8", errors="replace"):
                return "fail"
            parent_idx = work / Path(p).parent.parent / "index.md"
            topic = Path(p).parent.name + "/"
            if parent_idx.is_file() and topic not in parent_idx.read_text(encoding="utf-8", errors="replace"):
                return "fail"
        return "pass"
    if check == "noise":
        notes = _new_notes(run, row["paths"])
        if len(notes) > row.get("max_new_notes", 2):
            return "fail"
        sources = [p for p in snapshot(work) if match_any(p, row.get("sources", []))]
        for p in notes:
            body = text(p)
            if words(body) > row.get("max_words", 150):
                return "fail"
            if leak_hits(body, row.get("forbidden_terms", []), []):
                return "fail"
            for s in sources:
                if difflib.SequenceMatcher(None, body, text(s)).ratio() > row.get("max_copy_ratio", 0.6):
                    return "fail"
        return "pass"
    if check == "writes_only":
        return "pass" if all(match_any(p, row["paths"]) for p in changed) else "fail"
    if check == "leak_free":
        hits = []
        for p in changed:
            if match_any(p, row["paths"]):
                hits += leak_hits(text(p), terms + row.get("terms", []), allow)
        return "fail" if hits else "pass"
    if check in ("reads_first", "knowledge_first"):
        # first read matches `first`; every `must_see` file is read before any `before` file
        first = row.get("first", row.get("knowledge", []))
        must_see = row.get("must_see", row.get("indexes", []))
        if not reads or not match_any(reads[0], first):
            return "fail"
        first_src = next((i for i, r in enumerate(reads) if match_any(r, row.get("before", []))), len(reads))
        seen = set(reads[:first_src])
        return "pass" if all(i in seen for i in must_see) else "fail"
    if check == "must_read":
        return "pass" if all(any(match_any(r, [g]) for r in reads) for g in row["paths"]) else "fail"
    if check == "max_reads":
        bad = [r for r in reads if match_any(r, row.get("forbidden", []))]
        return "pass" if len(reads) <= row["limit"] and not bad else "fail"
    if check == "no_web_search":
        return "pass" if run["web_searches"] == 0 else "fail"
    if check == "file_contains":
        # any created or modified file (index files too) matching paths holds every string
        for p in changed:
            if match_any(p, row["paths"]):
                body = text(p).lower()
                if all(x.lower() in body for x in row.get("contains_all", [])):
                    return "pass"
        return "fail"
    if check == "file_excludes":
        # no created or modified file matching paths contains any of `any`
        for p in changed:
            if match_any(p, row["paths"]) and any(x.lower() in text(p).lower() for x in row["any"]):
                return "fail"
        return "pass"
    if check == "answer_excludes":
        ans = (run.get("final") or "").lower()
        return "fail" if any(x.lower() in ans for x in row["any"]) else "pass"
    if check == "answer_contains":
        ans = (run.get("final") or "").lower()
        return "pass" if all(s.lower() in ans for s in row["all"]) else "fail"
    if check == "no_writes":
        return "pass" if not [p for p in changed if match_any(p, row["paths"])] else "fail"
    if check == "no_outside_reads":
        return "pass" if not run.get("outside") else "fail"
    raise ValueError(f"unknown check {check}")


def grade_runs(key: dict, runs: list[dict], terms, allow, judged: dict | None = None) -> dict:
    """Grade every row over every run; judged rows come from the checker."""
    judged = judged or {}
    table = {}
    for row in key["rows"]:
        marks = []
        for i, run in enumerate(runs):
            if run["exit"] not in (0,):
                marks.append("fail")
                continue
            mark = grade_row(row, run, Path(run["run_dir"]) / "work", terms, allow)
            if mark == "judged":
                mark = judged.get(row["id"], {}).get(str(i + 1), "judged")
            marks.append(mark)
        table[row["id"]] = marks
    need = key.get("pass_runs", 2)
    row_pass = {rid: sum(m == "pass" for m in marks) >= min(need, len(marks)) for rid, marks in table.items()}
    score = sum(m == "pass" for marks in table.values() for m in marks)
    confirmed = [rid for rid, marks in table.items() if sum(m == "fail" for m in marks) >= min(need, len(marks))]
    flaky = [rid for rid, marks in table.items() if 0 < sum(m == "fail" for m in marks) < min(need, len(marks))]
    return {"marks": table, "row_pass": row_pass, "bar_met": all(row_pass.values()),
            "score": score, "max_score": len(table) * len(runs), "confirmed": confirmed,
            "flaky": flaky}


# ---------------------------------------------------------------- guard + diff

def guard_snapshot(files) -> dict:
    return {str(f): sha256_file(Path(f)) for f in files}


def guard_verify(manifest: dict) -> list[str]:
    changed = []
    for f, digest in manifest.items():
        if not Path(f).is_file() or sha256_file(Path(f)) != digest:
            changed.append(f)
    return changed


def change_blocks(old: str, new: str) -> int:
    """Number of separate changed regions (lines within 3 of each other merge)."""
    sm = difflib.SequenceMatcher(None, old.splitlines(), new.splitlines())
    spans = [(i1, i2) for tag, i1, i2, _, _ in sm.get_opcodes() if tag != "equal"]
    blocks, last = 0, None
    for i1, i2 in spans:
        if last is None or i1 - last > 3:
            blocks += 1
        last = i2
    return blocks


def write_diff(old: Path, new: Path, out: Path, title: str = "") -> dict:
    a = old.read_text(encoding="utf-8").splitlines()
    b = new.read_text(encoding="utf-8").splitlines()
    html = difflib.HtmlDiff(wrapcolumn=80).make_file(a, b, f"live: {old.name}", f"candidate: {new.name}",
                                                     context=True, numlines=4)
    if title:
        html = html.replace("<body>", f"<body><h2>{title}</h2>", 1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    old_t, new_t = "\n".join(a), "\n".join(b)
    return {"html": str(out), "word_delta": words(new_t) - words(old_t),
            "blocks": change_blocks(old_t, new_t)}


# ---------------------------------------------------------------- score history

def history_path(settings: dict) -> Path:
    """The instance's score history (never in bSmart-System)."""
    return Path(settings["_instance"]) / "State" / settings.get("history_file", "bimprove-history.jsonl")


def score_record(kit: dict, phase: str, mode: str, settings: dict, g: dict, tokens: int,
                 outcome: str, extra: dict | None = None) -> dict:
    m = settings["models"]
    rec = {"date": now(), "case": kit.get("name", Path(kit["_dir"]).name),
           "case_version": str(kit.get("version", "0")), "phase": phase, "mode": mode,
           "targets": kit["targets"],
           "models": {r: " ".join(x for x in (m[r]["model"], m[r]["effort"]) if x)
                      for r in ROLES if m[r]["model"]},
           "score": g.get("score"), "max_score": g.get("max_score"), "bar_met": g.get("bar_met"),
           "marks": g.get("marks", {}), "row_pass": g.get("row_pass", {}),
           "tokens": tokens, "outcome": outcome}
    rec.update(extra or {})
    return rec


def append_history(settings: dict, rec: dict) -> None:
    path = history_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_history(settings: dict) -> list[dict]:
    path = history_path(settings)
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def last_score(settings: dict, case: str, phase: str) -> dict | None:
    """Latest live-MD score for this case and phase (any version)."""
    recs = [r for r in read_history(settings) if r.get("case") == case and r.get("phase") == phase
            and r.get("marks")]
    return recs[-1] if recs else None


def compare_scores(prev: dict | None, now_rec: dict) -> dict:
    """Per-row change against the previous record: regressions, gains, same."""
    if not prev:
        return {"previous": None, "regressed": [], "gained": [], "note": "first score for this case"}
    reg, gain = [], []
    for rid, ok in now_rec["row_pass"].items():
        marks = now_rec["marks"].get(rid, [])
        if "judged" in marks or "judged" in prev.get("marks", {}).get(rid, []):
            continue  # not graded in one of the two runs
        before = prev.get("row_pass", {}).get(rid)
        if before is True and not ok:
            reg.append(rid)
        elif before is False and ok:
            gain.append(rid)
    note = []
    if prev.get("case_version") != now_rec["case_version"]:
        note.append(f"case version changed {prev.get('case_version')} -> {now_rec['case_version']}")
    if prev.get("models") != now_rec["models"]:
        note.append("models changed")
    return {"previous": {k: prev.get(k) for k in ("date", "case_version", "models", "score", "max_score")},
            "score": f"{prev.get('score')} -> {now_rec['score']}", "regressed": reg, "gained": gain,
            "note": "; ".join(note)}


def run_regress(args) -> int:
    """Rerun a case with the live MDs, no coach; grade, record, compare with the last score."""
    ext = Path(__file__).resolve().parent
    settings = load_settings(Path(args.instance))
    if args.max_parallel:
        settings["parallel"] = args.max_parallel
    need = ("improve_worker",) if args.no_checker else ROLES
    problems = check_settings(settings, need=need)
    if problems:
        print("\n".join(problems))
        return EXIT_CONFIG
    kit = load_kit(Path(args.kit))
    phase = kit_phase(kit, args.phase)
    key = read_json(Path(kit["_dir"]) / kit["phases"][phase]["answer_key"])
    terms, allow = load_denylist(args.denylist or settings.get("_denylist"), kit.get("leak_terms"))
    out = Path(args.out)
    spent = {"total": 0, "runs": 0}
    prev = last_score(settings, kit.get("name", Path(kit["_dir"]).name), phase)
    try:
        runs = run_phase(kit, phase, settings, Path(args.system), kit["target_md"], None,
                         out / "runs", args.runs, spent)
        if runs and all(r.get("env_blocked") for r in runs):
            print("stop:not_an_md_problem:environment")
            return EXIT_CONFIG
        judged = {}
        if not args.no_checker:
            chk = run_checker(settings, ext, key, runs, out, "regress", "")
            spent["total"] += chk["tokens"]
            judged = chk["verdict"].get("judged", {})
    except QuotaStop as exc:
        print(f"stop:quota ({exc})")
        return EXIT_QUOTA
    g = grade_runs(key, runs, terms, allow, judged)
    rec = score_record(kit, phase, "regress", settings, g, spent["total"],
                       "pass" if g["bar_met"] else "fail")
    cmp = compare_scores(prev, rec)
    rec["compare"] = cmp
    append_history(settings, rec)
    write_json(out / "score.json", rec)
    print(json.dumps({"case": rec["case"], "phase": phase, "score": f"{g['score']}/{g['max_score']}",
                      "regressed": cmp["regressed"], "gained": cmp["gained"], "note": cmp["note"],
                      "tokens": spent["total"]}))
    return EXIT_FINDINGS if cmp["regressed"] else EXIT_OK


# ---------------------------------------------------------------- the case

def decide(history: list[dict], max_rounds: int = 3, stall_limit: int = 2) -> str:
    """Next step from the graded history (index 0 = baseline)."""
    base = history[0]
    if base.get("not_md"):
        return "stop:not_an_md_problem"
    if base["bar_met"]:
        return "stop:baseline_passes"
    if not base["confirmed"]:
        return "stop:not_an_md_problem:flaky"
    if len(history) > 1 and history[-1]["bar_met"]:
        return "stop:improved"
    best, stall = base["score"], 0
    for h in history[1:]:
        if h["score"] > best:
            best, stall = h["score"], 0
        else:
            stall += 1
        if stall >= stall_limit:
            return "stop:no_improvement"
    if len(history) - 1 >= max_rounds:
        return "stop:max_rounds"
    return "continue"


def failure_brief(key: dict, graded: dict, checker_reasons: str) -> str:
    lines = []
    for row in key["rows"]:
        if row["id"] in key.get("held_out", []):
            continue
        if not graded["row_pass"][row["id"]]:
            lines.append(f"- {row['id']}: expected: {row['says']} (runs: {', '.join(graded['marks'][row['id']])})")
    return "\n".join(lines) + ("\n\nChecker notes:\n" + checker_reasons.strip() if checker_reasons.strip() else "")


def run_summary(runs: list[dict]) -> str:
    parts = []
    for i, r in enumerate(runs, 1):
        work = Path(r["run_dir"]) / "work"
        files = []
        for p in r["created"] + r["modified"]:
            if p.lower().endswith(".md"):
                body = (work / p).read_text(encoding="utf-8", errors="replace")[:1500]
                files.append(f"--- {p} ---\n{body}")
        parts.append(f"## Run {i}\nReads (in order): {r['reads']}\nWeb searches: {r['web_searches']}\n"
                     f"Created: {r['created']}\nModified: {r['modified']}\nFinal answer:\n{(r['final'] or '')[:1500]}\n"
                     + "\n".join(files))
    return "\n\n".join(parts)


def parse_verdict(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except ValueError:
        return {}


def run_checker(settings, ext: Path, key: dict, runs, case_dir: Path, label: str, md_diff: str) -> dict:
    rules = (ext / "checker.md").read_text(encoding="utf-8")
    judged = [r for r in key["rows"] if r["check"] == "judged"]
    prompt = (f"{rules}\n\n# Answer key (judged rows)\n{json.dumps(judged, indent=2)}\n\n"
              f"# All rows\n{json.dumps([{'id': r['id'], 'says': r['says']} for r in key['rows']], indent=2)}\n\n"
              f"# MD change under test\n{md_diff or '(none: live MD)'}\n\n# Runs\n{run_summary(runs)}\n")
    cdir = case_dir / "checker" / label
    cdir.mkdir(parents=True, exist_ok=True)
    call = call_agent(settings, "checker", cdir, prompt, cdir / "log", sandbox="read-only")
    verdict = parse_verdict(call["final"])
    write_json(cdir / "verdict.json", verdict)
    return {"verdict": verdict, "tokens": call["tokens"]["total"], "seconds": call["seconds"],
            "quota_stop": call["quota_stop"]}


def run_coach(settings, ext: Path, base: dict, brief: str, case_dir: Path, n: int) -> dict:
    """base: {target: current best file}. One target -> ./candidate.md; several -> ./files/<target>."""
    cdir = case_dir / "candidates" / f"c{n}"
    cdir.mkdir(parents=True, exist_ok=True)
    files = {}
    if len(base) == 1:
        (rel, src), = base.items()
        files[rel] = cdir / "candidate.md"
        shutil.copy2(src, files[rel])
        task = (f"Edit ./candidate.md in this folder (a copy of the live `{rel}`). Make exactly ONE change.")
    else:
        for rel, src in base.items():
            files[rel] = cdir / "files" / rel
            files[rel].parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, files[rel])
        listing = "\n".join(f"- ./files/{rel}" for rel in base)
        task = ("These are copies of the live files you may change:\n" + listing +
                "\nPick the ONE file whose wording best explains the failures and make exactly ONE change "
                "in it. Leave the other files untouched.")
    rules = (ext / "coach.md").read_text(encoding="utf-8")
    prompt = (f"{rules}\n\n# Your task\n{task} Then write one line to ./reason.txt saying what you "
              f"changed and why.\n\n# What went wrong\n{brief}\n")
    call = call_agent(settings, "coach", cdir, prompt, cdir / "log")
    return {"dir": cdir, "files": files, "tokens": call["tokens"]["total"], "seconds": call["seconds"],
            "quota_stop": call["quota_stop"]}


def run_case(args) -> int:
    ext = Path(__file__).resolve().parent
    settings = load_settings(Path(args.instance))
    if args.max_parallel:
        settings["parallel"] = args.max_parallel
    problems = check_settings(settings)
    if problems:
        print("\n".join(problems))
        return EXIT_CONFIG
    kit = load_kit(Path(args.kit))
    phase = kit_phase(kit, args.phase)
    key_path = Path(kit["_dir"]) / kit["phases"][phase]["answer_key"]
    key = read_json(key_path)
    system = Path(args.system)
    targets = kit["targets"]
    target = targets[0]
    live = {t: system / t for t in targets}
    missing = [str(p) for p in live.values() if not p.is_file()]
    if missing:
        raise ConfigError(f"target MD not found: {', '.join(missing)}")
    case_dir = Path(args.out)
    case_dir.mkdir(parents=True, exist_ok=True)
    terms, allow = load_denylist(args.denylist or settings.get("_denylist"), kit.get("leak_terms"))
    protected = [key_path, ext / "checker.md", *live.values(), Path(args.denylist or settings.get("_denylist") or key_path)]
    manifest = guard_snapshot(protected)
    write_json(case_dir / "guard.json", manifest)
    spent = {"total": 0, "runs": 0}
    state = {"phase": phase, "started": now(), "worker": settings["models"]["improve_worker"],
             "coach": settings["models"]["coach"], "checker": settings["models"]["checker"],
             "token_cap": settings["token_cap_case"], "history": [], "outcome": None}
    progress = lambda: write_json(case_dir / "case.json", {**state, "tokens_spent": spent["total"]})  # noqa: E731
    best, best_label = dict(live), "live"
    try:
        runs = run_phase(kit, phase, settings, system, target, None, case_dir / "baseline",
                         args.runs, spent)
        if runs and all(r.get("env_blocked") for r in runs):
            state["outcome"] = "stop:not_an_md_problem:environment"
            state["note"] = "the agent CLI blocked the worker's commands in every run; fix the CLI setup"
            state["finished"] = now()
            progress()
            print(state["outcome"])
            return EXIT_CONFIG
        chk = run_checker(settings, ext, key, runs, case_dir, "baseline", "")
        spent["total"] += chk["tokens"]
        if chk["quota_stop"]:
            raise QuotaStop("checker hit a plan or rate limit")
        judged = chk["verdict"].get("judged", {})
        g = grade_runs(key, runs, terms, allow, judged)
        g.update({"label": "baseline", "not_md": chk["verdict"].get("md_problem") is False and not g["bar_met"],
                  "checker_notes": chk["verdict"].get("notes", ""),
                  "minutes": round(sum(r["seconds"] for r in runs) / 60, 1)})
        state["history"].append(g)
        progress()
        n = 0
        while (step := decide(state["history"], args.rounds, args.stall_limit)) == "continue":
            n += 1
            last = state["history"][-1]
            ref = state["history"][0] if best_label == "live" else next(h for h in state["history"] if h["label"] == best_label)
            brief = failure_brief(key, ref, ref.get("checker_notes", ""))
            coach = run_coach(settings, ext, best, brief, case_dir, n)
            spent["total"] += coach["tokens"]
            if coach["quota_stop"]:
                raise QuotaStop("coach hit a plan or rate limit")
            changed = guard_verify(manifest)
            if changed:
                state["outcome"] = "stop:guard_violation"
                state["guard_changed"] = changed
                progress()
                return EXIT_GUARD
            reason_file = coach["dir"] / "reason.txt"
            entry = {"label": f"c{n}", "reason": reason_file.read_text(encoding="utf-8").strip()
                     if reason_file.is_file() else ""}
            changed_t = [t for t in targets if coach["files"][t].read_bytes() != best[t].read_bytes()]
            if len(changed_t) != 1:
                entry.update({"bar_met": False, "score": -1, "confirmed": last["confirmed"],
                              "rejected": f"{len(changed_t)} files changed; exactly one allowed"})
                state["history"].append(entry)
                progress()
                continue
            ct = changed_t[0]
            cand = dict(best)
            cand[ct] = coach["files"][ct]
            d = write_diff(best[ct], cand[ct], coach["dir"] / "diff.html", f"Candidate c{n}: {ct}")
            entry.update({"file": ct, **d})
            if d["blocks"] != 1:
                entry.update({"bar_met": False, "score": -1, "confirmed": last["confirmed"],
                              "rejected": f"{d['blocks']} change regions; exactly one allowed"})
                state["history"].append(entry)
                progress()
                continue
            md_diff = "".join(difflib.unified_diff(best[ct].read_text(encoding="utf-8").splitlines(True),
                                                   cand[ct].read_text(encoding="utf-8").splitlines(True),
                                                   f"live/{ct}", f"candidate/{ct}"))
            cruns = run_phase(kit, phase, settings, system, target, cand, case_dir / f"c{n}-runs",
                              args.runs, spent)
            regress = []
            for rphase in kit["phases"][phase].get("regression_phases", []):
                regress += run_phase(kit, rphase, settings, system, target, cand,
                                     case_dir / f"c{n}-regress-{rphase}", 1, spent)
            chk = run_checker(settings, ext, key, cruns, case_dir, f"c{n}", md_diff)
            spent["total"] += chk["tokens"]
            if chk["quota_stop"]:
                raise QuotaStop("checker hit a plan or rate limit")
            gc = grade_runs(key, cruns, terms, allow, chk["verdict"].get("judged", {}))
            reg_ok = True
            for rphase in kit["phases"][phase].get("regression_phases", []):
                rkey = read_json(Path(kit["_dir"]) / kit["phases"][rphase]["answer_key"])
                rr = [r for r in regress if r["phase"] == rphase]
                rg = grade_runs(rkey, rr, terms, allow, {})
                fails = [k for k, ok in rg["row_pass"].items() if not ok and
                         next(x for x in rkey["rows"] if x["id"] == k)["check"] != "judged"]
                gc.setdefault("regression", {})[rphase] = rg["marks"]
                reg_ok = reg_ok and not fails
            if not reg_ok:
                gc["bar_met"] = False
                gc["score"] = min(gc["score"], last.get("score", 0))
            gc.update(entry)
            gc["checker_notes"] = chk["verdict"].get("notes", "")
            gc["quality_ok"] = chk["verdict"].get("quality_ok", True)
            if gc["quality_ok"] is False:
                gc["bar_met"] = False
            gc["minutes"] = round(sum(r["seconds"] for r in cruns + regress) / 60, 1)
            state["history"].append(gc)
            if gc["score"] > max(h.get("score", -1) for h in state["history"][:-1]):
                best, best_label = cand, f"c{n}"
            progress()
        state["outcome"] = step
    except QuotaStop as exc:
        state["outcome"] = f"stop:quota ({exc})"
        state["finished"] = now()
        progress()
        record_case(kit, phase, settings, state, spent)
        print(state["outcome"])
        return EXIT_QUOTA
    state["best"] = best_label
    if best_label != "live":
        final = case_dir / "final"
        final.mkdir(exist_ok=True)
        changed_t = [t for t in targets if best[t] != live[t]]
        state["changed_files"] = changed_t
        for t in changed_t:
            shutil.copy2(best[t], final / Path(t).name)
            html = "side-by-side.html" if len(changed_t) == 1 else f"side-by-side-{Path(t).stem}.html"
            state.setdefault("final_diffs", {})[t] = write_diff(live[t], best[t], final / html,
                                                              f"{t}: live vs {best_label}")
        state["final_diff"] = state["final_diffs"][changed_t[0]]
    state["finished"] = now()
    progress()
    record_case(kit, phase, settings, state, spent)
    print(state["outcome"])
    return EXIT_OK


def record_case(kit, phase, settings, state, spent) -> None:
    """Append the live-MD baseline score (and the best candidate's) to the history."""
    hist = state.get("history") or []
    if not hist:
        return
    best = next((h for h in hist if h.get("label") == state.get("best")), None)
    extra = {"rounds": len(hist) - 1}
    if best and best.get("label") != "baseline":
        extra["best"] = {"label": best["label"], "file": best.get("file"), "score": best.get("score"),
                         "marks": best.get("marks", {})}
    append_history(settings, score_record(kit, phase, "case", settings, hist[0], spent["total"],
                                          state.get("outcome") or "", extra))


# ---------------------------------------------------------------- card + PR text

def estimate(kit: dict, phase: str, settings: dict, runs: int = 3, rounds: int = 3) -> dict:
    p = kit["phases"][phase]
    w, m = p.get("estimate_tokens_per_run", 60000), p.get("estimate_minutes_per_run", 4)
    c, cm = kit.get("estimate_coach_tokens", 50000), kit.get("estimate_coach_minutes", 3)
    k, km = kit.get("estimate_checker_tokens", 50000), kit.get("estimate_checker_minutes", 3)
    jobs = max(1, min(int(settings.get("parallel", 2)), 2))
    waves = -(-runs // jobs)
    base_t, base_m = runs * w + k, waves * m + km
    round_t, round_m = c + runs * w + k, cm + waves * m + km
    return {"baseline_tokens": base_t, "baseline_minutes": base_m, "round_tokens": round_t,
            "round_minutes": round_m, "max_tokens": base_t + rounds * round_t,
            "max_minutes": base_m + rounds * round_m}


def render_card(case: dict, est: dict, settings: dict) -> str:
    t = (ext_dir() / "templates" / "card.template.md").read_text(encoding="utf-8")
    vals = {k: str(v) for k, v in case.items()}
    vals.update({k: f"{v:,}" if isinstance(v, int) else str(v) for k, v in est.items()})
    vals["quota_pool"] = settings.get("quota_pool", "unknown")
    vals["token_cap"] = f"{settings.get('token_cap_case', 0):,}"
    for key, val in vals.items():
        t = t.replace("{" + key + "}", val)
    return t


def ext_dir() -> Path:
    return Path(__file__).resolve().parent


def pr_text(case: dict, target: str, terms, allow) -> tuple[str, list[str]]:
    t = (ext_dir() / "templates" / "pr.template.md").read_text(encoding="utf-8")
    hist = case.get("history", [])
    base = hist[0] if hist else {}
    best = next((h for h in hist if h.get("label") == case.get("best")), {})
    vals = {"target": target, "reason": best.get("reason", ""),
            "baseline": f"{base.get('score', '?')}/{base.get('max_score', '?')}",
            "candidate": f"{best.get('score', '?')}/{best.get('max_score', '?')}",
            "word_delta": str(case.get("final_diff", {}).get("word_delta", "?")),
            "rounds": str(len(hist) - 1)}
    for key, val in vals.items():
        t = t.replace("{" + key + "}", val)
    return t, leak_hits(t, terms, allow)


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bimprove", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("config"); p.add_argument("--instance", required=True)
    p = sub.add_parser("run")
    for a in ("--kit", "--instance", "--system", "--out"):
        p.add_argument(a, required=True)
    p.add_argument("--phase")
    p.add_argument("--runs", type=int, default=3); p.add_argument("--md")
    p = sub.add_parser("grade")
    p.add_argument("--key", required=True); p.add_argument("--runs-dir", required=True)
    p.add_argument("--denylist")
    p = sub.add_parser("guard"); p.add_argument("action", choices=["snapshot", "verify"])
    p.add_argument("--manifest", required=True); p.add_argument("files", nargs="*")
    p = sub.add_parser("diff"); p.add_argument("old"); p.add_argument("new"); p.add_argument("--out", required=True)
    p = sub.add_parser("leak"); p.add_argument("--denylist", required=True); p.add_argument("--root", required=True)
    p.add_argument("--glob", action="append")
    p = sub.add_parser("case")
    for a in ("--kit", "--instance", "--system", "--out"):
        p.add_argument(a, required=True)
    p.add_argument("--phase", help="default: the kit's first phase")
    p.add_argument("--runs", type=int, default=3); p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--stall-limit", type=int, default=2,
                   help="stop after this many rounds in a row with no gain (operator may raise it)")
    p.add_argument("--denylist"); p.add_argument("--max-parallel", type=int, default=0)
    p = sub.add_parser("regress")
    for a in ("--kit", "--instance", "--system", "--out"):
        p.add_argument(a, required=True)
    p.add_argument("--phase"); p.add_argument("--runs", type=int, default=3)
    p.add_argument("--denylist"); p.add_argument("--max-parallel", type=int, default=0)
    p.add_argument("--no-checker", action="store_true", help="skip judged rows (no checker tokens)")
    p = sub.add_parser("history"); p.add_argument("--instance", required=True); p.add_argument("--case")
    p = sub.add_parser("card")
    p.add_argument("--kit", required=True); p.add_argument("--phase")
    p.add_argument("--instance", required=True); p.add_argument("--what", default="")
    p.add_argument("--md", default="")
    p = sub.add_parser("pr-text"); p.add_argument("--case", required=True); p.add_argument("--target", required=True)
    p.add_argument("--denylist")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "config":
            s = load_settings(Path(args.instance))
            probs = check_settings(s)
            for role in ROLES:
                print(f"{role}: {s['models'][role]['model'] or 'NOT SET'} {s['models'][role]['effort']}".rstrip())
            print("\n".join(probs) if probs else "config ok")
            return EXIT_CONFIG if probs else EXIT_OK
        if args.cmd == "run":
            s = load_settings(Path(args.instance))
            probs = check_settings(s, need=("improve_worker",))
            if probs:
                print("\n".join(probs)); return EXIT_CONFIG
            kit = load_kit(Path(args.kit))
            spent = {"total": 0, "runs": 0}
            res = run_phase(kit, kit_phase(kit, args.phase), s, Path(args.system), kit["target_md"],
                            Path(args.md) if args.md else None, Path(args.out), args.runs, spent)
            print(json.dumps({"runs": len(res), "tokens": spent["total"]}))
            return EXIT_OK
        if args.cmd == "grade":
            key = read_json(Path(args.key))
            runs = [read_json(p) for p in sorted(Path(args.runs_dir).glob("run*/run.json"))]
            terms, allow = load_denylist(args.denylist, key.get("leak_terms"))
            g = grade_runs(key, runs, terms, allow)
            print(json.dumps(g, indent=2))
            return EXIT_OK if g["bar_met"] else EXIT_FINDINGS
        if args.cmd == "guard":
            if args.action == "snapshot":
                write_json(Path(args.manifest), guard_snapshot(args.files)); return EXIT_OK
            changed = guard_verify(read_json(Path(args.manifest)))
            print("\n".join(changed) if changed else "guard ok")
            return EXIT_GUARD if changed else EXIT_OK
        if args.cmd == "diff":
            print(json.dumps(write_diff(Path(args.old), Path(args.new), Path(args.out)))); return EXIT_OK
        if args.cmd == "leak":
            terms, allow = load_denylist(args.denylist)
            hits = scan_leaks(Path(args.root), args.glob, terms, allow)
            for h in hits:
                print(f"library_leak {h['file']}:{h['line']} term={h['term']}")
            return EXIT_FINDINGS if hits else EXIT_OK
        if args.cmd == "case":
            return run_case(args)
        if args.cmd == "regress":
            return run_regress(args)
        if args.cmd == "history":
            for r in read_history(load_settings(Path(args.instance))):
                if args.case and r.get("case") != args.case:
                    continue
                print(f"{r.get('date')}  {r.get('case')} v{r.get('case_version')} {r.get('phase')} "
                      f"{r.get('mode')}: {r.get('score')}/{r.get('max_score')} {r.get('outcome')} "
                      f"tokens={r.get('tokens')} models={r.get('models')}")
            return EXIT_OK
        if args.cmd == "card":
            s = load_settings(Path(args.instance))
            kit = load_kit(Path(args.kit))
            ph = kit_phase(kit, args.phase)
            print(render_card({"what": args.what, "md": args.md or ", ".join(kit["targets"]),
                               "phase": ph}, estimate(kit, ph, s), s))
            return EXIT_OK
        if args.cmd == "pr-text":
            case = read_json(Path(args.case))
            terms, allow = load_denylist(args.denylist)
            text, hits = pr_text(case, args.target, terms, allow)
            print(text)
            if hits:
                print(f"LEAK: {hits} - fix the text before any push", file=sys.stderr)
                return EXIT_FINDINGS
            return EXIT_OK
    except ConfigError as exc:
        print(exc)
        return EXIT_CONFIG
    except QuotaStop as exc:
        print(f"stop:quota ({exc})")
        return EXIT_QUOTA
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
