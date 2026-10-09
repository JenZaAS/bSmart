# bSmart Protocol: legacy state migration

```yaml
protocol:
  id: state
  title: Legacy state migration
  purpose: Migrate deprecated bSmart_State.md and role files into project handoffs.
  use_when:
    - migrating an existing bSmart instance off role files
    - inspecting an older instance that still has bSmart_State.md or Roles/
  active_state_owner: the session for selection; the project handoff for durable notes
```

## Deprecated file

```yaml
legacy_state_file:
  container_path: /workspace/bSmart/bSmart_State.md
  local_path: ./bSmart/bSmart_State.md
  status: deprecated_migration_only
  may_contain:
    - last known mode
    - last known active project
    - last known workstream
    - last known focus notes
  must_not:
    - override the session project
    - compete with the project handoff
    - be loaded as normal startup context
```

## Migration procedure

1. `bsmart-instance-upgrade` backs up `Roles/` and `bSmart_State.md` under `.bsmart-upgrade-backups/<stamp>/roles-migration/` before it changes a handoff.
2. For each role file and for `bSmart_State.md`, copy project, workstream, focus, and handoff into that project's `handoff.md`, or the workstream handoff when the workstream folder exists.
3. Append. Never replace existing handoff text.
4. Preserve unknown fields in the appended section. If the project or workstream folder is missing, or the file names no project but still has notes, ask. Do not create a project to make the migration fit.
5. Leave the original files in place as history. They are not a selector.
6. Restore with `bsmart-instance-upgrade --restore-session-projects <backup>` to put those bytes back.

## Compatibility rule

Legacy files may remain as history. They are never an active source of truth. Startup and `/project` use the session and the project index, not `Roles/current_role.md`.
