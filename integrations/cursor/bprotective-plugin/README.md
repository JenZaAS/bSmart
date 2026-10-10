# bProtective Cursor plugin

Optional Cursor adapter for the shared bProtective core. It is not live-tested in Cursor.

`beforeShellExecution` checks shell commands. `preToolUse` with matcher `Write|Delete` denies an edit whose path is the state file, the local armed marker, `~/.bprotective`, or the outside armed record. Cursor's hooks docs list those tool names. `afterFileEdit` cannot deny an edit, so it is not used. The armed record still fails closed if an edit lands another way.

The hook command is `./scripts/run_hook.cmd`. That file starts with a POSIX shell and also contains a Windows batch section. Git checks it out with CRLF so `cmd.exe` can find `goto` labels, and the shell lines end with a comment so that carriage return is not part of the command. Windows does not need `sh`. It runs `py -3`, then `python`, then `python3`, and exits with that process's code. It does not try a second interpreter after a non-zero exit. If Python is missing, it prints `permission: allow` with `user_message` and `agent_message` saying bProtective could not run, and exits 0, so `failClosed` does not block every command while protection is off. `failClosed` still blocks a crash, a timeout, or a missing core. `BPROTECTIVE_CORE` can point at the directory that contains `hook.py` if this plugin is copied out of the checkout. Point Cursor at:

`bSmart-System/integrations/cursor/bprotective-plugin`

Installing this plugin does not turn protection on. The operator runs both `bprotective on` and `bprotective yes <ID>` in their own terminal. Agent hooks block those commands.

Checked against the Cursor hooks documentation on 2026-10-10: shell stdin carries `command`, and stdout returns `permission` of `allow`, `deny`, or `ask`. Escalate maps to `ask`. Block maps to `deny`. While protection is off, a shell command returns `allow`. A guard-file edit is still denied.

Cursor's own docs list `ask` as a real permission. Separate community reports say current Cursor builds do not enforce `ask` and only honor `deny`. `preToolUse` documents `ask` as not enforced. This adapter was not run inside Cursor, so that gap is unverified here. For a shell that cannot be hooked reliably, use the pre-flight check in `integrations/bprotective/README.md`.

bProtective protects against accidental catastrophic commands, not against a deliberately adversarial agent.
