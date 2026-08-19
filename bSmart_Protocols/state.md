# bSmart Protocol: State

```yaml
protocol:
  id: state
  title: State
  purpose: Define the canonical bSmart instance state file and active-project / Free Mode rules.
  use_when:
    - reading current project state
    - changing active project
    - entering or leaving Free Mode
    - reconciling duplicate or stale state claims
  depends_on:
    - /workspace/bSmart/bSmart_State.md
    - /workspace/bSmart-System/bSmart_Protocols/projects.md
```

## State ownership

```yaml
canonical_state_file:
  container_path: /workspace/bSmart/bSmart_State.md
  local_path: ./bSmart/bSmart_State.md
  owns:
    - mode
    - active_project_short_name
    - updated_at_utc
    - short_notes_about_current_focus
  rule: The global active/current project is stored only here. Other bSmart files may refer to this file or describe project-local status, but must not duplicate or override the global active/current project selection.
```

## State shape

Preferred content shape:

```markdown
# bSmart state

This file tracks the current/active project selection for bSmart.

- Mode: `Project` | `Free Mode`
- Active project (short name): `<project-slug>` | `none`
- Updated at (UTC): `<YYYY-MM-DD HH:MM UTC>`

Notes:
- <optional short current-focus note>
```

## Reading state

1. Read `bSmart_State.md` when present.
2. Treat it as the source of truth for global active/current project.
3. If the file is missing, follow the manifest/setup missing-content behavior.
4. If another file appears to claim a different global active/current project, treat that as drift in the other file unless there is direct evidence that `bSmart_State.md` itself is stale.

## Changing state

Only change the global active/current project when the operator explicitly selects a project, creates a project and chooses to open it, or asks to enter Free Mode.

When changing state:
1. Update `Mode`, `Active project (short name)`, and `Updated at (UTC)` in `bSmart_State.md`.
2. Keep project-specific TODOs/project files project-local; do not mirror the global active/current project there.
3. Log meaningful state changes in the local bSmart log when appropriate.

## Free Mode

```yaml
free_mode:
  mode: Free Mode
  active_project_short_name: none
  behavior:
    - do not write task artifacts into a project folder unless the operator later selects or creates a project
    - use global bSmart TODO/workdocs for non-project handoff when needed
```

## Drift handling

When a maintenance or Dreaming workflow finds duplicate or conflicting active-project claims:
- preserve `bSmart_State.md` as canonical unless there is direct evidence it is stale;
- normalize or flag the duplicate claim in the other file;
- ask before changing `bSmart_State.md` unless the operator already gave a clear state-change command;
- avoid copying the full state rule into feature-specific protocols; link back to this protocol instead.
