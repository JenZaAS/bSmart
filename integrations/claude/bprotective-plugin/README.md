# bProtective Claude plugin

This package is not yet verified in the Claude app. It follows the Claude Code plugin layout so it can be tested later with:

```text
claude --plugin-dir bSmart-System/integrations/claude/bprotective-plugin
```

`PreToolUse` matches `Bash|PowerShell` for shell commands and `Write|Edit|MultiEdit` for file edits. The command is `run_hook.cmd` under `${CLAUDE_PLUGIN_ROOT}`. It does not call `sh -c`. The script runs `python3`, then `python`, then `py -3`, and does not run a second interpreter after a non-zero exit. On Windows without Git Bash, Claude runs hooks with PowerShell, and the `.cmd` file runs there. The file is checked out with CRLF so `cmd.exe` can find its labels. If Python is missing, the launcher writes `bProtective could not run because Python was not found.` to stderr and exits 0 with no decision, so a missing interpreter does not block every command.

Checked against the Claude Code hooks reference on 2026-10-10. Shell commands arrive in `tool_input.command`. File edits arrive with `tool_input.file_path`. A block returns `permissionDecision: "deny"`. A shell escalation returns `permissionDecision: "ask"`. A write to the state file, the local armed marker, or the outside armed record is denied. An allowed command prints no decision, so Claude's own permission rules still apply. The PowerShell matcher is required on Windows when Bash is not registered. A missing core exits 2 with a deny payload.

Installing the plugin does not turn protection on. The operator runs both `bprotective on` and `bprotective yes <ID>` in their own terminal. Agent hooks block those commands.

bProtective protects against accidental catastrophic commands, not against a deliberately adversarial agent.
