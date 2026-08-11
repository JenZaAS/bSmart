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
  tool_approval_model:
    framework_mode: ask/update locally
    recommended_for_Hermes: approvals.mode smart
    bsmart_guardrails: mandatory
    low_risk_without_extra_prompt:
      - read-only inspection
      - local calculations and Python analysis without side effects
      - bounded creation of a small number of harmless new output files in approved work folders
      - syntax checks and metadata checks
    explicit_approval_required_for:
      - overwriting, deleting, moving, or permission-changing files; chmod, chown, chgrp, setfacl
      - creating many files, creating files outside approved work folders, or writing sensitive/executable/deploy-affecting content
      - host/runtime/deploy changes
      - package installs, credential changes, external publication, sensitive-data access, and destructive actions
  approval_required_for:
    - destructive changes
    - runtime/deploy changes
    - persona changes
    - system updates
  secret_handling: do not expose secret values in chat/logs

local_paths:
  content_root: /workspace/bSmart
  project_root_selection:
    - BSMART_PROJECT_ROOT
    - /projects
    - ./projects
    - /workspace/bSmart/Projects
  sandbox_root_selection:
    - BSMART_SANDBOX_ROOT
    - /sandboxes
    - ./sandboxes
    - ./bSmart/Sandboxes
  mail_root_selection:
    - BSMART_MAIL_ROOT
    - /mail
    - ./mail
    - /workspace/bSmart/Mail
  workdocs: /workspace/bSmart/Workdocs
  library: /workspace/bSmart/Library
  log: /workspace/bSmart/bSmart_Log.md

mail_handling:
  natural_language_trigger: when the user says "check your mail" or similar, check bSmart bMail first, not internet email/Himalaya, unless the user explicitly says email/Gmail/IMAP.
  quick_check_command: python3 /workspace/bSmart-System/scripts/bMail check --mailbox /mail
  read_command_template: python3 /workspace/bSmart-System/scripts/bMail read --mailbox /mail --id <message-id>
  fallback_mailbox_paths:
    - /mail
    - ./mail
    - /workspace/bSmart/Mail
```
