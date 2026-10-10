#!/usr/bin/env python3
"""Shared hook launcher. Plugin scripts find this file and run it.

Cursor, Claude Code, and Codex each keep a thin before_shell.py that only
names its adapter. This file loads hook.py from the same directory.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    hook = Path(__file__).resolve().with_name("hook.py")
    sys.argv = [str(hook), *(sys.argv[1:] if argv is None else argv)]
    runpy.run_path(str(hook), run_name="__main__")


if __name__ == "__main__":
    main()
