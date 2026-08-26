# bSmart features

```yaml
feature_registry:
  path: /workspace/bSmart-System/bSmart_Features.md
  purpose: Canonical user-facing registry of bSmart features and where they live.
  sort_default: user_workflow_order
  update_rule: Update this file whenever bSmart features are added, removed, renamed, merged, or materially changed.
  design_rule: Keep the top-level list simple, user-facing, and non-technical. Put subfeatures and internal mechanisms inside detail cards, not in the main list.
  list_modes:
    full: name + short_description
    index: name_only
    grouped: group + name + short_description
  display_commands:
    - help
    - info
    - features
    - show features
    - show bSmart features
    - show feature index
    - show features by group
    - show feature <name>
  progressive_help_rule: First answer briefly; if a numbered list was shown, a later number expands only that item.
```

## Display rules

```yaml
commands:
  show_features:
    aliases:
      - show features
      - show bSmart features
    output: User-facing list of feature names with short descriptions.
  show_feature_index:
    aliases:
      - show feature index
      - show bSmart feature index
    output: Name-only user-facing list.
  show_features_by_group:
    aliases:
      - show features by group
      - show bSmart features by group
    output: Grouped user-facing list with names and short descriptions.
  show_feature_detail:
    aliases:
      - show feature <name>
      - show bSmart feature <name>
      - tell me more about <number>
      - <number>
    output: Compact feature card for the requested item; expand only if the user asks for more.
  progressive_help:
    aliases:
      - help
      - info
    output: One or two short orientation sentences plus `Info keywords: help, features, setup, projects, tasks, safety.`
```

## Feature list

1. Projects — Manage project context and project folders.
2. Tasks — Track next actions and handoffs.
3. Workdocs — Keep detailed notes for larger work.
4. Library — Store and reuse durable knowledge.
5. Decision Log — Record important decisions and approvals.
6. History — Keep a concise diary of completed work.
7. Dreaming — Improve local bSmart content while you sleep.
8. Improvement Scout — Find external ideas to improve bSmart itself.
9. Safety — Keep actions transparent and low-risk.
10. Security Watch — Check visible VPS/container security drift.
11. Setup — Initialize and maintain bSmart structure.
12. Extensions — Enable optional add-on packs.
13. Features — Show available bSmart capabilities.

## Feature index

1. Projects
2. Tasks
3. Workdocs
4. Library
5. Decision Log
6. History
7. Dreaming
8. Improvement Scout
9. Safety
10. Security Watch
11. Setup
12. Extensions
13. Features

## Features by group

### Work
- Projects — Manage project context and project folders.
- Tasks — Track next actions and handoffs.
- Workdocs — Keep detailed notes for larger work.

### Knowledge
- Library — Store and reuse durable knowledge.
- Decision Log — Record important decisions and approvals.
- History — Keep a concise diary of completed work.
- Dreaming — Improve local bSmart content while you sleep.
- Improvement Scout — Find external ideas to improve bSmart itself.

### System
- Safety — Keep actions transparent and low-risk.
- Security Watch — Check visible VPS/container security drift.
- Setup — Initialize and maintain bSmart structure.
- Extensions — Enable optional add-on packs.
- Features — Show available bSmart capabilities.

## Feature details

### Projects

```yaml
name: Projects
group: Work
status: active
visibility: user-facing
short_description: Manage project context and project folders.
files:
  - /workspace/bSmart/Projects/
  - /workspace/bSmart/bSmart_State.md
  - /workspace/bSmart-System/bSmart_Protocols/projects.md
  - /workspace/bSmart-System/bSmart_Templates/project.template.md
description: Creates, lists, opens, and manages bSmart projects. Includes active project selection, project folders, project metadata, project status, and project-specific agent focus.
commands:
  - list projects
  - show active project
  - open project <name>
  - create project <name>
  - show project focus
included_capabilities:
  - Active project state
  - Project registry
  - Project-specific agent focus
  - Project archive status
notes:
  - Keep project-related subfeatures under Projects instead of listing them as separate top-level features.
  - Projects live under /workspace/bSmart/Projects unless explicitly archived or moved.
```

