# Roles are deprecated

```yaml
note:
  kind: library
  status: deprecated
  since: 0.1.45-draft
  replacement: session-scoped projects and project handoff files
```

Roles used to be the way one bSmart instance kept an active project. Each role file under `Roles/<role-id>_role.md` stored `active_project`, `active_workstream`, `current_focus`, and `task_handoff`. `Roles/current_role.md` selected one of those files for every session at once.

That selector is retired. A session chooses a project for itself with `/project <name>` or in conversation. The choice is not written to a shared selector. Durable focus and handoff now live in the project:

```text
projects/<project>/handoff.md
projects/<project>/workstreams/<workstream>/handoff.md
```

When you find an old role file in instance content:

- Treat it as history, not as the current session's project.
- Read `active_project`, `active_workstream`, `current_focus`, and `task_handoff` as the note that was current when the role was last used.
- The same facts, when migration succeeded, are appended in that project's handoff under `Migrated from <role>`.
- Unknown fields stay in `bSmart/State/role-migration-review.md` and in the backup `review.md`. They are not copied into the project handoff.
- `current_role.md` only named which role file the old selector pointed at. It is not a project.
- `/role` does not change state. Use `/project`.

The pre-migration copy is in `.bsmart-upgrade-backups/<stamp>/roles-migration/`. Restoring that backup puts `Roles/` back and restores a handoff only when the file still matches what migration wrote. A handoff edited after migration is kept.

`bSmart/State/role-migration.json` is written at the end of a migration even when questions remain. A skipped non-UTF-8 handoff is not retried on the next `bsmart-update`. Delete that marker and run `bsmart-instance-upgrade` again to retry those questions. Restore deletes the marker, so the next `bsmart-update` migrates again unless the system copy is also downgraded.
