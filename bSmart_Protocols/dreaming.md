# bSmart Protocol: Dreaming

```yaml
protocol:
  id: dreaming
  title: Dreaming
  purpose: Low-noise scheduled maintenance for bSmart content quality.
  use_when:
    - configuring scheduled bSmart content cleanup
    - reviewing stale/conflicting/verbose bSmart content
    - preparing safe compaction or pruning proposals
  scope:
    includes:
      - /workspace/bSmart content files
      - project TODOs and project.md files
      - workdocs and library notes
      - instance-local bSmart configuration
    excludes_by_default:
      - /workspace/bSmart-System system changes
      - deploy/runtime files
      - secrets
      - external publication
```

## Purpose

Dreaming is a bSmart feature for improving an **instance's bSmart content**, not the reusable bSmart system itself.

Its goals are:
- remove or propose removal of stale content;
- detect and reconcile conflicting content;
- compact verbose content so future sessions use fewer tokens;
- preserve meaning, approvals, important decisions, and useful context;
- keep active TODOs, project state, workdocs, and library entries coherent.

## Operating model

```yaml
modes:
  daily:
    default_frequency: daily
    default_time_local: around 04:00 Norway time
    default_scope: current_day_or_recent_session_activity
    token_budget: low
    default_output: small dream note plus concise user delivery only if useful
  weekly:
    default_frequency: weekly
    default_time_local: Friday night to Saturday around 04:00 Norway time
    default_scope: overall bSmart content quality
    token_budget: moderate_but_bounded
    focus:
      - stale content
      - conflicting content
      - compression opportunities
      - duplicated TODOs or decisions
      - project/library/workdoc organization
```

## Safety and automation policy

Dreaming is for **instance content**. It must not treat `/workspace/bSmart-System` as cleanup scope. The agent may be the main developer of bSmart-System, but Dreaming itself improves `/workspace/bSmart` and comparable per-instance content roots.

Dreaming must also stay separate from **research/discovery/review jobs** such as bSearch, bSmart improvement scout, Hermes release watch, security watch, or browser/Chrome scouting. Those jobs own their own candidate lists, shortlists, pending review state, reports, and follow-up decisions. Dreaming may only note operational drift around those jobs (for example oversized stale reports, duplicate local files, or broken metadata). It must not copy their recommendations into the Dreaming backlog, re-present their shortlist as Dreaming items, score/archive their items, or otherwise become a second review queue for research output.

Default posture balances automation with reversibility:
- automatically apply low-risk, clear, instance-content improvements when configured to do so;
- create a backup snapshot before every applied change;
- write a change manifest so any Dream action can be reviewed or undone later;
- ask the operator when the change is unclear, potentially destructive, touches active project meaning, or would alter audit/safety-relevant content;
- never remove approvals, audit-relevant decisions, safety notes, or active handoff state merely to save tokens;
- do **not** edit `/workspace/bSmart-System`, deploy, push, chmod/chown, or modify runtime/host state as part of Dreaming.

Automation classes:
```yaml
auto_allowed_with_backup:
  - compress verbose non-active instance notes without changing meaning
  - remove exact duplicate stale lines when one canonical copy is clear
  - mark obviously stale generated/cache/index files as excluded from normal search
  - update Dreaming indexes/manifests/reports
  - archive clearly obsolete instance-only scratch notes into a hidden Dream backup/archive area instead of deleting
ask_first:
  - deleting content permanently
  - moving or rewriting active project files
  - changing project goals, active TODO semantics, decisions, approvals, safety warnings, access model, or user preferences
  - resolving non-obvious conflicts
  - any Dream Project action
  - anything touching bSmart-System
```

Backups are mandatory before applied changes. Prefer reversible rewrite/archive over deletion.

## Setup prompt rule

During bSmart setup or re-setup, if Dreaming is not configured for this instance, ask:

> Enable bSmart Dreaming for this AI instance?

Recommended choices:
1. `Yes — use defaults` — daily around 04:00 and weekly Friday night/Saturday around 04:00 Norway time.
2. `Customize schedule` — operator specifies daily and weekly frequency/time.
3. `No — do not ask again` — record disabled in local `bSmart_Agent.md` so `/new` does not keep prompting.
4. `Later — ask again on future setup/startup`.

Record the choice in instance-local `bSmart_Agent.md` or another local bSmart state/config file. Do not hardcode all containers to run Dreaming.

## Configuration shape

