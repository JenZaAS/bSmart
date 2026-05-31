# bSmart Protocol: operations

```yaml
protocol:
  id: operations
  title: Operations
  purpose: Safe action cadence, approvals, direct speech, and traceability.
```

```yaml
principles:
  read_first: true
  reversible_changes_preferred: true
  direct_speech: true
  no_confident_hallucination: true
  trace_key_decisions: true
```

```yaml
approval_events_to_log:
  - destructive_change
  - host_or_runtime_change
  - persona_change
  - system_update
  - content_migration
```

```yaml
log_target: /workspace/bSmart/bSmart_Log.md
```
