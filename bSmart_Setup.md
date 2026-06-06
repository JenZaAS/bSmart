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
  - configure_approval_mode_and_guardrails
  - create_content_root_if_missing
  - create_content_readme_if_missing
  - create_bSmart_Agent_from_template
  - create_bSmart_State_from_template
  - create_bSmart_TODO_from_template
  - create_bSmart_Log_from_template
  - create_content_folders
  - verify_minimal_HERMES_hook
  - offer_optional_extensions
  - offer_show_available_features
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
  secret_storage:
    preferred:
      - native deployer secrets mounted read-only
      - /opt/docker-workspace/<service>/secrets mounted as /run/secrets:ro
    avoid:
      - /workspace/secrets
      - bSmart repos/content folders
      - project folders
    permission_baseline:
      directories: "0700"
      private_keys: "0600"
      public_keys_and_known_hosts: "0644 or stricter"

tool_approval_model:
  purpose: reduce repetitive framework permission prompts while preserving operator control through bSmart guardrails
  framework_support:
    Hermes:
      recommended_config:
        approvals.mode: smart
      command_hint: hermes config set approvals.mode smart
      restart_required: true
  setup_questions:
    - keep framework approval mode manual
    - use smart/low-friction framework approvals plus bSmart guardrails
    - turn framework approvals off only for explicitly trusted local/sandboxed environments
  default_choice: use smart/low-friction framework approvals plus bSmart guardrails
  bsmart_guardrails:
    low_risk_without_extra_prompt:
      - read-only inspection
      - calculations and local Python analysis that do not modify files or call external services
      - bounded creation of a small number of harmless new output files in approved work folders
      - syntax checks and harmless metadata checks
    explicit_operator_approval_required:
      - host/runtime/deploy changes
      - overwriting, deleting, moving, or permission-changing files; chmod, chown, chgrp, setfacl
      - creating many files, creating files outside approved work folders, or writing sensitive/executable/deploy-affecting content
      - commands that install packages, expose services, change credentials, publish externally, or access sensitive data
      - destructive or hard-to-reverse actions
    rule: framework approval mode is not the safety boundary; bSmart guardrails remain mandatory
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

## Available features prompt

```yaml
feature_registry:
  path: /workspace/bSmart-System/bSmart_Features.md
  setup_prompt: Would you like to see available bSmart features now?
  if_yes: show bSmart features
  list_mode: name + short_description
```
