# bProtective Cursor plugin

Optional Cursor `beforeShellExecution` adapter for the shared bProtective core. It is not live-tested in Cursor.

The hook command tries `python3 ./scripts/before_shell.py`, then `python`, then `py -3`. Point Cursor at:

`bSmart-System/integrations/cursor/bprotective-plugin`

Installing this plugin does not turn protection on. Confirm `bprotective on` with `bprotective yes <ID>`.

Checked against the Cursor hooks documentation on 2026-10-08: stdin carries `command`, and stdout returns `permission` of `allow`, `deny`, or `ask`. Escalate maps to `ask`. Block maps to `deny`. While protection is off, the hook returns `allow`.

Cursor's own docs list `ask` as a real permission. Separate community reports say current Cursor builds do not enforce `ask` and only honor `deny`. This adapter was not run inside Cursor, so that gap is unverified here. For a shell that cannot be hooked reliably, use the pre-flight check in `integrations/bprotective/README.md`.
