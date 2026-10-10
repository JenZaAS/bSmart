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

response_style:
  default: concise
  rule: Answer the requested point first and keep routine responses short; add detail only when requested, required for correctness/safety, or needed to explain a blocker.
  preferred_formats:
    - short paragraphs
    - bullets
    - compact labeled fields
  avoid:
    - repeating the request or already-known context
    - narrating routine tool output
    - long plans when one safe next step is sufficient
    - filler, hedging, or decorative prose
  preserve:
    - exact commands and paths
    - material caveats and uncertainty
    - destructive-action warnings
    - approval boundaries
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
  sensitive_action_expansion:
    trigger: Use only when an action is sensitive, user-visible, or likely to trigger a framework approval prompt.
    rule: Add a compact plain-language note before the tool call; do not expand routine status notes.
    max_length: "1-2 short sentences"
    include_when_useful:
      - high-level meaning of the action
      - main risk or why it may be flagged
      - likely approval scope suggestion, e.g. prefer Allow Once for one-off SSH/setup checks
    avoid:
      - full command-by-command breakdowns unless the operator asks
      - repeated long explanations for routine reads/checks
    example: "bSmart — Preparing GitHub SSH setup: this adds GitHub to SSH known_hosts and tests login. It may be flagged because it edits an SSH dotfile; if prompted, prefer Allow Once."

operation_tags:
  when: final replies, and progress notes where the harness shows them, only after actual work
  format: "bSmart [<scope>]: <ops> — <optional note, max 5 words>"
  startup_reminder: bStart prints this shape with an ASCII hyphen so a redirected Windows console can print the reminder
  placement: one line per scope touched, at the start of the message
  scope:
    project: the project's short index label, for example DSW
    library: the instance Library
    instance: this agent's bSmart instance content
    system: bSmart-System; this should essentially never happen and is a red flag
  ops:
    inside_a_project: read, write, delete, in the combination that happened
    outside_a_project: write and delete only; never report reads
  never_report:
    - log writes
    - history writes
    - pure chat
    - web lookups with no bSmart file change
  rule: Ops must reflect what already happened, not what was planned. This extends the bSmart action-note convention.

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
  protocol: /workspace/bSmart-System/bSmart_Protocols/secret-provider-onboarding.md
  provider_modes:
    - deployer/native secret objects mounted read-only into the container
    - service-level host secret directories mounted read-only, e.g. <host-agent-root>/secrets -> /run/secrets:ro
    - environment variables only when the operator accepts wider runtime exposure
    - external vault/provider integrations when configured locally and allowed by their terms
    - manual operator-managed credentials
  public_system_rule: bSmart-System defines provider types and safe verification only; site-local provider defaults belong in the instance content root.
  avoid:
    - /workspace/secrets
    - project folders
    - bSmart content/system repos
    - broad collaboration-group permission roots
    - bSmart logs, TODOs, workdocs, or chat transcripts
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

bprotective:
  purpose: Deterministic command guard for Hermes and for other shell-capable assistants.
  default: disabled
  core: integrations/bprotective/
  cli: scripts/bprotective
  hermes_integration: integrations/hermes/bprotective-plugin/
  commands:
    status: /bprotective status
    enable_request: /bprotective on
    disable_request: /bprotective off
    approve: /bprotective yes <ID>
    reject: /bprotective no <ID>
    cli_status: bprotective status
    cli_check: bprotective check --json -- "<command>"
  approval_rules:
    - turning bProtective on requires explicit confirmation
    - turning bProtective off requires explicit confirmation
    - risky commands escalate to the harness approval gate, or to the operator in chat when no gate exists
    - catastrophic commands are blocked deterministically
    - setup and startup must not turn the guard on
  state:
    default: off
    resolution: BPROTECTIVE_STATE_FILE, else State/bprotective.json under the per-instance content root from bsmart_instance.default_content_root, else an existing ~/.hermes/bprotective.json
    armed_record: ~/.bprotective/armed.json, or BPROTECTIVE_ARMED_FILE. This file is outside the instance State directory.
    confirmation_expiry_seconds: 300
  instance_config: State/bprotective.yaml under that same content root
  instance_config_rule: Optional protected paths and extra patterns only. The file cannot enable the guard. The directory is the per-instance content root from bsmart_instance.default_content_root.
  boundary: bProtective protects against accidental catastrophic commands. It does not protect against a deliberately adversarial agent, and it does not replace OS, container, Docker, or host-level security controls.

