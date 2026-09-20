# bSmart Protocol: startup hooks

```yaml
protocol:
  id: startup-hooks
  title: Startup hooks
  purpose: Keep client-specific startup files short, identical, and separate from bSmart system content.
  helper: /workspace/bSmart-System/scripts/bsmart-hooks
  helper_local: ./bSmart-System/scripts/bsmart-hooks
```

## Hook files

Use the same content from `bSmart_Templates/AGENTS.md` for every supported startup hook:

- `AGENTS.md`
- `HERMES.md`
- `CLAUDE.md`
- `.hermes.md`
- `.cursorrules`

`init` creates the canonical `AGENTS.md`, `HERMES.md`, and `CLAUDE.md` files when they are missing. It never overwrites existing hooks.

`reset` is an explicit operator command. It resets the canonical hooks and any other supported hook files that already exist.

`check` reports whether existing hooks match the shared template.

After updating bSmart-System in an existing workspace, run:

```bash
python3 /workspace/bSmart-System/scripts/bsmart-instance-upgrade
```

This explicit upgrade helper backs up differing canonical hooks, installs the workspace-root `bStart.py`, and synchronizes `HERMES.md`, `AGENTS.md`, and `CLAUDE.md`. It does not modify bSmart instance content or state.

The standard post-pull command is:

```bash
python3 /workspace/bSmart-System/scripts/bsmart-update
```

It performs the startup integration repair, create-only content repair, and project-integration verification without pulling Git. It also reports known outdated instance-profile sections with a proposed narrow patch; applying that patch requires operator approval.

## Runtime defaults

Resolve the workspace root as follows:

1. Use an explicit `--root` when supplied.
2. In Docker, use `/workspace`.
3. Locally, use the current directory containing the startup hook.

Resolve the shared system and instance content relative to that root when absolute container paths do not exist:

```text
system: ./bSmart-System
content: ./bSmart
extensions: ./bSmart-Extensions
projects: ./projects
sandboxes: ./sandboxes, only when present
```

The system manifest remains the authority after the hook loads. Docker/local differences belong in path resolution and instance-local configuration, not duplicated hook text.

## Agent commands

When the operator says `initialize bSmart`, run the normal bSmart setup and then `hooks init` behavior.

When the operator says `reset AGENTS.md`, interpret it as:

```text
reset all supported startup hooks in the current workspace
```

Run:

```bash
python3 /workspace/bSmart-System/scripts/bsmart-hooks reset
# local:
python3 ./bSmart-System/scripts/bsmart-hooks reset
```

Do not reset hooks merely because they differ. Inspect and ask first unless the operator explicitly requested reset.
