---
name: project
description: List, select, create, rename, retire, or delete bSmart projects.
---

# /project

From the workspace root, run the shared bSmart adapter. Reply with its stdout unchanged. Do not summarize it, choose a different project action, or confirm a rename, retire, or delete yourself.

```text
python3 bSmart-System/integrations/bsmart_client_adapter.py project $ARGUMENTS
```

`$ARGUMENTS` means the words the user typed after the command. If that placeholder is still literal, use those words instead. Preserve quotes around multi-word names. Do not add paths or flags. The adapter remembers this client's project between commands; do not set environment variables for it. Leaving a project requires `handoff:` and a short wrap-up in those arguments, for example `Beta handoff: parser is green`. Delete, retire, and rename can name the project exactly: `delete NAME`, `retire NAME`, `rename CURRENT NEW`. If `python3` is missing or fails, use `python` (or `py -3` on Windows).

If the output asks for confirmation, show the Yes and No lines and wait.
