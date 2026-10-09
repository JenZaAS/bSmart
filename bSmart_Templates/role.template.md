# bSmart role (deprecated)

Roles are deprecated. Do not create a new role file from this template.

A historical role file looked like this:

```yaml
role:
  name: <role-name>
  id: <role-id>
state:
  active_project: <project-slug> | none
  active_workstream: <workstream-name> | none
  updated_at_utc: <ISO-8601 UTC timestamp>
  current_focus: <short current focus>
  task_handoff: <short resume point>
```

Those fields were the old instance-wide selector's project, workstream, focus, and handoff. They are not active state. The replacement is a session project plus `projects/<project>/handoff.md`. See `bSmart_Docs/roles-deprecated.md`.
