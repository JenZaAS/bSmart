# bSmart Protocol: roles (deprecated) and file concurrency

```yaml
protocol:
  id: roles-and-concurrency
  title: Deprecated roles and file concurrency
  purpose: Record that roles are deprecated, and define narrow file-write collision handling for shared project files.
  use_when:
    - reading an old Roles/ file or current_role.md
    - writing a shared project file another session may be editing
    - migrating an instance that still has role files
  deprecated: true
  replaced_by: session-scoped project selection and per-project handoff files
```

## Roles are deprecated

Roles were an instance-wide hat that owned the active project. `Roles/current_role.md` was one selector for the whole instance, so choosing a role in one session changed it for every other session. That model is retired.

As of this version:

- Projects are the unit of work.
- The active project and optional workstream are session-scoped. They live in the conversation, not in a shared file other sessions read as their selection.
- A session with no selection is in Free mode and must not guess a project.
- Focus and handoff that must survive a session live in the project: `handoff.md`, or `workstreams/<name>/handoff.md` when a workstream is in use.
- Select a project with `/project <name>` or by asking in the conversation. `/role` only prints a short deprecation notice.

Old files under `Roles/`, including `current_role.md` and `<role-id>_role.md`, are historical. Do not load them as the active project. Do not recreate the selector. If a migration question is still open, ask the operator; do not invent a destination. The upgrade backup under `.bsmart-upgrade-backups/<stamp>/roles-migration/` is what a rollback restores.

See `bSmart_Docs/roles-deprecated.md` for how to read a leftover role file.

## Shared projects

- Several sessions may work in the same project.
- Selecting a project does not lock the project.
- Sessions that need separate handoffs in one project use workstreams.
- bSmart prevents only narrow simultaneous writes to the same file through `.bLock`.

## File locks

```yaml
file_lock:
  suffix: .bLock
  example: INDEX.md.bLock
  scope: one target file only
  create: atomic exclusive create immediately before writing
  contents:
    - session or project label when available
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

1. Check for `<target>.bLock` before writing a shared file such as `projects/INDEX.md` or a project `handoff.md`.
2. If absent, create it atomically; failure means another writer won the race.
3. If present, wait three seconds and retry up to three times.
4. If still present, report the lock owner/age when readable and ask whether to override.
5. Never delete another session's lock automatically merely because it looks old.
6. If the operator authorizes override, preserve the existing lock information, perform the write, and remove only the lock associated with the completed write.
7. A lock protects collision timing, not semantic correctness. Verify the resulting file.

## Migration

`bsmart-update` and `bsmart-instance-upgrade` back up `Roles/` and legacy `bSmart_State.md` before merging unambiguous focus and handoff text into the matching project handoff. Existing handoff text is kept. Unknown fields stay in the review file, not the handoff. Ambiguous cases are asked and are not guessed. The migration marker is written even when questions remain; delete `bSmart/State/role-migration.json` and run `bsmart-instance-upgrade` again to retry a skipped handoff. Restore removes that marker.
