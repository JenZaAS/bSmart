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
  - bStart.py
  - /workspace/bSmart-System/bSmart.md
  - /workspace/bSmart-System/bSmart_Invariants.md
  - /workspace/bSmart/bSmart_Agent.md
  - /workspace/bSmart/bGuardrails.md when present
  - /workspace/bSmart/Roles/current_role.md
  - selected /workspace/bSmart/Roles/<role-id>_role.md
  - selected project.md and workstream context when active
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
    HERMES_WRITE_SAFE_ROOT: /opt/data:/workspace:/projects:/sandboxes
  first_run_helper: /workspace/bSmart-System/scripts/bsmart-bootstrap-workspace
  existing_instance_upgrade: /workspace/bSmart-System/scripts/bsmart-instance-upgrade
  existing_instance_update: /workspace/bSmart-System/scripts/bsmart-update
  existing_instance_repair: /workspace/bSmart-System/scripts/bsmart-content-upgrade --create-missing
  upgrade_rule: back up differing startup hooks, install bStart.py, and synchronize canonical hooks; do not alter instance content/state
  command_rule: "pull" changes only the system checkout; "update" runs bsmart-update without pulling; setup uses the same finalization for existing instances
  profile_migration: apply known exact bSmart_Agent.md compatibility migrations automatically with a backup and clear report; ask only for ambiguous or broader changes
  repair_rule: create missing standard content files only; never overwrite existing instance content
  startup_behavior: run the quiet content-upgrade check on every /new; keep heavier Git and storage checks once-per-UTC-day throttled
  integration_behavior: run the quiet /project adapter check on every /new; install/enable the managed adapter when missing and report only changes or setup problems
  action_note_behavior: explain the purpose before startup maintenance; name the concrete operation (update, create missing bHistory, or install/enable /project) rather than exposing only a generic tool-execution description
  verification:
    - restart_or_redeploy_after workspace/bootstrap/compose changes
    - run bsmart-instance-upgrade after a system checkout update on an existing instance
    - send /new to the target bot
    - send Hi as the first agent-authored verification turn
    - confirm bSmart startup summary and no GitHub SSH-key warning
```

```yaml
governance:
  system_changes: treat_as_versioned_changes
  content_changes: local_instance_state
  HERMES.md: shared_startup_hook
  AGENTS.md: same_shared_startup_hook
  SOUL.md: no_bSmart_footprint_preferred
```

## Progressive help and `/new` greeting

After `/new`, the gateway reset itself may not be an agent-authored turn, but the first real reply after reset should be concise and discoverable:

```text
Hi, <operator-name>!
bSmart — Startup
<compact startup summary from bStart.py>
Info keywords: help, features, setup, projects, tasks, safety.
<short question about continuing the current TODO item>
```

Help should be progressive:
- `help`/`info` gives only the keyword line plus a short orientation.
- `features` gives a brief numbered feature list from `bSmart_Features.md`.
- A later numeric reference such as `2` or `tell me more about 2` expands only that item.
- Keep responses short unless the operator asks for more detail.
