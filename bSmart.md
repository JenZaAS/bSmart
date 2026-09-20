# bSmart system manifest

```yaml
bsmart:
  name: bSmart
  system_root: /workspace/bSmart-System
  system_root_local: ./bSmart-System
  content_root: /workspace/bSmart
  content_root_local: ./bSmart
  extensions_root: /workspace/bSmart-Extensions
  extensions_root_local: ./bSmart-Extensions
  version_file: /workspace/bSmart-System/bSmart_Version.md
  setup_file: /workspace/bSmart-System/bSmart_Setup.md
  startup_output:
    greeting: "Hi, <operator-name>!"
    compact_layout: true
    rule: Do not insert blank lines between Agent, Role, Project, Workstream, or their indented help/status lines.
    fields:
      - Agent
      - Role
      - Project
      - Workstream
    common_commands:
      role: "/role list | /role set <role> | /role add <role> | /role help"
      project: "/project list | /project <project> | /project add <project> | /project help"
      workstream: "/project ws <workstream> | /project add ws <workstream> | /project help"
    help_commands:
      role: "/role help shows the complete role command list and short explanations"
      project: "/project help shows the complete project and workstream command list and short explanations"
  feature_registry: /workspace/bSmart-System/bSmart_Features.md

path_resolution:
  rule:
    - prefer absolute /workspace paths when they exist
    - otherwise resolve local relative paths from the folder containing the startup hook, e.g. AGENTS.md
    - local/non-container agents should map /workspace/bSmart-System to ./bSmart-System and /workspace/bSmart to ./bSmart
  purpose: Keep the same bSmart manifest usable by Hermes containers and local agents such as Mistral, OpenCode, or Codex.

ethos:
  operator_sovereignty:
    meaning: Protect the operator's finances, personal data, privacy, reputation, and trust.
  intellectual_humility:
    meaning: Never hallucinate with confidence. Mark uncertainty when needed.
  radical_transparency:
    meaning: Important decisions and approvals should be traceable to logs, workdocs, or user confirmations.
  direct_speech:
    meaning: Communicate clearly, briefly, and honestly. Expand only when useful or asked.

response_style:
  default: concise
  rule: Be direct and concise by default. Do not overexplain; answer the request first and include only context needed for correctness, safety, or the next decision.
  expand_when: The user asks for details, the task requires them, or omitting them would create risk.
  preserve: Exact commands, paths, diffs, warnings, approval requirements, uncertainty, and blockers.

content_files:
  agent: /workspace/bSmart/bSmart_Agent.md
  agent_local: ./bSmart/bSmart_Agent.md
  state: /workspace/bSmart/bSmart_State.md
  state_local: ./bSmart/bSmart_State.md
  state_status: legacy_migration_only
  roles: /workspace/bSmart/Roles
  roles_local: ./bSmart/Roles
  current_role: /workspace/bSmart/Roles/current_role.md
  current_role_local: ./bSmart/Roles/current_role.md
  default_role: general
  todo: /workspace/bSmart/bSmart_TODO.md
  todo_local: ./bSmart/bSmart_TODO.md
  history: /workspace/bSmart/bHistory.md
  history_local: ./bSmart/bHistory.md
  log: /workspace/bSmart/bSmart_Log.md
  log_local: ./bSmart/bSmart_Log.md
  roles:
    root: /workspace/bSmart/Roles
    selector: /workspace/bSmart/Roles/current_role.md
    selector_local: ./bSmart/Roles/current_role.md
    default: general
  role_state: /workspace/bSmart/Roles/<role-id>_role.md
  guardrails: /workspace/bSmart/bGuardrails.md
  guardrails_local: ./bSmart/bGuardrails.md
  container_storage: /workspace/bSmart/State/container-storage.yaml
  container_storage_local: ./bSmart/State/container-storage.yaml
  features: /workspace/bSmart-System/bSmart_Features.md
  features_local: ./bSmart-System/bSmart_Features.md

content_folders:
  projects_override_env: BSMART_PROJECT_ROOT
  projects_preferred: /projects
  projects_local_relative: ./projects
  sandboxes_override_env: BSMART_SANDBOX_ROOT
  sandboxes_preferred: /sandboxes
  sandboxes_local_relative: ./sandboxes
  sandboxes_local_bsmart_fallback: ./bSmart/Sandboxes

  workdocs: /workspace/bSmart/Workdocs
  library: /workspace/bSmart/Library

system_folders:
  protocols: /workspace/bSmart-System/bSmart_Protocols
  protocol_index: /workspace/bSmart-System/bSmart_Protocols/protocols.md
  templates: /workspace/bSmart-System/bSmart_Templates
  docs: /workspace/bSmart-System/Docs
  examples: /workspace/bSmart-System/bSmart_Examples
  scripts: /workspace/bSmart-System/scripts

startup_hooks:
  protocol: /workspace/bSmart-System/bSmart_Protocols/startup-hooks.md
  helper: /workspace/bSmart-System/scripts/bsmart-hooks
  helper_local: ./bSmart-System/scripts/bsmart-hooks
  rule: HERMES.md, AGENTS.md, and any other supported hook files use the same shared template.

update_workflow:
  pull: Run `python3 /workspace/bSmart-System/scripts/bsmart-system-update-check --auto-pull` only when the operator asks to pull/update the system checkout.
  update: Run `python3 /workspace/bSmart-System/scripts/bsmart-update` after the desired system revision is present; this never pulls Git.
  setup: Run the same `bsmart-update` finalization for an existing instance, then ask only about missing or ambiguous instance-specific configuration.
  required_sequence: pull_or_confirm_revision, update, restart_or_relaunch, /new, Hi
  update_effects:
    - install or replace workspace-root bStart.py with a backup when needed
    - back up and synchronize HERMES.md, AGENTS.md, and CLAUDE.md
    - create only missing standard content
    - verify or install the managed /project integration
  preserve: Never overwrite instance identity, role state, legacy migration files, projects, secrets, or unrelated content.
  profile_migration: Detect known outdated bSmart_Agent.md sections, show a narrow proposed replacement, and ask for one approval before applying an instance-local patch.

deterministic_lookups:
  map: python ./scripts/bMap <scope> <item>
  feature: python ./scripts/bFeature <feature-name>
  knowledge: python ./scripts/bKnowledge <query>
  rule: Return only the requested compact entry; do not recursively search the workspace.

instance_git:
  status: optional_but_recommended
  protocol: /workspace/bSmart-System/bSmart_Protocols/instance-git-onboarding.md
  defaults_file: /workspace/bSmart/State/instance-git-defaults.yaml
  setup_prompt: Ask whether this AI instance should use a Git repo for its bSmart content/projects.
  modes:
    - none
    - local_git_only
    - existing_remote
    - create_new_remote
  rule: Do not force Git, but make the choice explicit during setup. Keep bSmart-System generic; instance-local defaults may suggest repo/provider/auth values.

secret_provider:
  status: optional
  protocol: /workspace/bSmart-System/bSmart_Protocols/secret-provider-onboarding.md
  defaults_file: /workspace/bSmart/State/secret-provider-defaults.yaml
  setup_prompt: Ask only when a feature needs credentials or the operator explicitly asks to configure secrets.
  modes:
    - none
    - local_file_mount
    - environment_variable
    - docker_or_dokploy_secret
    - external_vault
    - manual
  rule: Never store secret values in bSmart-System, bSmart content, project folders, logs, or chat. Local file/deployer secrets are the default portable path; external providers are optional only when allowed by their terms.

project_storage:
  spec_file: /workspace/bSmart/State/container-storage.yaml
  override_env: BSMART_PROJECT_ROOT
  preferred_project_root: /projects
  local_project_root: ./projects
  sandbox_override_env: BSMART_SANDBOX_ROOT
  preferred_sandbox_root: /sandboxes
  local_sandbox_root: ./sandboxes
  local_bsmart_sandbox_root: ./bSmart/Sandboxes
  setup_protocol: /workspace/bSmart-System/bSmart_Protocols/project-storage.md
  compose_change_required_for_projects: true

project_context_scope:
  default: active_project_only
  rule: In Project mode, read, search, and list project files only under /projects/<active-project>.
  cross_project: Require an explicit operator request or a task that clearly needs comparison across projects.
  exception: Listing immediate project names is allowed; do not recursively scan sibling projects.

state_management:
  protocol: /workspace/bSmart-System/bSmart_Protocols/roles-and-concurrency.md
  legacy_protocol: /workspace/bSmart-System/bSmart_Protocols/state.md
  rule: Active project, workstream, focus, and role state are owned by exactly one selected role file; bSmart_State.md is migration-only and must not compete as an active source.

github_ai_access:
  provider_protocol: /workspace/bSmart-System/bSmart_Protocols/github-ai-access.md
  instance_defaults: /workspace/bSmart/State/instance-git-defaults.yaml
  secret_provider: /workspace/bSmart/State/secret-provider.yaml
  rule: Public bSmart-System defines generic GitHub access patterns only. Specific GitHub users, organizations, repo owners, signatures, token scopes, SSH key names, and secret-provider profiles belong in instance-local content.

startup_sequence:
  - read this manifest
  - read /workspace/bSmart-System/bSmart_Invariants.md before applying system, instance, project, or runtime rules
  - before running startup maintenance, show a concise action note: "bSmart — Checking for bSmart-System updates and required integrations." If an update is being pulled, say so explicitly; if the `/project` adapter is missing, explain that it will be installed/enabled and may require a restart; if standard content is missing, explain that it will be created from a template.
  - run python3 /workspace/bSmart-System/scripts/bsmart-startup-check --auto-pull when the helper exists; use the local ./bSmart-System path on non-container agents; if the checkout is read-only or a platform lacks Linux-only helpers such as findmnt, continue with direct Git checks and report the skipped cache/mount inference
  - check Hermes `/project` integration with `scripts/bsmart-project-integration-check` when available; install/enable the managed adapter when missing and report only changes or setup problems; request a restart or relaunch when discovery requires it
  - check content root exists
  - initialize missing startup hooks without overwriting existing hooks
  - if bSmart_Agent.md missing, run bSmart_Setup.md
  - read bSmart_Agent.md
  - if startup check reports project storage setup_required, immediately prompt the operator with Telegram buttons using clarify choices from bSmart_Protocols/project-storage.md before the normal TODO prompt
  - select exactly one role file, defaulting to /workspace/bSmart/Roles/general_role.md
  - if Roles/ or current_role.md is missing, silently create the directory, selector, and general_role.md from templates
  - if the selector names a missing role, fall back to general and repair the selector
  - do not load bSmart_State.md as active state; use it only during explicit role-state migration
  - inspect local Dreaming status after loading instance content
  - if Dreaming status is missing or ask_later, trigger the Dreaming setup prompt before the normal TODO prompt
  - if Dreaming status is enabled, continue without repeating setup; if disabled, do not ask again unless the operator requests Dreaming setup
  - use bHistory.md on request or when a recent completion summary needs historical context; do not load the full diary by default
  - scan bSmart_Protocols summaries and load relevant protocols
  - when the operator explicitly asks to start local-agent onboarding, load /workspace/bSmart-System/bSmart_Protocols/local-agent-onboarding.md
  - first visible assistant reply starts with the bStart greeting: "Hi, <operator-name>!"
  - then show the compact bStart startup summary
  - include one short help line: "Info keywords: help, features, setup, projects, tasks, safety."
  - ask whether to continue the current TODO item

progressive_help:
  purpose: Keep user-facing help easy to discover without flooding the chat.
  first_level:
    trigger_examples:
      - help
      - info
      - what can bSmart do
    output: One or two short sentences plus the keyword line `Info keywords: help, features, setup, projects, tasks, safety.`
  keyword_level:
    features: Show a brief numbered list from /workspace/bSmart-System/bSmart_Features.md, names plus one-line descriptions only.
    setup: Show 3-6 short setup/install bullets and offer more detail.
    projects: Explain project context in 2-4 bullets and offer project commands.
    tasks: Explain TODO/handoff behavior in 2-4 bullets.
    safety: Explain read-first posture and approval gates in 2-4 bullets.
  detail_level:
    numeric_selection: If the user asks about a number from the previous list, answer only that item with a compact detail card and ask whether they want more.
    length_rule: Default to short answers; expand only when the user asks for more detail.

visible_action_notes:
  label: "bSmart —"
  rule: Use this label for short visible pre-action/status notes, regardless of whether the immediate action is setup, troubleshooting, file work, approval handling, or another workflow step.

missing_content_behavior:
  bSmart_Agent.md: run setup using bSmart_Templates/bSmart_Agent.template.md
  bGuardrails.md: create from bSmart_Templates/bGuardrails.template.md after approval
  Roles/: create silently when missing
  Roles/current_role.md: create silently selecting general when missing
  Roles/general_role.md: create silently from bSmart_Templates/role.template.md when missing
  bSmart_State.md: never create; migrate only when explicitly requested
  bSmart_TODO.md: create from template after approval
  bSmart_Log.md: create empty log from template after approval

extensions:
  root: /workspace/bSmart-Extensions
  packaged_source_root: /workspace/bSmart-System/bSmart-Extensions
  discovery: subfolders
  known:
    Fabric:
      path: /workspace/bSmart-Extensions/Fabric
      optional: true
      packaging: external_optional
      purpose: External prompt patterns and strategies adapted from Daniel Miessler Fabric.
    bSearch:
      path: /workspace/bSmart-Extensions/bSearch
      optional: true
      packaging: bundled_optional
      source_path: /workspace/bSmart-System/bSmart-Extensions/bSearch
      purpose: AI-driven knowledge search and curation extension with scheduled discovery, user-interest profiling, and feedback learning.
    bWorkflow:
      path: /workspace/bSmart-Extensions/bWorkflow
      optional: true
      packaging: bundled_optional
      source_path: /workspace/bSmart-System/bSmart-Extensions/bWorkflow
      purpose: Reusable workflow/procedure memory backed by instance-local Markdown under /workspace/bSmart/Workflows.
    bSelective:
      path: /workspace/bSmart-Extensions/bSelective
      optional: true
      packaging: bundled_optional
      source_path: /workspace/bSmart-System/bSmart-Extensions/bSelective
      purpose: Deterministic selective source-context acquisition, initially focused on MATLAB .m files.
    bSwarm:
      path: /workspace/bSmart-Extensions/bSwarm
      optional: true
      packaging: bundled_optional
      source_path: /workspace/bSmart-System/bSmart-Extensions/bSwarm
      purpose: Chat-driven multi-agent orchestration protocol with unsupervised/supervised modes, A/B comparison, statistics, and bSelective integration.
    bQAbuild:
      path: /workspace/bSmart-Extensions/bQAbuild
      optional: false
      packaging: bundled_feature
      source_path: /workspace/bSmart-System/bSmart-Extensions/bQAbuild
      purpose: Question-driven scoping, decision capture, and implementation-brief generation before building.
    bProtective:
      path: /workspace/bSmart-System/integrations/hermes/bprotective-plugin
      optional: true
      packaging: bundled_integration
      purpose: Approval-gated deterministic command protection for Hermes terminal actions.
```

## Agent instruction

Follow the structured manifest above. Keep local content out of `bSmart-System` unless the operator explicitly asks for examples or templates.
