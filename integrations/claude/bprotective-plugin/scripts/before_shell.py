#!/usr/bin/env python3
"""Claude Code PreToolUse entry. Not live-tested in Claude Code."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

ADAPTER = "claude"


def resolve_hook() -> Path | None:
    """Find hook.py in-tree or via BPROTECTIVE_CORE when this plugin is copied."""
    candidates: list[Path] = []
    env = os.environ.get("BPROTECTIVE_CORE")
    if env:
        root = Path(env).expanduser()
        candidates.append(root / "hook.py")
        candidates.append(root)
    here = Path(__file__).resolve()
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "bprotective" / "hook.py")
    for parent in here.parents:
        candidates.append(parent / "integrations" / "bprotective" / "hook.py")
        candidates.append(parent / "bprotective" / "hook.py")
    for candidate in candidates:
        if candidate.is_file() and candidate.name == "hook.py":
            return candidate
    return None


def _deny_missing() -> None:
    message = "bProtective core failed to load. Set BPROTECTIVE_CORE to the directory that contains hook.py."
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    }
    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    hook = resolve_hook()
    if hook is None:
        _deny_missing()
        raise SystemExit(2)
    sys.argv = [str(hook), "--adapter", ADAPTER, *sys.argv[1:]]
    runpy.run_path(str(hook), run_name="__main__")
