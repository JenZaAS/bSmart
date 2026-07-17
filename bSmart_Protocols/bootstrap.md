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
new_agent_bootstrap_standard:
  assumption: all newly initialized AI agents should run bSmart
  stale_image_rule: do not bake bSmart-System into the Docker image
  image_allowed_hook:
    - a tiny generic first-run startup hook is allowed
    - hook may fetch/run scripts/bsmart-bootstrap-workspace against the mounted /workspace
    - hook should clone/update bSmart-System from the public HTTPS Git repo into /workspace/bSmart-System
    - hook should create only missing local content files and never overwrite an existing instance identity/state without approval
  compose_defaults:
    working_dir: /workspace
    TERMINAL_CWD: /workspace
    HERMES_WRITE_SAFE_ROOT: /workspace
  first_run_helper: /workspace/bSmart-System/scripts/bsmart-bootstrap-workspace
  verification:
    - restart_or_redeploy_after workspace/bootstrap/compose changes
    - send /new to the target bot
    - send Hi as the first agent-authored verification turn
    - confirm bSmart startup summary and no GitHub SSH-key warning
```

```yaml
governance:
  system_changes: treat_as_versioned_changes
  content_changes: local_instance_state
  HERMES.md: minimal_hook_only
  SOUL.md: no_bSmart_footprint_preferred
```
