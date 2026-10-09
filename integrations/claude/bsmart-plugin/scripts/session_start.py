#!/usr/bin/env python3
"""Session-start hook for Cursor, Codex, and Claude bSmart plugins.

Reads the client hook payload on stdin, runs bStart.py once, and writes the
client's context JSON on stdout. Command-line arguments cannot choose paths.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

CLIENTS = ("cursor", "claude", "codex")


def find_workspace(start: Path) -> Path | None:
    try:
        current = start.expanduser().resolve()
    except OSError:
        return None
    for candidate in (current, *current.parents):
        if (candidate / "bSmart-System" / "bStart.py").is_file():
            return candidate
    return None


def read_payload() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def workspace_from(data: dict) -> Path | None:
    candidates: list[Path] = []
    roots = data.get("workspace_roots") or []
    if isinstance(roots, str):
        roots = [roots]
    if isinstance(roots, list):
        candidates.extend(Path(str(item)) for item in roots if item)
    for key in ("cwd", "workspace_root"):
        value = data.get(key)
        if isinstance(value, str) and value:
            candidates.append(Path(value))
    for name in ("BSMART_WORKSPACE", "CURSOR_PROJECT_DIR", "CLAUDE_PROJECT_DIR"):
        value = os.environ.get(name)
        if value:
            candidates.append(Path(value))
    candidates.append(Path.cwd())
    for candidate in candidates:
        found = find_workspace(candidate)
        if found is not None:
            return found
    return None


def run_bstart(workspace: Path) -> tuple[str, int]:
    script = workspace / "bSmart-System" / "bStart.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--root", str(workspace)],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=90,
        check=False,
        shell=False,
    )
    text = (completed.stdout or "") + (("\n" + completed.stderr) if completed.stderr else "")
    return text.strip(), completed.returncode


def context_text(startup: str, returncode: int, client: str | None = None) -> str:
    status = "bStart.py finished." if returncode == 0 else "bStart.py reported a problem."
    text = (
        "bSmart client startup hook already ran bStart.py. Do not run it again. "
        "In the first reply, preserve the startup lines and command-help lines.\n"
        f"{status}\n\n{startup}"
    )
    if client == "cursor":
        text += (
            "\n\nWrap that visible startup block in a fenced code block with no language tag "
            "so Markdown does not collapse the line breaks."
        )
    return text


def payload(client: str, text: str) -> dict:
    if client == "cursor":
        return {"additional_context": text}
    if client in {"claude", "codex"}:
        return {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": text,
            }
        }
    raise ValueError(f"Unknown client: {client}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit bSmart session-start context.")
    parser.add_argument("--client", required=True, choices=CLIENTS)
    args = parser.parse_args(argv)
    data = read_payload()
    workspace = workspace_from(data)
    if workspace is None:
        text = context_text(
            "bSmart startup hook could not find bSmart-System/bStart.py. "
            "Run python3 bSmart-System/bStart.py from the workspace root. "
            "If python3 is missing or fails, use python bSmart-System/bStart.py (or py -3 bSmart-System/bStart.py on Windows).",
            1,
            args.client,
        )
    else:
        try:
            startup, code = run_bstart(workspace)
        except (OSError, subprocess.SubprocessError) as exc:
            startup, code = f"bStart.py could not be started: {exc}", 1
        text = context_text(startup, code, args.client)
    sys.stdout.buffer.write(json.dumps(payload(args.client, text), ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
