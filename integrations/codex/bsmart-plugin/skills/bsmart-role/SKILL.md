---
name: bsmart-role
description: Run bSmart /role commands. Use when the user types /role, or asks to list, select, or create a bSmart role.
---

# bSmart role

From the workspace root, run the shared bSmart adapter. Reply with its stdout unchanged. Do not summarize it or invent a role.

```text
python bSmart-System/integrations/bsmart_client_adapter.py role $ARGUMENTS
```

`$ARGUMENTS` means the words the user typed after the command. If that placeholder is still literal, use those words instead. With no arguments, pass nothing so the adapter shows `/role help`. Do not add paths, environment variables, or flags. If `python` is unavailable, use `python3`.
