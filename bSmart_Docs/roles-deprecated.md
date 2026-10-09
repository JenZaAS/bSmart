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
- Unknown fields in the role file were preserved for review. Do not drop them and do not invent replacements.
- `current_role.md` only named which role file the old selector pointed at. It is not a project.
- `/role` does not change state. Use `/project`.

The pre-migration copy is in `.bsmart-upgrade-backups/<stamp>/roles-migration/`. Restoring that backup puts `Roles/` and any handoff files the migration touched back to those bytes.
