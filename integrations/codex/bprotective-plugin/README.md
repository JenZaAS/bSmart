# bProtective Codex plugin

This package is not live-tested in Codex. Codex does have a `PreToolUse` hook. The plugin ships `hooks/hooks.json` with matcher `Bash|PowerShell|apply_patch`, using the same layout as `integrations/codex/bsmart-plugin/`. Codex does not run the hook until the operator reviews and trusts that definition.

Checked against the Codex hooks documentation on 2026-10-10. `tool_input.command` is the shell text. `apply_patch` is matched so a patch that updates the state file, the local armed marker, or the outside armed record is denied. `permissionDecision: "deny"` blocks. `permissionDecision: "ask"` is documented as unsupported: Codex records a hook error and still runs the command. This adapter therefore does not return `ask`.

- A block is denied. The message has no confirmation token.
- An escalation returns no `PreToolUse` decision, so `PermissionRequest` can show the operator prompt. `PermissionRequest` does not auto-allow and does not add a token.
- Codex full-auto mode has no approval prompt. Ask-class commands such as `git push`, `pip install`, `docker`, and `gh pr` can run while protection is on.
- Shell commands that turn the guard on or off, or that write, delete, or move its state file, are denied.
- An allowed command prints no decision.
- Windows uses `commandWindows` with `$env:PLUGIN_ROOT` and calls Python directly. The POSIX command does not retry the hook after a non-zero exit.
- A missing core exits 2 with a deny payload.

The generic pre-flight protocol in `bSmart_Protocols/operations.md` remains the fallback when the hook is not trusted. Installing the plugin does not turn protection on. The operator runs both `bprotective on` and `bprotective yes <ID>` in their own terminal.

bProtective protects against accidental catastrophic commands, not against a deliberately adversarial agent.
