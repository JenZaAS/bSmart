---
name: bsmart-project
description: Run bSmart /project commands. Use when the user types /project, or asks to list, select, create, rename, retire, or delete a bSmart project or workstream.
---

# bSmart project

From the workspace root, run the shared bSmart adapter. Reply with its stdout unchanged. Do not summarize it, choose a different project action, or confirm a rename, retire, or delete yourself.

```text
python3 bSmart-System/integrations/bsmart_client_adapter.py project $ARGUMENTS
```

`$ARGUMENTS` means the words the user typed after the command. If that placeholder is still literal, use those words instead. Preserve quotes around multi-word names. Do not add paths, environment variables, or flags. If `python3` is not on PATH, use `python`.

If the output asks for confirmation, show the Yes and No lines and wait.
