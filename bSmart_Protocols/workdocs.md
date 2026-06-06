# bSmart Protocol: workdocs

```yaml
protocol:
  id: workdocs
  title: Workdocs
  purpose: Track non-trivial work across sessions without relying on chat memory.
```

```yaml
paths:
  active_workdocs: /workspace/bSmart/Workdocs
  library: /workspace/bSmart/Library
  template: /workspace/bSmart-System/bSmart_Templates/WORKDOC.template.md
```

```yaml
create_when:
  - task_spans_sessions
  - troubleshooting
  - external_verification_required
  - system_or_deployment_structure_changes
  - user_requests_workdoc
```
