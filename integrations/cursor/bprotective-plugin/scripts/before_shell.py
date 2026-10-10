#!/usr/bin/env python3
"""Cursor hook entry. Not live-tested in Cursor."""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

ADAPTER = "cursor"


def resolve_entry() -> Path | None:
    """Find entry.py in-tree or via BPROTECTIVE_CORE when this plugin is copied."""
    candidates: list[Path] = []
    env = os.environ.get("BPROTECTIVE_CORE")
    if env:
        root = Path(env).expanduser()
        candidates.append(root / "entry.py")
    here = Path(__file__).resolve()
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "bprotective" / "entry.py")
    for parent in here.parents:
        candidates.append(parent / "integrations" / "bprotective" / "entry.py")
        candidates.append(parent / "bprotective" / "entry.py")
    for candidate in candidates:
        if candidate.is_file() and candidate.name == "entry.py":
            return candidate
    return None


def _deny_missing() -> None:
    message = "bProtective core failed to load. Set BPROTECTIVE_CORE to the directory that contains hook.py."
    payload = {"permission": "deny", "user_message": message, "agent_message": message}
    sys.stdout.write(json.dumps(payload))


if __name__ == "__main__":
    entry = resolve_entry()
    if entry is None:
        _deny_missing()
        raise SystemExit(2)
    sys.argv = [str(entry), "--adapter", ADAPTER, *sys.argv[1:]]
    runpy.run_path(str(entry), run_name="__main__")
