---
name: role
description: Roles are deprecated. Show the notice that points to /project.
---

# /role

From the workspace root, run the shared bSmart adapter. Reply with its stdout unchanged. Do not create a role or change the session project.

```text
python3 bSmart-System/integrations/bsmart_client_adapter.py role $ARGUMENTS
```

`$ARGUMENTS` means the words the user typed after the command. If that placeholder is still literal, use those words instead. With no arguments, pass nothing so the adapter shows `/role help`. Do not add paths, environment variables, or flags. If `python3` is missing or fails, use `python` (or `py -3` on Windows).