```yaml
dreaming:
  status: enabled | disabled | ask_later
  owner_instance: <agent-name>
  local_timezone: Europe/Oslo
  content_scope:
    system_root_excluded: /workspace/bSmart-System
    instance_root: /workspace/bSmart
    project_roots_default: exclude_active_projects_unless_requested
  backup:
    required_before_change: true
    hidden_root: /workspace/bSmart/.dreaming-backups
    exclude_from_regular_search: true
    per_run_layout: YYYY-MM-DDTHHMMSSZ/<action-id>/
    manifest: manifest.jsonl
    restore_policy: review_selected_action_then_restore_or_modify
  automation:
    clear_stale_or_conflict: apply_with_backup
    unclear_or_meaning_changing: ask_first
    project_content: ask_first
    permanent_delete: ask_first
  daily:
    enabled: true
    schedule: "0 2 * * *"
    intent: around 04:00 Norway time; UTC schedule may be approximate across DST
    scope: recent_session_and_changed_bSmart_content
    token_budget: low
    auto_apply_clear_changes: true
  weekly:
    enabled: true
    schedule: "30 2 * * 6"
    intent: Friday night/Saturday around 04:00 Norway time; UTC schedule may be approximate across DST
    scope: overall_bSmart_content
    token_budget: moderate_bounded
    auto_apply_clear_changes: true
  outputs:
    root: /workspace/bSmart/Workdocs/dreaming
    format: dated markdown report plus concise Telegram delivery
```

## Backup and undo model

Before any Dreaming run applies a content change, it must create a backup under the hidden root, default:

`/workspace/bSmart/.dreaming-backups/`

This directory is intentionally hidden and should be excluded from normal interactive search, regular project/workdoc scans, and token-loading. It exists for review/undo only.

Each changed action should have:
- a unique action id;
- original file copy or pre-change patch;
- resulting diff or short description;
- category: `compression`, `stale_cleanup`, `conflict_resolution`, `organization`, `index_update`, or `nap_handoff`;
- confidence: `clear` or `needs_review`;
- restore instruction.

Undo/review flow:
1. Dream report lists action ids with 1–2 sentence summaries.
2. User selects an action id to inspect.
3. Agent shows detailed diff/context and offers restore, modify, keep, or postpone.

## Backlog and unattended no-op policy

Unresolved Dreaming asks must persist until handled. They should not be forgotten just because the user is away for days.

Use a small instance-local backlog file, default:

`/workspace/bSmart/Workdocs/dreaming/pending-dream-actions.jsonl`

Backlog rules:
- append new pending asks/actions as JSONL records with `status: pending`;
- preserve pending records across later Dreaming runs;
- when the user returns, show the backlog as one-line summaries and process items one-by-one;
- update status to `accepted`, `rejected`, `postponed`, `undone`, or `superseded` rather than deleting records;
- deduplicate obvious repeats by linking a later run to the existing pending action instead of adding another copy.

No-op/no-interaction rule:
- If no relevant content changed and no new Dreaming actions/asks were produced, do not create a bulky new report.
- Optionally update a tiny state file with `last_noop_run_at`, `files_scanned`, and `reason: no_relevant_changes`.
- Do not repeat-deliver old pending asks every day when the user has not interacted; keep them in the backlog for the next user-visible Dream review.
- If new real Dreaming findings appear while old asks are pending, append them to the same backlog; pending dreams may stack, but no-op dreams should not inflate content.

## Brevity/token policy

Dreaming interaction must be terse by default. Use detail files for depth; chat should only carry enough to decide next action.

Defaults:
- no-op run: silent, or tiny state only;
- non-empty scheduled report: aim for 3–8 lines in chat;
- item list: max one line per item;
- decision prompt: one sentence plus choices;
- details only on `Inspect details` or explicit request;
- avoid repeating file lists, diffs, backups, and rationale in chat unless needed for the current decision.

## Dream report format

Every non-empty Dreaming run should end with a compact report. The detailed artifacts stay in `/workspace/bSmart/Workdocs/dreaming/`; the chat delivery should be short. Empty/no-op scheduled runs should stay silent or write only tiny state, depending on scheduler requirements.

Recommended report sections:
```yaml
summary:
  run_id: <timestamp-or-id>
  mode: daily | weekly | nap | dream_project
  elapsed: <duration>
  scanned:
    files: <count>
    recent_sessions: <count-or-omitted>
  changes:
    compression: <count>
    stale_cleanup: <count>
    conflict_resolution: <count>
    organization: <count>
    index_update: <count>
    nap_handoff: <count>
  asks_pending: <count>
  backup_root: /workspace/bSmart/.dreaming-backups/<run-id>
commands:
  - dream review <run-id>
  - dream inspect <action-id>
  - dream undo <action-id>
  - dream keep <action-id>
  - dream postpone <action-id>
```

