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

shared_group:
  purpose: keep bSmart-managed files editable by selected human and agent users
  group: bsmart
  users: ask/update locally
  managed_roots:
    - /workspace/bSmart
    - /workspace/bSmart-System
    - /workspace/bSmart-Extensions
  inheritance:
    - group ownership on managed roots
    - group read/write access
    - setgid directories
    - default ACLs when supported
  safety:
    - show group, users, and roots before applying permission changes
    - do not blanket-change runtime, backup, or application data folders without explicit approval

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