bprotective_preflight:
  purpose: Apply the same guard when the assistant has a shell and no pre-execution hook.
  when: Only while bProtective is on. Check once with bprotective status. While the guard is off, do not run bprotective check before commands.
  check: python3 bSmart-System/scripts/bprotective check --json -- "<exact command>"
  launcher: If python3 is missing or fails, use python, or py -3 on Windows.
  do_not_enable: Do not run bprotective on unless the operator asks. Off is the default.
  operation_tag: A pre-flight check is not tagged. Tag only work that already happened, as "bSmart [<scope>]: <ops> - <note of at most 5 words>". Inside a project report the read, write, and delete that happened. Outside a project report write and delete only. A blocked or not-run command is not a write or delete. Do not tag log or history writes, pure chat, web lookups, or the check itself.
  results:
    allow:
      exit: 0
      action: The guard is off or the command is allowed. Follow the normal bSmart approval rules.
    escalate:
      exit: 1
      action: Do not run the command. Quote the reason and ask the operator in chat. After they explicitly approve that exact command, run it. Do not treat a later check as a veto of that approval.
    block:
      exit: 2
      action: Refuse. Do not run the command and do not ask for an override.
  controls:
    status: bprotective status
    enable: The operator runs both `bprotective on` and `bprotective yes <ID>` in their own terminal. Agent hooks block those commands, so the agent cannot confirm them.
    disable: The operator runs both `bprotective off` and `bprotective yes <ID>` in their own terminal. Agent hooks block those commands.
    cancel: bprotective no <ID>, also from the operator's own terminal
    recover: When the state file is missing and the armed marker or the outside armed record is still present, the operator runs `bprotective recover` and then `bprotective yes <ID>` in their own terminal. That writes a clean off state. Agent hooks block `recover` as well.
  missing_core: A missing core blocks terminal commands. Hermes returns core-missing. Cursor, Claude, and Codex hook entries exit 2 with a deny payload, and Cursor sets failClosed. A hook launcher that cannot find Python exits 0 without a deny, so a missing interpreter does not block every command while protection is off.
  hooks: A Cursor, Claude, or Codex bProtective hook enforces the same core when it is installed and trusted. Installation still leaves the guard off. A shell command that runs bprotective on, off, yes, no, or recover, or that names the bProtective CLI, scripts path, or State directory together with a write-capable tool, is blocked. File-edit hooks deny Write, Edit, MultiEdit, Cursor Write/Delete, and Codex apply_patch when the path is the state file, the local armed marker, or the outside armed record. Codex PreToolUse denies blocks and returns no decision for escalations, so PermissionRequest can prompt. It does not return ask, and it never includes a token. PermissionRequest denies blocks and leaves escalations on the operator prompt. Codex full-auto mode, which has no approval prompt, can run ask-class commands such as git push, pip install, docker, and gh pr. The agent never receives a confirmation token from those hooks. Once the guard has been armed, a state file that reads off without a recorded operator-confirmed off fails closed, and a missing state file fails closed while the outside armed record or the local marker remains.

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
    - standard instance content via bsmart-content-upgrade (quiet; every /new)
    - Hermes /project adapter presence via bsmart-project-integration-check (quiet; every /new; skipped when Hermes is not installed)
  important_behavior:
    - missing container-storage.yaml is reported as setup_required
    - when the hermes CLI and an existing Hermes profile are both absent, the integration check reports skipped/not applicable and does not create a Hermes home
    - internal/local project storage is recorded with bsmart-project-storage-check --configure-internal; mounted storage remains --configure-mounted
    - before any startup helper call that may update or repair local state, use a plain-language action note naming the intended bSmart operation; do not rely on the framework's generic execute_code approval reason
    - on CIFS/SMB-backed workspaces executable bits may not be honored; run Python helpers with python3 <script> instead of executing the script path directly
    - the helper does not create the spec or change Compose/Dokploy unless an explicit configure subcommand is run
```

```yaml
orchestrator_compose_visibility:
  protocol: /workspace/bSmart-System/bSmart_Protocols/hermes-runtime-onboarding.md
  problem: A host blueprint is visible from the agent more often than the orchestrator's live Compose. Live Compose is authoritative.
  risk: Copying a stale blueprint over live Compose overwrites orchestrator-side changes. A hash match shows the texts match; it does not show that the container is healthy.
  inspection: Prefer a narrow read-only helper when the host provides one. That helper is an optional host pattern, not a bSmart-System command, and it must not be assumed to exist at a fixed path.
  helper_constraints:
    - read-only
    - exact service lookup or allowlist
    - no deploy, edit, or delete operations
    - avoid printing secrets
    - timeout and a clear error when the orchestrator cannot be read
  mutation: Build, sync, redeploy, and restart go through the containerized Hermes protocol and an allowlisted update harness when the host has one. Unrestricted docker is not the update path.
  reconciliation_sources:
    - /workspace/bSmart/State/container-storage.yaml
    - the host blueprint Compose
    - the orchestrator's live Compose
```

```yaml
log_target: /workspace/bSmart/bSmart_Log.md
```
