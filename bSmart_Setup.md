# bSmart setup

```yaml
purpose: Create or update local bSmart content for one Hermes workspace.
mode: interactive
system_root: /workspace/bSmart-System
content_root: /workspace/bSmart
```

## Setup checklist

```yaml
steps:
  - verify_system_root
  - configure_optional_shared_group
  - create_content_root_if_missing
  - create_content_readme_if_missing
  - create_bSmart_Agent_from_template
  - create_bSmart_State_from_template
  - create_bSmart_TODO_from_template
  - create_bSmart_Log_from_template
  - create_content_folders
  - verify_minimal_HERMES_hook
  - offer_optional_extensions
```

## Required operator inputs

```yaml
agent:
  name: ask
  role: ask
  operator: ask
  framework: default Hermes
  platforms: ask

access_model:
  writable_paths: ask_or_detect
  readonly_paths: ask_or_detect
  unavailable: ask_or_detect

shared_group:
  purpose: keep bSmart-managed files editable by selected human and agent users
  default_group: bsmart
  group_choice:
    - create_or_use_default_bsmart_group
    - choose_existing_group
    - create_custom_named_group
  users_to_add: ask
  managed_roots: ask_with_defaults
  default_managed_roots:
    - /workspace/bSmart
    - /workspace/bSmart-System
    - /workspace/bSmart-Extensions
  optional_managed_roots:
    - /workspace
    - other operator-approved project or agent workspace paths
  inheritance:
    group_ownership: selected_shared_group
    directory_mode: setgid
    access: group_read_write
    default_acls: enabled_when_supported
  safety:
    - do not mention or hardcode site-local user names in reusable bSmart instructions
    - do not blanket-change runtime, backup, or application data folders without explicit operator scope approval
    - show planned group, users, and roots before applying host-side permission changes

operating_policy:
  default_posture: ask
  approval_thresholds: ask
  secret_handling: default avoid exposing secrets
```

## HERMES.md hook

```yaml
path: /workspace/HERMES.md
required_line: At session start, read /workspace/bSmart-System/bSmart.md and follow it.
action:
  - inspect existing HERMES.md
  - show proposed change
  - apply only with operator approval
```

## Optional extensions

```yaml
extensions:
  Fabric:
    question: Install or enable Fabric extension?
    default: yes
    target_path: /workspace/bSmart-Extensions/Fabric
```
