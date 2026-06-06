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
    - show features
    - show bSmart features
    - show feature index
    - show features by group
    - show feature <name>
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
    output: Full feature card including files, longer description, commands, included capabilities, and notes.
```

## Feature list

1. Projects — Manage project context and project folders.
2. Tasks — Track next actions and handoffs.
3. Workdocs — Keep detailed notes for larger work.
4. Library — Store and reuse durable knowledge.
5. Decision Log — Record important decisions and approvals.
6. Safety — Keep actions transparent and low-risk.
7. Setup — Initialize and maintain bSmart structure.
8. Extensions — Enable optional add-on packs.
9. Features — Show available bSmart capabilities.

## Feature index

1. Projects
2. Tasks
3. Workdocs
4. Library
5. Decision Log
6. Safety
7. Setup
8. Extensions
9. Features

## Features by group

### Work
- Projects — Manage project context and project folders.
- Tasks — Track next actions and handoffs.
- Workdocs — Keep detailed notes for larger work.

### Knowledge
- Library — Store and reuse durable knowledge.
- Decision Log — Record important decisions and approvals.

### System
- Safety — Keep actions transparent and low-risk.
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
description: Creates, verifies, and repairs the local bSmart structure, including folders, templates, local state files, bootstrap behavior, content-root separation, and protocol discovery.
commands:
  - run bSmart setup
  - verify bSmart bootstrap
  - show bSmart paths
  - show protocols
included_capabilities:
  - Bootstrap chain
  - Local content root
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
description: Provides a standard location and setup flow for optional external packs such as Fabric without mixing them into core bSmart.
commands:
  - show extensions
included_capabilities:
  - Optional prompt packs
  - External workflow libraries
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
