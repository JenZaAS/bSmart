# bProtective

bProtective is an optional, off-by-default command guard. One Python core decides allow, escalate, or block. Hermes, Cursor, Claude Code, Codex, and a generic shell assistant all use that core. Nothing in setup or startup turns the guard on. The operator confirms `on` and `off` separately.

The core has no third-party dependencies. It covers POSIX shells and Windows PowerShell/cmd, including commands aimed at the operator's own PC (`E:\` paths, `Remove-Item -Recurse`, `rd /s`, `format`, `del /s`, `diskpart`, `Set-ExecutionPolicy`, `reg delete`).

## Decisions

| Decision | Meaning |
|---|---|
| `allow` | The guard is off, or the command is not blocked or escalated. |
| `escalate` | Risky. Do not run it until the operator approves that command. |
| `block` | Catastrophic. Refuse it. Do not ask for an override. |

Missing state is off. Unreadable state fails closed for a shell command. An invalid instance config fails closed only while the guard is on. A missing config file adds nothing.

## CLI

```text
python3 bSmart-System/scripts/bprotective status
python3 bSmart-System/scripts/bprotective on
python3 bSmart-System/scripts/bprotective yes <ID>
python3 bSmart-System/scripts/bprotective off
python3 bSmart-System/scripts/bprotective no <ID>
python3 bSmart-System/scripts/bprotective check --json -- "<command>"
```

If `python3` is missing or fails, use `python`, or `py -3` on Windows. `check` exit codes are `0` allow, `1` escalate, `2` block, and `3` usage error. `--json` prints `decision`, `rule_key`, `reason`, `message`, and `enabled`. CLI and hook output is encoding-safe on a cp1252 console.

Confirmation to turn the guard on or off expires after 300 seconds. The operator sends `yes <ID>`. The assistant does not confirm a change on its own.

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

`BSMART_CONTENT_ROOT` overrides the content root. `BSMART_SYSTEM_ROOT` is the checkout passed to `default_content_root`. Neither path is symlink-resolved, so a symlinked checkout stays on the instance that launched it. `BPROTECTIVE_CONFIG_FILE` overrides the config path. `BPROTECTIVE_CORE` is the directory that contains `core.py` when a copied Hermes plugin cannot see the checkout.

## Adapters

| Adapter | Mechanism | Escalate | Live-tested |
|---|---|---|---|
| Hermes | `pre_tool_call` on terminal tools, `/bprotective` | Hermes `approve` gate | Behavior covered by unit tests. Not re-tested against a live Hermes gateway in this change. |
| CLI / generic assistant | `scripts/bprotective check` | Ask the operator in chat | CLI tested locally. |
| Cursor | `beforeShellExecution` | `permission: "ask"` | Not live-tested. Payload checked against Cursor hooks docs on 2026-10-08. |
| Claude Code | `PreToolUse` matcher `Bash\|PowerShell` | `permissionDecision: "ask"` | Not live-tested. Same unverified status the repo already uses for the Claude bSmart plugin. |
| Codex | `PreToolUse` and `PermissionRequest` | PreToolUse `deny` with no token. PermissionRequest denies blocks and leaves escalations on the operator prompt. | Not live-tested. |

Cursor's documented `beforeShellExecution` result is `permission` `allow`, `deny`, or `ask`, with `user_message` and `agent_message`. Input used here is `command`. This adapter sets `failClosed`, so a crash or a missing core blocks the shell command. `BPROTECTIVE_CORE` is the directory that contains `hook.py` when the plugin was copied out of the checkout. Community reports say Cursor currently ignores `ask` and only enforces `deny`. This repo has not reproduced that. Until it is live-tested, treat Cursor escalation as unverified.

Claude Code `PreToolUse` input uses `tool_input.command`. The adapter returns `hookSpecificOutput.permissionDecision` `deny` or `ask`. The matcher includes `PowerShell` because Windows sessions may not emit `Bash`. Empty stdout leaves Claude's own permission flow in place for allowed commands.

Codex `PreToolUse` can deny, or allow with `updatedInput`. The docs say `permissionDecision: "ask"` is parsed and then ignored, and the tool call continues. Returning `ask` would fail open. The Codex adapter denies a block or an escalation and does not put a confirmation token in that message. `PermissionRequest` denies blocks and shell attempts to change the guard. For an escalation it returns no decision, so the operator prompt stays, and it never returns `allow`. The Windows command is `commandWindows` and uses PowerShell, because `||` and `${PLUGIN_ROOT}` do not work in Windows PowerShell 5.1. A non-zero hook exit is not retried with another interpreter. Codex still requires the operator to trust the hook definition before it runs. Checked against the Codex hooks guide on 2026-10-10.

Installing a hook plugin does not enable protection. While the guard is off, Cursor receives `permission: allow` and Claude/Codex receive no decision.
