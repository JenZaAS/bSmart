# bSmart current role (deprecated)

Do not create this file. `current_role.md` was the instance-wide role selector. It is not a session's project.

Historical shape:

```yaml
role_selection:
  current_role: general
  updated_at_utc: <ISO-8601 UTC timestamp>
```

The active project now lives only in the session. Use `/project`.
