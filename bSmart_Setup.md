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
