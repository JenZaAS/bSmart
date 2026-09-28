---
name: bsmart-startup
description: Run bSmart session startup. Use at the start of a Codex session in a bSmart workspace when the context does not already contain a bSmart — Startup block.
---

# bSmart startup

If the session already contains a `bSmart — Startup` block, do not run startup again.

Otherwise, from the workspace root, run:

```text
python bSmart-System/bStart.py
```

Use `python3` when `python` is unavailable. In the first reply, preserve the startup lines and command-help lines.
