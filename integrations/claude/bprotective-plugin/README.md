# bProtective Claude plugin

This package is not yet verified in the Claude app. It follows the Claude Code plugin layout so it can be tested later with:

```text
claude --plugin-dir bSmart-System/integrations/claude/bprotective-plugin
```

The `PreToolUse` hook matches `Bash|PowerShell` and runs `before_shell.py` with `python3`, then `python`, then `py -3`.

Checked against the Claude Code hooks reference on 2026-10-08. Shell commands arrive in `tool_input.command`. A block returns `permissionDecision: "deny"`. An escalation returns `permissionDecision: "ask"`. An allowed command prints no decision, so Claude's own permission rules still apply. The PowerShell matcher is required on Windows when Bash is not registered.

Installing the plugin does not turn protection on. Confirm `bprotective on` with `bprotective yes <ID>`.
