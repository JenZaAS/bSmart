---
name: projcet
description: Alias for the bSmart /project command.
---

# /projcet

From the workspace root, run the shared bSmart adapter. Reply with its stdout unchanged. Do not summarize it or confirm a rename, retire, or delete yourself.

```text
python bSmart-System/integrations/bsmart_client_adapter.py projcet $ARGUMENTS
```

`$ARGUMENTS` means the words the user typed after the command. If that placeholder is still literal, use those words instead. Preserve quotes around multi-word names. Do not add paths, environment variables, or flags. If `python` is unavailable, use `python3`.

If the output asks for confirmation, show the Yes and No lines and wait.
