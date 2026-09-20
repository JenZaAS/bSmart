# bSmart role

```yaml
role:
  name: <role-name>
  file: ./bSmart/Roles/<role-id>_role.md
  status: active | inactive
  startup_selection: exactly one role is loaded at startup
  default_role: general
```

## Role scope

A role is a session-scoped operational hat, not a replacement identity for the AI instance and not a project lock.

```yaml
identity:
  instance_identity_source: ../bSmart_Agent.md
  role_focus: <short operational focus>

state:
  active_project: <project-slug> | none
  active_workstream: <workstream-name> | none
  updated_at_utc: <ISO-8601 UTC timestamp>
  current_focus: <short current focus>
  task_handoff: <short resume point>
```

The role file owns the active project, workstream, focus, and role-specific handoff. It may contain role-specific preferences and pointers, but not secrets or generic system procedures.

## Startup behavior

- A General role always exists as the fallback role.
- Exactly one role file is selected and loaded during startup.
- If General is the only available role, do not announce the role unless useful for clarity.
- An explicitly selected role takes precedence over defaults or legacy state.
- Role selection changes which role file is read; it does not require a log-off procedure.
- A role may work with any project permitted by the operator.

## Shared projects

Multiple roles may work with the same project. bSmart does not lock an entire project to one role. The operator is responsible for avoiding conflicting simultaneous edits; bSmart provides file-level collision protection through the role/concurrency protocol.

## Legacy state

`bSmart_State.md` is not active role state. During migration, read it only to extract the last known project/workstream/focus into the selected role file, verify the migration, and then retire the legacy file.
