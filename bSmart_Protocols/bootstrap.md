# bSmart Protocol: bootstrap

```yaml
protocol:
  id: bootstrap
  title: Bootstrap
  purpose: Session-start loading order and file roles.
  use_when:
    - starting a session
    - installing bSmart
    - troubleshooting bSmart autoload
  depends_on:
    - /workspace/bSmart-System/bSmart.md
    - /workspace/bSmart/bSmart_Agent.md
```

```yaml
startup_order:
  - host_framework_persona
  - /workspace/bSmart-System/bSmart.md
  - /workspace/bSmart/bSmart_Agent.md
  - /workspace/bSmart/bSmart_State.md
  - /workspace/bSmart/bSmart_TODO.md
  - relevant_protocols
```

```yaml
governance:
  system_changes: treat_as_versioned_changes
  content_changes: local_instance_state
  HERMES.md: minimal_hook_only
  SOUL.md: no_bSmart_footprint_preferred
```
