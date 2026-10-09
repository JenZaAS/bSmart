---
name: bsmart-startup
description: Run bSmart session startup. Use at the start of a Codex session in a bSmart workspace when the context does not already contain a bSmart — Startup block.
---

# bSmart startup

If the session already contains a `bSmart — Startup` block, do not run startup again.

Otherwise, from the workspace root, run:

```text
python3 bSmart-System/bStart.py
```

If `python3` is missing or fails, use `python` (or `py -3` on Windows). In the first reply, preserve the startup lines and command-help lines.
