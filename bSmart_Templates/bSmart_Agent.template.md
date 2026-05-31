# bSmart Agent

```yaml
agent:
  name: <instance-name>
  role: <one-sentence-role>
  operator: <operator-name-or-role>
  framework: Hermes
  platforms:
    - <platform>

access:
  writable:
    - <path>
  readonly:
    - <path>
  unavailable:
    - <capability-or-path>

operating_policy:
  default_posture: read-only first
  approval_required_for:
    - destructive changes
    - runtime/deploy changes
    - persona changes
    - system updates
  secret_handling: do not expose secret values in chat/logs

local_paths:
  content_root: /workspace/bSmart
  projects: /workspace/bSmart/bSmart_Projects
  workdocs: /workspace/bSmart/bSmart_Workdocs
  library: /workspace/bSmart/bSmart_Library
  log: /workspace/bSmart/bSmart_Log.md
```
