# bSmart Protocol: operations

```yaml
protocol:
  id: operations
  title: Operations
  purpose: Safe action cadence, approvals, direct speech, and traceability.
```

```yaml
principles:
  read_first: true
  reversible_changes_preferred: true
  direct_speech: true
  no_confident_hallucination: true
  trace_key_decisions: true
```

```yaml
visible_action_notes:
  label: "bSmart —"
  meaning: Short pre-action/status notes for visible agent actions.
  applies_to:
    - tool/status checks
    - file reads or edits
    - approvals
    - troubleshooting
    - workflow steps
  rule: Use the bSmart label consistently regardless of the immediate action source or reason.
  style: Gerund phrase, concise, only when useful for traceability or operator awareness.

approval_events_to_log:
  - destructive_change
  - host_or_runtime_change
  - persona_change
  - system_update
  - content_migration
```

```yaml
secret_storage:
  principle: Keep credentials outside collaborative workspaces and outside Git repos.
  preferred:
    - deployer/native secret objects mounted read-only into the container
    - service-level host secret directories mounted read-only, e.g. /opt/docker-workspace/<service>/secrets -> /run/secrets:ro
  avoid:
    - /workspace/secrets
    - project folders
    - bSmart content/system repos
    - broad collaboration-group permission roots
  permissions:
    directories: "0700 by the service runtime user where possible"
    private_keys: "0600"
    public_keys_and_known_hosts: "0644 or stricter"
  note: If a legacy /workspace/secrets directory exists, migrate it to the service-level secret path, then leave only a temporary compatibility path or remove it after verification.
```

```yaml
tool_approval_model:
  purpose: Avoid repeated low-value permission prompts from the host framework while keeping meaningful operator approval inside bSmart.
  recommended_default:
    Hermes:
      approvals.mode: smart
      reason: Let Hermes auto-approve low-risk tool calls and reserve prompts for higher-risk actions.
  bsmart_guardrails:
    low_risk_actions_may_proceed:
      - read-only inspection
      - arithmetic/calculations
      - local Python analysis that does not modify files, change runtime state, install packages, call external services, or expose secrets
      - bounded creation of a small number of harmless new output files in approved work folders
      - syntax checks and metadata checks
    explicit_operator_approval_required:
      - overwriting, deleting, moving, or permission-changing files; chmod, chown, chgrp, setfacl
      - creating many files, creating files outside approved work folders, or writing sensitive/executable/deploy-affecting content
      - host/runtime/deploy changes
      - package installs, service exposure, credential changes, external publication, or sensitive-data access
      - destructive or hard-to-reverse actions
  invariant: Framework approval mode is not the safety boundary; bSmart guardrails are.
  setup_note: During init, ask the operator whether to keep manual framework approvals, use smart/low-friction approvals, or disable framework approvals only in explicitly trusted environments.
```

```yaml
git_handoff:
  purpose: Keep bSmart handoff/content repos current when tasks or projects close.
  rule: If the local bSmart content root is a Git repo, commit relevant task/project closure changes when finishing tasks, archiving projects, updating handoff TODOs, or recording decision-log entries.
  applies_to:
    - /workspace/bSmart
    - any bSmart content root with its own Git repo
  commit_scope: Stage only relevant bSmart content/handoff files for the completed task or project; do not mix unrelated local changes.
  commit_style: concise conventional message, e.g. "chore: close <task>" or "chore: archive <project> project".
  exception: If changes are sensitive, ambiguous, unrelated, or operator says not to commit, leave them uncommitted and explain why.
  nested_git_policy:
    rule: Nested Git repos inside projects are independent source repos by default, not submodules.
    if_agent_clones_repo: Add the cloned path to the AI instance repo .gitignore unless the operator explicitly requests a submodule.
    before_instance_commit: Run /workspace/bSmart-System/scripts/bsmart-ignore-nested-git --check when available.
    fix_command: /workspace/bSmart-System/scripts/bsmart-ignore-nested-git --fix
    submodules: opt_in_only
```

```yaml
bsmart_system_update_check:
  purpose: Keep each AI instance's bSmart-System repo fresh without requiring routine user prompting.
  trigger: first /new startup per UTC day when helper/support exists
  target: /workspace/bSmart-System only
  helper: /workspace/bSmart-System/scripts/bsmart-system-update-check
  startup_wrapper: /workspace/bSmart-System/scripts/bsmart-startup-check
  default_remote: https://github.com/JenZaAS/bSmart.git
  reason: public bSmart-System updates should work in sibling AI containers without per-container GitHub SSH secrets
  safe_actions:
    - fetch/check remote status over HTTPS by default
    - auto-pull only when repo is clean, on expected branch, and fast-forward only
  never_auto_update:
    - /workspace/bSmart instance/content repo
    - dirty, diverged, or unexpected-remote system repo
  state_file: /workspace/bSmart/State/bsmart-system-update.yaml
  report_style: compact; report only updated, up-to-date, skipped, or blocked state
```

```yaml
bsmart_startup_checks:
  purpose: Run the concrete /new checks that are safe for an AI instance to execute locally.
  helper: /workspace/bSmart-System/scripts/bsmart-startup-check
  invocation: python3 /workspace/bSmart-System/scripts/bsmart-startup-check --auto-pull
  local_invocation: python3 ./bSmart-System/scripts/bsmart-startup-check --auto-pull
  cadence: once per UTC day
  state_file: /workspace/bSmart/State/bsmart-startup-check.yaml
  checks:
    - bSmart-System Git freshness via bsmart-system-update-check
    - project/sandbox storage spec via bsmart-project-storage-check
  important_behavior:
    - missing container-storage.yaml is reported as setup_required
    - on CIFS/SMB-backed workspaces executable bits may not be honored; run Python helpers with python3 <script> instead of executing the script path directly
    - the helper does not create the spec or change Compose/Dokploy unless an explicit configure subcommand is run
```

```yaml
dokploy_compose_visibility:
  problem: SschwAdmin can see image-source blueprint compose but not necessarily live Dokploy compose stored in Dokploy UI/database.
  risk: Copying stale blueprint compose into Dokploy can overwrite operator-made Dokploy changes.
  preferred_solution: narrow read-only helper exposed to SschwAdmin, e.g. /usr/local/ai-bin/dokploy-compose-read <service>
  helper_constraints:
    - read-only
    - exact service lookup or allowlist
    - no deploy/edit/delete operations
    - avoid printing secrets where possible
    - timeout and clear errors if API/token unavailable
  reconciliation_sources:
    - /workspace/bSmart/State/container-storage.yaml
    - /opt/image-sources/<instance>/docker-compose.yml blueprint
    - live Dokploy compose via read-only helper when available
```

```yaml
log_target: /workspace/bSmart/bSmart_Log.md
```
