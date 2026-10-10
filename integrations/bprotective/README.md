# bProtective

bProtective is an optional, off-by-default command guard. One Python core decides allow, escalate, or block. Hermes, Cursor, Claude Code, Codex, and a generic shell assistant all use that core. Nothing in setup or startup turns the guard on. The operator confirms `on` and `off` separately.

The core has no third-party dependencies. It covers POSIX shells and Windows PowerShell/cmd, including commands aimed at the operator's own PC (`E:\` paths, `Remove-Item -Recurse`, `rd /s`, `format`, `del /s`, `diskpart`, `Set-ExecutionPolicy`, `reg delete`).

## Decisions

| Decision | Meaning |
|---|---|
| `allow` | The guard is off, or the command is not blocked or escalated. |
| `escalate` | Risky. Do not run it until the operator approves that command. |
| `block` | Catastrophic. Refuse it. Do not ask for an override. |

A missing state file is off only when this install was never armed. After the operator has confirmed on, a missing state file fails closed while the outside armed record or the local marker remains. A state file that reads off without a recorded operator-confirmed off also fails closed. Unreadable state fails closed for a shell command. An invalid instance config fails closed only while the guard is on. A missing config file adds nothing. A missing core blocks terminal commands.

bProtective protects against accidental catastrophic commands. It does not protect against a deliberately adversarial agent. Deleting the outside armed record as well as the state file and the local marker looks like a fresh install.

## CLI

```text
python3 bSmart-System/scripts/bprotective status
python3 bSmart-System/scripts/bprotective on
python3 bSmart-System/scripts/bprotective yes <ID>
python3 bSmart-System/scripts/bprotective off
python3 bSmart-System/scripts/bprotective no <ID>
python3 bSmart-System/scripts/bprotective recover
python3 bSmart-System/scripts/bprotective check --json -- "<command>"
```

If `python3` is missing or fails, use `python`, or `py -3` on Windows. `check` exit codes are `0` allow, `1` escalate, `2` block, and `3` usage error. `--json` prints `decision`, `rule_key`, `reason`, `message`, and `enabled`. CLI and hook output is encoding-safe on a cp1252 console.

Confirmation to turn the guard on or off expires after 300 seconds. The operator runs both the request and `yes <ID>` in their own terminal. Agent hooks block `on`, `off`, `yes`, `no`, and `recover`, so the assistant cannot confirm a change. When the state file is missing and the armed record remains, the operator runs `bprotective recover` and then `bprotective yes <ID>` in that same terminal. That writes a clean off state.

## Generic assistants

Some desktop assistants can run a shell and cannot install a pre-execution hook. For those, bProtective is a pre-flight check. The short instructions live in `bSmart_Protocols/operations.md` under `bprotective_preflight` and are pointed to from `bSmart.md`.

While protection is on, before a command on the operator's machines, or before a destructive command:

1. Run `bprotective check --json -- "<exact command>"`.
2. `allow`: follow the normal bSmart approval rules.
3. `escalate`: do not run it. Quote the reason and ask the operator in chat. Run that exact command only after they explicitly approve it.
4. `block`: refuse. Do not run it and do not ask for an override.

Do not turn the guard on unless the operator asks.

The check is not an operation tag. After work that already happened, tag it as `bSmart [<scope>]: <ops> - <note of at most 5 words>`. Inside a project, report the read, write, and delete that happened. Outside a project, report write and delete only. A blocked or not-run command is not a write or delete. Do not tag the check, log or history writes, pure chat, or web lookups.

## Instance config

Optional paths and patterns belong in the per-instance content root from `scripts/bsmart_instance.py` (`default_content_root`), in the instance next to the checkout:

```text
State/bprotective.yaml
```

`bprotective.config.json` is accepted instead. If both files exist, the guard fails closed while it is on. The file cannot set `enabled`.

```yaml
protected_paths:
  - E:\demo\data
extra_block:
  - key: custom-wipe
    pattern: "Invoke-CustomWipe"
    reason: custom wipe
extra_escalate: []
```

A recursive delete that names a protected path is blocked. Another mutating command that names it is escalated. Reads are allowed. Unquoted Windows paths are fine; put complicated regular expressions in the JSON form so backslashes stay literal. Extra pattern keys are letters, digits, `_`, and `-`.

## State

`BPROTECTIVE_STATE_FILE` wins when set. Otherwise the core uses `State/bprotective.json` under the content root from `bsmart_instance.default_content_root`. If that file does not exist yet and `~/.hermes/bprotective.json` does, the Hermes file remains the state file so an already-confirmed Hermes install stays on. With no content root, the default is `~/.hermes/bprotective.json`.

