# bProtective Codex plugin

This package is not live-tested in Codex. Codex does have a `PreToolUse` hook. The plugin ships `hooks/hooks.json` with matcher `Bash|PowerShell`, using the same layout as `integrations/codex/bsmart-plugin/`. Codex does not run the hook until the operator reviews and trusts that definition.

Checked against the Codex hooks documentation on 2026-10-08. `tool_input.command` is the shell text. `permissionDecision: "deny"` blocks. `permissionDecision: "ask"` is documented as unsupported: Codex records a hook error and still runs the command. This adapter therefore does not return `ask`.

- A block is denied. The message has no confirmation token.
- An escalation is denied in `PreToolUse` with no confirmation token. `PermissionRequest` leaves the operator prompt in place and does not auto-allow.
- Shell commands that turn the guard on or off, or that write, delete, or move its state file, are denied.
- An allowed command prints no decision.
- Windows uses `commandWindows` with `$env:PLUGIN_ROOT`. The POSIX command does not retry the hook after a non-zero exit.

The generic pre-flight protocol in `bSmart_Protocols/operations.md` remains the fallback when the hook is not trusted. Installing the plugin does not turn protection on.