Two-step detail UX:
1. `dream review <run-id>` lists each Dream action with a short 1–2 sentence description.
2. `dream inspect <action-id>` shows the exact diff/context and offers keep/undo/modify/postpone.

Interactive decision UX:
- When Dreaming finds pending asks in a live user session, present them as interactive choices/buttons when the platform supports it.
- For a single pending ask, offer choices such as `Accept`, `Reject`, `Postpone`, and `Inspect details`.
- For multiple pending asks, first list **all** pending items in a compact review list, max one line per item.
- After showing the full list, present the first pending item for decision with choices such as `Accept`, `Reject`, `Postpone`, and `Inspect details`.
- Process pending asks one-by-one. After each response/action, move to the next pending item until all are handled or the user stops/postpones the review.
- For scheduled cron delivery, the user may be absent; include the compact one-line list plus command/options in the report, then handle the next reply interactively when the user returns.
- Do not force the operator to type exact command syntax when an interactive choice can safely express the decision.

## Daily run guidelines

Daily Dreaming should be cheap:
1. Inspect only recent session context, recent bSmart logs/TODO changes, active project state, and files modified in the last 24–36 hours.
2. Avoid active project content unless the recent work clearly requires a nap/handoff update; normal project cleanup belongs to Dream Project.
3. Identify stale handoff items, duplicate TODOs, unresolved conflicts, and obvious compaction opportunities.
4. Auto-apply only clear low-risk instance-content changes with backups; ask for unclear or meaning-changing changes.
5. Produce at most 3 user-visible findings.
6. Write a short dated report under `/workspace/bSmart/Workdocs/dreaming/`.
7. Deliver a compact summary with review/undo commands.

## Weekly run guidelines

Weekly Dreaming may look more broadly, but must still stay bounded:
1. Start with indexes and metadata: feature registry, active project list, TODO headings, workdoc/library filenames, and recent log entries.
2. Exclude `/workspace/bSmart-System` from cleanup scope; only use it as protocol reference.
3. Avoid rewriting project content automatically. For projects, produce Dream Project suggestions unless the change is only a global index/handoff note.
4. Sample/read full files only when metadata indicates drift, duplication, conflict, or verbosity.
5. Produce grouped findings:
   - applied safe changes with backup action ids;
   - stale/remove/archive candidates;
   - conflicts to resolve;
   - compaction candidates;
   - organization improvements;
   - possible new Dreaming checks.
6. Prefer specific file/section targets over long commentary.
7. Deliver a compact summary with review/undo commands.

## Dream Project

Dream Project is an on-request variant for a selected project. It is not part of automatic daily/weekly cleanup.

Rules:
- only run when the operator asks for it, for example `dream project <name>`;
- inspect that project's `project.md`, TODO, workdocs, data notes, and related library entries;
- propose one item at a time or a short numbered list;
- always ask before applying each project change;
- include less-invasive variants when appropriate, such as “archive a copy and add a short summary” instead of rewriting/deleting;
- create backups before any accepted project edit.

## Nap

Nap is a short end-of-session handoff command, conceptually `nap` or `/nap` if the host framework later supports a slash command.

Purpose:
- make sure the current session's useful work is recorded before starting fresh;
- update active project notes, workdocs, TODO, bSmart log, and relevant Git status notes as appropriate;
- create a compact handoff so the next `/new` starts cleanly.

Nap behavior:
1. Identify current active project/session focus.
2. Save or update only the necessary instance-local notes.
3. If files are changed, create Dreaming backups for pre-change state and record action ids.
4. Report very briefly: what was updated, any pending decisions, and whether Git has uncommitted changes.
5. If integrated slash-command support is unavailable, tell the user: “Nap done — ready for `/new`.” Do not itself assume it can issue `/new` on the user's behalf unless the platform/framework explicitly supports that.

## Possible future Dreaming checks

- Detect TODO items marked complete in one file but still pending elsewhere.
- Flag project files whose active status contradicts `bSmart_State.md`.
- Identify long workdocs that should be archived into Library summaries.
- Detect duplicated decisions across project notes and the global log.
- Suggest moving reusable knowledge from workdocs into Library.
- Maintain a compact per-instance “content index” to reduce future token use.
- Track repeated user corrections that should become bSmart protocol updates, while still requiring approval before system edits.