`BSMART_CONTENT_ROOT` overrides the content root. `BSMART_SYSTEM_ROOT` is the checkout passed to `default_content_root`. Neither path is symlink-resolved, so a symlinked checkout stays on the instance that launched it. `BPROTECTIVE_CONFIG_FILE` overrides the config path. `BPROTECTIVE_CORE` is the directory that contains `hook.py` when a copied plugin cannot see the checkout.

Turning the guard on also writes `bprotective.json.armed` beside the state file and records that absolute path in `~/.bprotective/armed.json`. `BPROTECTIVE_ARMED_FILE` overrides the outside record. The outside record is what still fails closed after `State/` itself is deleted. An operator-confirmed off records that fact and clears the local marker. `bprotective recover` is the operator command when the state file is gone and one of those armed records remains.

## Adapters

| Adapter | Mechanism | Escalate | Live-tested |
|---|---|---|---|
| Hermes | `pre_tool_call` on terminal tools, `/bprotective` | Hermes `approve` gate | Behavior covered by unit tests. Not re-tested against a live Hermes gateway in this change. |
| CLI / generic assistant | `scripts/bprotective check` | Ask the operator in chat | CLI tested locally. |
| Cursor | `beforeShellExecution`, plus `preToolUse` for `Write\|Delete` | `permission: "ask"` for a shell escalation. A guard-file edit is `deny`. | Not live-tested. Payload checked against Cursor hooks docs on 2026-10-10. |
| Claude Code | `PreToolUse` matcher `Bash\|PowerShell` and `Write\|Edit\|MultiEdit` | `permissionDecision: "ask"` for a shell escalation. A guard-file edit is `deny`. | Not live-tested. Same unverified status the repo already uses for the Claude bSmart plugin. |
| Codex | `PreToolUse` and `PermissionRequest`, including `apply_patch` | PreToolUse denies blocks and returns no decision for escalations, so PermissionRequest can prompt. It never returns `ask` and never includes a token. | Not live-tested. |

Cursor's documented `beforeShellExecution` result is `permission` `allow`, `deny`, or `ask`, with `user_message` and `agent_message`. Input used here is `command`. `preToolUse` uses the same permission object. Its matcher is `Write|Delete`, which the Cursor hooks docs list as file-tool names. This adapter sets `failClosed`, so a crash or a missing core blocks the action. The hook command is `./scripts/run_hook.cmd`. That file is a POSIX shell script with a Windows batch section, so Cursor on Windows does not need `sh`. If Python is missing, the launcher exits 0 and prints `permission: allow`, and `failClosed` does not block every command. `BPROTECTIVE_CORE` is the directory that contains `hook.py` when the plugin was copied out of the checkout. Community reports say Cursor currently ignores `ask` and only enforces `deny`. This repo has not reproduced that. Until it is live-tested, treat Cursor escalation as unverified. The file-edit hook is unverified too. The armed record still fails closed if an edit lands.

Claude Code `PreToolUse` input uses `tool_input.command` for a shell and `tool_input.file_path` for Write, Edit, and MultiEdit. The adapter returns `hookSpecificOutput.permissionDecision` `deny` or `ask` for a shell. A write to the state file, the local marker, or the outside armed record is `deny`. The shell matcher includes `PowerShell` because Windows sessions may not emit `Bash`. Empty stdout leaves Claude's own permission flow in place for allowed commands. The hook command is `run_hook.cmd` under `${CLAUDE_PLUGIN_ROOT}`. It does not call `sh -c`. On Windows without Git Bash, Claude runs hook commands with PowerShell, and a `.cmd` file runs there without `sh`. If Python is missing, the launcher exits 0 with no decision. Checked against the Claude Code hooks reference on 2026-10-10.

Codex `PreToolUse` can deny, or allow with `updatedInput`. The docs say `permissionDecision: "ask"` is parsed and then ignored, and the tool call continues. Returning `ask` would fail open. The Codex adapter denies a block and returns no decision for an escalation, so `PermissionRequest` still runs. It does not put a confirmation token in the message. `PermissionRequest` denies blocks and writes to the guard files. For an escalation it returns no decision, so the operator prompt stays, and it never returns `allow`. Codex full-auto mode has no approval prompt, so an ask-class command such as `git push`, `pip install`, `docker`, or `gh pr` can run while protection is on. The Windows command is `commandWindows` and uses PowerShell, because `||` and `${PLUGIN_ROOT}` do not work in Windows PowerShell 5.1. A non-zero hook exit is not retried with another interpreter. Codex still requires the operator to trust the hook definition before it runs. Checked against the Codex hooks guide on 2026-10-10. The `apply_patch` matcher was not live-tested.

Installing a hook plugin does not enable protection. While the guard is off, Cursor receives `permission: allow` and Claude/Codex receive no decision.
