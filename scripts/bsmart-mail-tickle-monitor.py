#!/usr/bin/env python3
"""Hermes cron monitor source for bSmart bMail wake markers.

Install/copy this under the target agent's Hermes scripts directory
(usually /opt/data/scripts/) and use it as a Hermes cron monitor_script.
It prints stable JSON only when wake markers are pending; empty stdout means
no pending bMail and monitor-mode suppresses the agent run.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    mailbox = os.environ.get("BSMART_MAIL_ROOT", "/mail")
    bmail = os.environ.get("BSMART_BMAIL", "/workspace/bSmart-System/scripts/bMail")
    if not Path(bmail).exists():
        # Stable output: if bMail is missing this should wake the agent/admin once.
        print(f"bMail unavailable: {bmail}")
        return 0
    proc = subprocess.run(
        [sys.executable, bmail, "tickle", "--mailbox", mailbox],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    elif proc.stderr:
        # Stable enough for repeated failures; useful during setup.
        print(f"bMail tickle error: {proc.stderr.strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