### Tasks

```yaml
name: Tasks
group: Work
status: active
visibility: user-facing
short_description: Track next actions and handoffs.
files:
  - /workspace/bSmart/bSmart_TODO.md
  - /workspace/bSmart-System/bSmart_Templates/bSmart_TODO.template.md
description: Maintains a concise checklist of completed items, next tasks, decisions, and safe resume points across sessions.
commands:
  - show todo
  - show bSmart TODO
included_capabilities:
  - Current TODO list
  - Session handoff
  - Safe resume points
notes:
  - Keep TODOs actionable and current when work is completed or deferred.
```

### Workdocs

```yaml
name: Workdocs
group: Work
status: active
visibility: user-facing
short_description: Keep detailed notes for larger work.
files:
  - /workspace/bSmart/Workdocs/
  - /workspace/bSmart-System/bSmart_Protocols/workdocs.md
  - /workspace/bSmart-System/bSmart_Templates/WORKDOC.template.md
description: Creates structured working documents for non-trivial, multi-session, troubleshooting, verification, or system-structure work.
commands:
  - create workdoc
  - show workdocs
included_capabilities:
  - Multi-session notes
  - Troubleshooting notes
  - Verification notes
  - Workdoc archive flow
notes:
  - Archive completed workdocs into the Library only after operator choice and category selection.
```

### Library

```yaml
name: Library
group: Knowledge
status: active
visibility: user-facing
short_description: Store and reuse durable knowledge.
files:
  - /workspace/bSmart/Library/
description: Stores reusable notes, references, templates, completed outputs, and curated knowledge so they can be browsed, improved, and reused later.
commands:
  - show library
  - search library <query>
included_capabilities:
  - Reusable knowledge storage
  - Reference material
  - Templates and examples
  - Archived completed outputs
notes:
  - Library is top-level because exposing it encourages active user interaction and curation.
  - Archive is an action or state within Projects, Workdocs, and Library, not a separate top-level feature.
```

### Decision Log

```yaml
name: Decision Log
group: Knowledge
status: active
visibility: user-facing
short_description: Record important decisions and approvals.
files:
  - /workspace/bSmart/bSmart_Log.md
  - /workspace/bSmart-System/bSmart_Protocols/operations.md
description: Captures meaningful setup, update, approval, migration, and project milestones without duplicating routine transcript detail.
commands:
  - show bSmart log
included_capabilities:
  - Milestone logging
  - Approval logging
  - Important decision history
notes:
  - Do not log secrets, routine tool output, or full transcripts.
```

### History

```yaml
name: History
group: Knowledge
status: active
visibility: user-facing
short_description: Keep a concise diary of completed work.
files:
  - /workspace/bSmart/bHistory.md
  - /workspace/bSmart-System/bSmart_Protocols/history.md
  - /workspace/bSmart-System/bSmart_Templates/bHistory.template.md
description: Records meaningful completed tasks and milestones as short dated bullets, with optional references to detailed decisions, workdocs, project files, or published changes.
commands:
  - show bHistory
  - show recent history
  - search bHistory <query>
included_capabilities:
  - Concise completed-work diary
  - Optional references to detail records
  - Recent-history lookup
notes:
  - bHistory is not a TODO list, decision log, workdoc, transcript, or backup manifest.
  - Do not load the full diary by default; search it or read its recent tail when needed.
```

### Dreaming

