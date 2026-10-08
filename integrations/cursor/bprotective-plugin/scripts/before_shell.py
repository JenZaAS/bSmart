#!/usr/bin/env python3
"""Cursor beforeShellExecution entry. Not live-tested in Cursor."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[3] / "bprotective" / "hook.py"

if __name__ == "__main__":
    sys.argv = [str(HOOK), "--adapter", "cursor", *sys.argv[1:]]
    runpy.run_path(str(HOOK), run_name="__main__")
