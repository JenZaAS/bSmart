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
- follow `/workspace/bSmart-System/bSmart_Protocols/state.md` for active/current project ownership and drift handling;
- ask the operator when the change is unclear, potentially destructive, would change canonical state, changes project goals/TODO meaning, or would alter audit/safety-relevant content;
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

During bSmart setup and on `/new`, inspect the instance-local Dreaming status before the normal TODO startup summary.

```yaml
startup_gate:
  missing_or_ask_later: trigger_setup_prompt
  enabled: continue_without_repeating_setup
  disabled: skip_setup_prompt_until_operator_requests_it
```

If the status is missing or `ask_later`, ask:

> Enable bSmart Dreaming for this AI instance?

Recommended choices:
1. `Yes — use defaults` — daily around 04:00 and weekly Friday night/Saturday around 04:00 Norway time.
2. `Customize schedule` — operator specifies daily and weekly frequency/time.
3. `No — do not ask again` — record `status: disabled` in local `bSmart_Agent.md` or another instance-local config so `/new` does not keep prompting.
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
- non-empty scheduled report: aim for 3–8 short, plain-language lines in chat;
- explain what was found and done in everyday words, without intimidating internal terminology;
- do not include filenames, backup paths, backup filenames, run IDs, action IDs, manifests, or internal commands in normal delivery;
- mention a safety copy only generically unless the user asks for details;
- summarize the number of earlier pending items and describe only the next item in plain language;
- decision prompt: one clear sentence plus simple choices;
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
- For a single pending ask, offer simple choices such as `Review it now`, `Later`, `Skip it`, and `Show details`.
- For multiple pending asks, say how many are waiting and summarize only the next item in plain language; do not expose internal IDs by default.
- Present the first pending item for decision with simple choices such as `Review it now`, `Later`, `Skip it`, and `Show details`.
- Process pending asks one-by-one. After each response/action, move to the next pending item until all are handled or the user stops/postpones the review.
- For scheduled cron delivery, the user may be absent; deliver only a short human summary and the next clear follow-up choice. Keep IDs, paths, commands, and detailed review options in the report/detail flow, not the normal message.
- Do not force the operator to type exact command syntax when an interactive choice can safely express the decision.

## Daily run guidelines

Daily Dreaming should be cheap:
1. Inspect only recent session context, recent bSmart logs/TODO changes, the canonical state file named by `/workspace/bSmart-System/bSmart_Protocols/state.md`, and files modified in the last 24–36 hours.
2. For active/current project drift, apply the state protocol's drift-handling rules instead of restating ownership here.
3. Avoid active project content unless the recent work clearly requires a nap/handoff update; normal project cleanup belongs to Dream Project.
4. Identify stale handoff items, duplicate TODOs, unresolved conflicts, and obvious compaction opportunities.
5. Auto-apply only clear low-risk instance-content changes with backups; ask for unclear or meaning-changing changes.
6. Produce at most 3 user-visible findings.
7. Write a short dated report under `/workspace/bSmart/Workdocs/dreaming/`.
8. Deliver a compact summary with review/undo commands.

## Recurring Dreams

Recurring Dreams are operator-defined, tag-driven checks performed by the existing daily or weekly Dreaming schedule. They extend Dreaming beyond content tidy work without creating a separate cron job for every small follow-up.

### Representation

Use a marker in an instance-local TODO item:

```text
[dream:<slug>]
```

The TODO item must point to a local workdoc or state file that defines the target, check method, and reporting rule. Keep the durable target details there rather than embedding a long instruction in the TODO line.

### Execution rules

1. The scheduled Dreaming run scans active TODO items for recognized `[dream:<slug>]` markers.
2. It performs only the check defined by the linked workdoc, using the narrowest available read-only access.
3. It compares the live result with the last recorded state and reports only new progress, feedback, status changes, closure, merge, or supersession.
4. It updates the local tracking state/workdoc with factual URLs, authors, timestamps, and short summaries when a change is found.
5. It stays silent when there is no change and does not create a normal Dreaming backlog item for a routine recurring check.
6. It must not publish, edit, react, label, merge, deploy, or otherwise change an external system unless a separate explicit operator action authorizes that operation.
7. A recurring Dream remains active until the TODO item is completed, the marker is removed, or the linked workdoc records it as superseded/disabled.

### Creation pattern

When the operator asks to create a recurring Dream, create or update:

- one concise active TODO item with `[dream:<slug>]`;
- one local workdoc/state record containing target, scope, cadence, last checked state, and reporting rules;
- the existing Dreaming job instructions only when the marker type is new and cannot use an established generic check.

Recurring Dreams are monitoring instructions, not a second research/review queue. They must not copy external recommendations into the Dreaming backlog or silently turn monitoring into publication.

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