```yaml
name: Dreaming
group: Knowledge
status: active
visibility: user-facing
short_description: Improve local bSmart content while you sleep.
files:
  - /workspace/bSmart-System/bSmart_Protocols/dreaming.md
  - /workspace/bSmart/Projects/bSmart/data/bsmart-dreaming.yaml
  - /workspace/bSmart/Workdocs/dreaming/
description: Runs scheduled content-quality checks for a bSmart instance. Daily Dreaming is low-token and focuses on recent session/content changes. Weekly Dreaming is broader and focuses on stale content, conflicts, duplication, and safe compaction opportunities. Clear low-risk instance-content changes may be applied automatically with hidden backups; unclear, project, or destructive changes require operator review.
commands:
  - show dreaming
  - configure dreaming
  - run daily dreaming
  - run weekly dreaming
  - dream review <run-id>
  - dream inspect <action-id>
  - dream undo <action-id>
  - dream project <name>
  - nap
included_capabilities:
  - Daily recent-session content cleanup
  - Weekly broader content review
  - Hidden backups and undo/review manifests
  - Stale-content detection
  - Conflict detection
  - Token-saving compaction suggestions
  - On-request Dream Project review
  - End-of-session Nap handoff
  - Per-instance opt-in/disable setup
notes:
  - Dreaming improves instance-local bSmart content, not bSmart-System itself.
  - Hidden backups live under /workspace/bSmart/.dreaming-backups and should not be scanned during normal work.
  - Ask before permanent deletion, unclear conflict resolution, project content changes, or bSmart-System/system/deploy/runtime changes.
  - If multiple Dreaming asks are pending, list all items first in one-line summaries, then present them one-by-one with interactive choices/buttons when the user is present; cron reports should include the same compact list plus options for later review.
  - Unhandled Dreaming asks persist in a small backlog until accepted/rejected/postponed/undone; no-op days should stay silent or update tiny state, not create bulky reports or repeat old asks.
  - Dream reports and decisions should be terse by default: 3–8 chat lines for non-empty reports, one-line item summaries, one-sentence decision prompts, and details only on request.
  - Setup should record disabled/no-ask choices so /new does not repeatedly prompt.
```

### Improvement Scout

```yaml
name: Improvement Scout
group: Knowledge
status: active
visibility: user-facing
short_description: Find external ideas to improve bSmart itself.
files:
  - /workspace/bSmart/Projects/bSmart/data/bsmart-improvement-scout.yaml
  - /workspace/bSmart/Projects/bSmart/data/bsmart-improvement-scout-*.md
  - Hermes cron job: bSmart improvement scout
description: Runs a scheduled bSmart-focused research pass over selected sources such as Hermes, agent CLI ecosystems, MCP tooling, GitHub trends, Fabric, and operator-added URLs. It looks for practical ideas, releases, tools, and patterns that could improve bSmart without bloating it. It prepares accept/reject/postpone recommendations only; it does not edit bSmart-System or deploy changes without later operator acceptance.
commands:
  - show improvement scout
  - run improvement scout
  - bSmart add <url>
included_capabilities:
  - Weekly external source review
  - Curated source list with cursor state
  - Up to ten source inspections per scheduled run
  - Up to three recommendations per run
  - Accept/reject/postpone proposal workflow
  - Operator-added source URLs
notes:
  - This is distinct from bSearch, which is broader knowledge discovery and curation.
  - This is distinct from Dreaming, which improves local bSmart content/state rather than scouting external ideas.
  - Current SschwAdmin cron job is `bSmart improvement scout` (`eb2f57b305a5`), scheduled Sunday 01:30 UTC.
```

### Safety

```yaml
name: Safety
group: System
status: active
visibility: user-facing
short_description: Keep actions transparent and low-risk.
files:
  - /workspace/bSmart-System/bSmart_Protocols/operations.md
  - /workspace/bSmart/bSmart_Agent.md
description: Defines safe operating behavior: read-first inspection, explicit approval gates, reversible-change preference, secret handling, visible action notes, and careful shared-permission changes.
commands:
  - show guardrails
included_capabilities:
  - Operator guardrails
  - Smart approval mode
  - Visible action notes
  - Shared group permissions
  - Secret-safe handling
notes:
  - bSmart guardrails remain mandatory even if framework approvals are relaxed.
  - Never blanket-change runtime, backup, or application data folders without explicit scope approval.
```

