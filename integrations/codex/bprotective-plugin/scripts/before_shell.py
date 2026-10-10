#!/usr/bin/env python3
"""Codex PreToolUse and PermissionRequest entry. Not live-tested in Codex.

Finds the shared integrations/bprotective/entry.py and runs it. The deny
payload below is only the last resort when that file cannot be found.
"""

from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

ADAPTER = "codex"
_MISSING = "bProtective core failed to load. Set BPROTECTIVE_CORE to the directory that contains hook.py."


def _entry() -> Path | None:
    candidates: list[Path] = []
    env = os.environ.get("BPROTECTIVE_CORE")
    if env:
        candidates.append(Path(env).expanduser() / "entry.py")
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "integrations" / "bprotective" / "entry.py")
        candidates.append(parent / "bprotective" / "entry.py")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


if __name__ == "__main__":
    entry = _entry()
    if entry is None:
        event = "PermissionRequest" if "--event" in sys.argv and "permission" in sys.argv else "PreToolUse"
        if event == "PermissionRequest":
            payload = {
                "hookSpecificOutput": {
                    "hookEventName": "PermissionRequest",
                    "decision": {"behavior": "deny", "message": _MISSING},
                }
            }
        else:
            payload = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": _MISSING,
                }
            }
        sys.stdout.write(json.dumps(payload))
        raise SystemExit(2)
    sys.argv = [str(entry), "--adapter", ADAPTER, *sys.argv[1:]]
    runpy.run_path(str(entry), run_name="__main__")
