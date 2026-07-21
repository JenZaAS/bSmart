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
  - run_or_offer_streamlined_workspace_bootstrap_helper
  - verify_system_root_public_https_git
  - verify_compose_defaults_working_dir_terminal_cwd_and_safe_root
  - configure_instance_git_only_if_operator_wants_content_git
  - configure_optional_shared_group
  - configure_approval_mode_and_guardrails
  - configure_project_storage
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

workspace_bootstrap:
  streamlined_helper: /workspace/bSmart-System/scripts/bsmart-bootstrap-workspace
  public_fetch_command: curl -fsSL https://raw.githubusercontent.com/JenZaAS/bSmart/main/scripts/bsmart-bootstrap-workspace -o /tmp/bsmart-bootstrap-workspace
  purpose: initialize the mounted workspace quickly without baking bSmart-System into the image
  defaults:
    bsmart_system_remote: https://github.com/JenZaAS/bSmart.git
    bsmart_system_updates: safe HTTPS fast-forward auto-pull
    HERMES.md: minimal hook only
    HERMES_WRITE_SAFE_ROOT: /workspace
    TERMINAL_CWD: /workspace
  rule: all new AI agents should be bSmart-enabled unless the operator explicitly says otherwise

instance_git:
  purpose: make the AI instance content/projects durable and syncable without mixing them into the bSmart system repo
  default: ask only for /workspace/bSmart content; do not confuse this with bSmart-System Git, which is required system infrastructure
  choices:
    - none
    - local_git_only
    - existing_remote
    - create_new_remote
  guidance:
    - recommend a private instance repo for persistent AI instances
    - allow no Git when the operator wants a temporary/local-only instance
    - do not store secrets in the instance repo
    - if Git is enabled, keep nested external code repos ignored unless the operator explicitly wants submodules
  nested_git_helper: /workspace/bSmart-System/scripts/bsmart-ignore-nested-git

project_storage:
  purpose: choose the canonical project folder location for this AI instance
  spec_file: /workspace/bSmart/State/container-storage.yaml
  trigger: ask when spec_file is missing
  daily_startup_helper: /workspace/bSmart-System/scripts/bsmart-startup-check
  daily_startup_invocation: python3 /workspace/bSmart-System/scripts/bsmart-startup-check --auto-pull
  daily_startup_local_invocation: python3 ./bSmart-System/scripts/bsmart-startup-check --auto-pull
  storage_helper: /workspace/bSmart-System/scripts/bsmart-project-storage-check
  storage_helper_invocation: python3 /workspace/bSmart-System/scripts/bsmart-project-storage-check
  storage_helper_local_invocation: python3 ./bSmart-System/scripts/bsmart-project-storage-check
  prompt_style: Telegram buttons when supported
  prompt_text: |
    bSmart - Project configuration

    Choose location for project folders:

    1) Mounted volume (e.g. external to Docker image and possibly a mounted SMB drive)

    2) Internal bSmart (standard bSmart project folder inside the container workspace)

    Some things will be stored in an internal project sandbox.
  choices:
    - Mounted volume
    - Internal bSmart
  mounted_volume:
    followup_prompt: |
      bSmart - Mounted project volume selected.

      Enter host-project-folder, e.g.

      /mnt/share/MyAI
    compose_line_template: "- <host-project-folder>:/projects:rw"
    helper_command: "python3 /workspace/bSmart-System/scripts/bsmart-project-storage-check --configure-mounted --host-project-folder <host-project-folder>"
    helper_command_local: "python3 ./bSmart-System/scripts/bsmart-project-storage-check --configure-mounted --host-project-folder <host-project-folder>"
  internal_bsmart:
    infer_workspace_host_path: findmnt -T /workspace -n -o SOURCE
    compose_line_template: "- <host-workspace>/bSmart/Projects:/projects:rw"
    helper_command: "python3 /workspace/bSmart-System/scripts/bsmart-project-storage-check --configure-internal"
    helper_command_local: "python3 ./bSmart-System/scripts/bsmart-project-storage-check --configure-internal"
    fallback_if_inference_fails: ask operator for the host path backing /workspace
  sandbox:
    canonical_root: /sandboxes
    per_project_template: /sandboxes/<project-slug>
    user_prompt: do not mention during initial project-storage setup unless operator asks
    host_prep_required_before_compose: true
    host_prep_command_template: "sudo install -d -o 10000 -g 10000 -m 0775 <host-sandbox-folder>"
    safety_note: "Create and permission the host sandbox folder before adding the /sandboxes bind mount; otherwise Docker/Dokploy may auto-create the missing source as root:root and the container will see /sandboxes mounted but unwritable."

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
  bSearch:
    question: Install or enable bSearch extension?
    default: yes
    target_path: /workspace/bSmart-Extensions/bSearch
    source_path: /workspace/bSmart-System/bSmart-Extensions/bSearch
    packaging: bundled_with_bsmart
    short_explanation: AI-driven knowledge search add-on that can run on a schedule, curate interesting items, maintain a short editable user-interest profile, and learn from feedback.
  Fabric:
    question: Install or enable Fabric extension?
    default: yes
    target_path: /workspace/bSmart-Extensions/Fabric
    packaging: external_optional
    short_explanation: Optional prompt-pattern and reasoning-strategy library adapted from Daniel Miessler Fabric.
```

## Available features prompt

```yaml
feature_registry:
  path: /workspace/bSmart-System/bSmart_Features.md
  setup_prompt: Would you like to see available bSmart features now?
  if_yes: show bSmart features
  list_mode: name + short_description
```
