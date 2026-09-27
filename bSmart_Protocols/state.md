# bSmart Protocol: legacy state migration

```yaml
protocol:
  id: state
  title: Legacy state migration
  purpose: Migrate deprecated bSmart_State.md information into the selected role file.
  use_when:
    - migrating an existing bSmart instance to role-owned state
    - inspecting an older instance that still has bSmart_State.md
  active_state_owner: /workspace/bSmart-System/bSmart_Protocols/roles-and-concurrency.md
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
    - override the selected role
    - compete with role-owned active state
    - be loaded as normal startup context
```

## Migration procedure

1. Confirm that the operator wants to migrate the instance to role-owned state.
2. Select the destination role, defaulting to `general_role`.
3. Read the legacy file and classify only project, workstream, focus, and handoff information.
4. Preserve unknown or ambiguous fields for operator review; do not invent replacements.
5. Write the accepted information into the selected role file.
6. Verify the role file and report the migration result.
7. Retire or remove the legacy file only after explicit approval and successful verification.

## Compatibility rule

Until migration is explicitly completed, the legacy file may remain as a stored historical/compatibility artifact. It is never an active source of truth. New role-aware commands and startup behavior must use the selected role file and `roles-and-concurrency.md`.

Project creation, selection, workstream changes, and Free Mode behavior must be updated in the selected role file. The old global-state model must not be extended.
