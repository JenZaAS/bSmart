---
name: bsmart-startup
description: Run bSmart session startup. Use when a Claude session in a bSmart workspace does not already contain a bSmart — Startup block.
---

# bSmart startup

If the session already contains a `bSmart — Startup` block, do not run startup again.

Otherwise, from the workspace root, run:

```text
python3 bSmart-System/bStart.py
```

If `python3` is missing or fails, use `python` (or `py -3` on Windows). In the first reply, preserve the startup lines and command-help lines. If startup prints a bSmart news block, relay that news briefly in the first reply, once, and do not repeat it later.
