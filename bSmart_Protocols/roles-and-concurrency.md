# bSmart Protocol: roles and file concurrency

```yaml
protocol:
  id: roles-and-concurrency
  title: Roles and file concurrency
  purpose: Define one-role startup state, shared-project behavior, and narrow file-write collision handling.
  use_when:
    - selecting or creating a role
    - changing a role's project or workstream
    - writing a file that another role may be editing
    - migrating legacy bSmart_State.md
```

## Role storage and selection

```yaml
roles:
  root_container: /workspace/bSmart/Roles
  root_local: ./bSmart/Roles
  selector: current_role.md
  filename: <role-id>_role.md
  default_role: general
  startup_rule: Load exactly one selected role file every session.
  recovery:
    missing_roles_directory: create directory, current_role.md, and general_role.md silently from templates
    missing_selector: create current_role.md selecting general silently
    missing_selected_role: fall back to general, create general_role.md if needed, and repair current_role.md
  general_role:
    id: general
    filename: general_role.md
    always_available: true
    silent_when_only_role: true
  state_owner:
    - active_project
    - active_workstream
    - updated_at_utc
    - current_focus
    - task_handoff
  legacy_state_file:
    path: /workspace/bSmart/bSmart_State.md
    active_use: false
    migration_only: true
```

Role state is stored in one structured Markdown file per role. Do not split one role's active state across multiple state files unless a future measured need justifies it.

## Role commands

```text
/role help             Show the complete role command list and a short explanation of roles.
/role list             List available role files.
/role set <role>       Select one role for the current session.
/role add <role>       Create a role file from the role template, then select it.
```

Role selection loads exactly one role file. The General role is always available as the fallback.

The shared runtime is exposed by `scripts/bsmart-role-core.mjs` and its JSON transport `scripts/bsmart-role.mjs`. `/role set` updates only `current_role.md`; `/role add` creates a role from the template and selects it. Project commands receive the selected role file and never parse `bSmart_State.md`.

## Project sharing

- Multiple roles may work with the same project.
- Selecting a role does not reserve or lock the entire project.
- There is no log-off procedure and no requirement to switch through another role before selecting a project.
- The operator is responsible for coordinating work that could conflict semantically.
- bSmart prevents only narrow simultaneous writes to the same file through `.bLock`.

## File locks

```yaml
file_lock:
  suffix: .bLock
  example: notes.md.bLock
  scope: one target file only
  create: atomic exclusive create immediately before writing
  contents:
    - role name
    - instance name when available
    - process/session identifier when available
    - created_at_utc
    - intended operation
  release: delete the .bLock immediately after the write and verification complete
  retry:
    wait_seconds: 3
    attempts: 3
    maximum_wait: approximately 10 seconds including the initial check
  still_locked: stop and ask the operator whether to ignore the lock and proceed
```

Rules:

1. Check for `<target>.bLock` before writing.
2. If absent, create it atomically; failure means another writer won the race.
3. If present, wait three seconds and retry up to three times.
4. If still present, report the lock owner/age when readable and ask whether to override.
5. Never delete another role's lock automatically merely because it looks old.
6. If the operator authorizes override, preserve the existing lock information, perform the write, and remove only the lock associated with the completed write.
7. A lock protects collision timing, not semantic correctness; roles must still verify the resulting file and coordinate meaning-changing edits.

## Migration from legacy state

- Read `bSmart_State.md` only during explicit migration.
- Copy active project, workstream, focus, and handoff information into `general_role.md` or the operator-selected role.
- Preserve unknown fields for review; do not invent role facts.
- Verify the new role file before retiring the legacy state file.
- Do not keep both files as competing active sources of truth.