### Security Watch

```yaml
name: Security Watch
group: System
status: active
visibility: user-facing
short_description: Check visible VPS/container security drift.
files:
  - /workspace/bSmart-System/bSmart_Protocols/security-watch.md
  - /opt/data/home/.hermes/scripts/bsmart-security-watch.py
description: Runs a low-noise, read-only security drift check from the designated admin instance. It verifies visible mounts, helper scripts, blueprints, obvious risky Compose/Dockerfile patterns, backup-file permission signals, and watched-file changes. Ordinary AI containers should not run this by default; bSmart setup should ask whether the current instance is the designated owner.
commands:
  - show security watch
  - run security watch
included_capabilities:
  - Weekly script-only watchdog
  - Visible mount posture checks
  - Blueprint/helper drift detection
  - Obvious secret/risky-pattern detection
  - Opt-in ownership per AI container
notes:
  - SschwAdmin is the default owner for Erling's VPS.
  - The lightweight weekly job is silent unless new findings, changed watched files, or check failures appear.
  - Live Docker/Dokploy state and host package CVEs require a future least-privilege host helper.
```

### Setup

```yaml
name: Setup
group: System
status: active
visibility: user-facing
short_description: Initialize and maintain bSmart structure.
files:
  - /workspace/HERMES.md
  - /workspace/bSmart-System/bSmart.md
  - /workspace/bSmart-System/bSmart_Setup.md
  - /workspace/bSmart-System/bSmart_Templates/
  - /workspace/bSmart-System/bSmart_Protocols/
  - /workspace/bSmart/
description: Creates, verifies, and repairs the local bSmart structure, including folders, templates, local state files, bootstrap behavior, content-root separation, optional instance Git, secret-provider configuration, and protocol discovery.
commands:
  - run bSmart setup
  - verify bSmart bootstrap
  - show bSmart paths
  - show protocols
included_capabilities:
  - Bootstrap chain
  - Local content root
  - Optional instance Git onboarding
  - Secret-provider onboarding
  - Protocol discovery
  - Template setup
  - Local state setup
notes:
  - Keep local content out of bSmart-System unless the operator explicitly asks for examples or templates.
  - Protocols are internal operating instructions and should usually appear under Setup, Safety, or the relevant user-facing feature.
```

### Extensions

```yaml
name: Extensions
group: System
status: active
visibility: user-facing
short_description: Enable optional add-on packs.
files:
  - /workspace/bSmart-Extensions/
  - /workspace/bSmart-System/bSmart.md
  - /workspace/bSmart-System/bSmart_Setup.md
description: Provides a standard location and setup flow for optional add-on packs, including bundled extensions such as bSearch and external packs such as Fabric, without mixing instance-installed state into core bSmart.
commands:
  - show extensions
included_capabilities:
  - Optional prompt packs
  - External workflow libraries
  - Bundled knowledge discovery (`bSearch`)
  - Bundled workflow memory (`bWorkflow`)
  - Bundled selective source-context retrieval (`bSelective`)
  - Bundled multi-agent orchestration protocol (`bSwarm`)
notes:
  - Extensions are discovered from /workspace/bSmart-Extensions subfolders.
```

### Features

```yaml
name: Features
group: System
status: active
visibility: user-facing
short_description: Show available bSmart capabilities.
files:
  - /workspace/bSmart-System/bSmart_Features.md
  - /workspace/bSmart-System/bSmart_Setup.md
  - /workspace/bSmart-System/bSmart.md
description: Provides the user-facing feature list, feature index, grouped views, detail cards, file links, commands, and update rules.
commands:
  - show features
  - show bSmart features
  - show feature index
  - show features by group
  - show feature <name>
included_capabilities:
  - Feature list
  - Feature index
  - Grouped feature view
  - Feature detail cards
notes:
  - Keep the main feature list at user-product level, not implementation level.
  - Put subfeatures and internal mechanisms inside the relevant detail card.
```
