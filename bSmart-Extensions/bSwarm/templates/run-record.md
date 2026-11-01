# bSwarm run — <short title>

## Summary

- Goal: <one line>
- Outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
- Workflow keyword: ordinary | bSelective | architect | bSelective architect | cascade | cascade critic | cascade critic audit
- Workflow: direct | architect_handoff | architect_taskflow | critcascade | critcascade_audit
- Runtime adapter: hermes | opencode | codex | claude | unknown
- Preflight QC: passed | blocked | downgraded | not_run
- Mode: unsupervised | supervised
- A/B: off | report | self_improving
- bSelective: all_off | all_on | mixed_ab
- Branch shape: direct_worker | architect_worker | mixed
- Recommendation: <one line>
- Next step: <one line>

## Project job

Use for a bounded cascade that should be reopenable from project content.

- Package: `<project>/jobs/<YYYY-MM-DD>-<slug>/`
- Report: `report.md` — first-open quick-glance report, updated in place
- Plan: `plan.md`
- Index: `<project>/jobs/README.md`
- Report contract: external-audit bullets only; optional findings are count only.
- Trust / not verified: `<short note>`
- Audit model list: `./bSmart/State/bswarm-audit-models.yaml` — `<configured / empty / unavailable>`

## Run specification

```yaml
bswarm_run:
  goal: ...
  scope: ...
  workflow_keyword: ...
  workflow: ...
  mode: ...
  intent: ...
  ab_testing: ...
  bselective: ...
  statistics: on
  branches:
    ordinary:
      pattern: direct_worker
      stages: [worker]
    bselective:
      pattern: direct_worker
      stages: [worker]
    architect:
      pattern: architect_worker
      stages: [architect, worker]
      artifacts:
        architect_plan: architect/architect-plan.md
    bselective_architect:
      pattern: architect_worker
      stages: [architect, worker]
      artifacts:
        architect_plan: bselective-architect/architect-plan.md
    cascade:
      pattern: architect_taskflow
      stages: [architect, worker, architect_evaluation]
    bselective_cascade:
      pattern: architect_taskflow
      stages: [architect, worker, architect_evaluation]
      artifacts:
        architect_plan: bselective-cascade/architect-plan.md
  budgets:
    max_depth: ...
    max_total_child_agents: ...
    max_iterations: ...
    critique_loop:
      target_score: 8
      stop_requires_no_critical_issues: true
      stop_requires_no_required_issues: true
      no_hard_round_cap: true
      initial_round_budget: 10
      extension_rounds: 10
      continue_until_target: true
    max_worker_attempts_per_supervisor: ...
  safety: ...
```

## Preflight QC

Run before launching agents. If this blocks, do not start the cascade.

```yaml
preflight_qc:
  adapter: hermes | opencode | codex | claude | unknown
  status: passed | blocked | downgraded | not_run
  planned_timeout_seconds: 1200
  checks:
    delegation.orchestrator_enabled:
      required: true
      observed: unknown
      result: passed | failed | not_applicable
    delegation.max_spawn_depth:
      required: ">= 2"
      observed: unknown
      result: passed | failed | not_applicable
    delegation.child_timeout_seconds:
      required: ">= planned_timeout_seconds"
      observed: unknown
      result: passed | failed | not_applicable
  warning_to_user: <exact warning shown, or none>
  action_taken: start | stop_for_settings | downgrade_to_supervisor_mediated_architect_handoff | downgrade_to_supervisor_mediated_cascade
  audit_models:
    file: ./bSmart/State/bswarm-audit-models.yaml
    configured_order: []
    implementing_or_critic_model: <model id or unknown>
    result: passed | blocked_empty | blocked_same_model | unavailable
    warning_to_user: <exact warning shown, or none>
```

## Critic model and external audits

External audit rows apply only to `cascade critic audit`. In every `cascade critic` run, record the author and critic model IDs and whether the critic was independent. Prefer a different model; record same-model fallbacks as reduced independence. External audit model IDs come from the ordered instance-local list.

| Model ID | Kind | Finding | Class | Status | Stop reason |
|---|---|---|---|---|---|
| `<actual model id or not launched>` | design | `<finding>` | automatic / decision / optional | `<status>` | `<reason>` |
| `<actual model id or not launched>` | code | `<finding>` | automatic / decision / optional | `<status>` | `<reason>` |

- Auditor proposals are re-sorted by the parent agent; unsure means `decision`.
- Continue to the next auditor only for `automatic` or `decision`.
- Optional-only findings stop the auditor list.
- If an adapter cannot name/select a configured model, record `not launched` and why.

## Statistics

```yaml
run_stats:
  outcome: ...
  elapsed_seconds: unknown
  supervisor_count: ...
  architect_count: ...
  # Programming-only compatibility metric; use worker_count for generic runs.
  coder_count: ...
  worker_count: ...
  retry_count: ...
  token_estimate: unknown
  context_pressure: unknown
  evidence_count: ...
  verification_count: ...
  context_stats:
    bselective_calls: ...
    whole_file_reads: ...
    tool_output_chars_total: ...
    target_related_tool_output_chars: ...
    fresh_input_tokens: unknown
    output_tokens: unknown
    reasoning_tokens: unknown
    cache_read_tokens: unknown
    fresh_total_tokens: unknown
    total_with_cache_read_tokens: unknown
```

## Stage statistics

Record one row per branch stage. Use `unknown` rather than inventing unavailable provider numbers.

| Branch | Stage | Duration seconds | API calls | Tool calls | Tool calls by type | bSelective calls | Whole-file reads | Input tokens | Output tokens | Reasoning tokens | Cache-read tokens | Fresh total tokens | Total with cache-read tokens | Tool-output chars | Target-related chars | [programming-only] MATLAB/runtime verification |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ordinary | worker | unknown | unknown | unknown | unknown | 0 | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | not_run |

Machine fields for each row:

```yaml
stage_stats:
  branch_id: ordinary
  stage: worker
  duration_seconds: unknown
  api_calls: unknown
  tool_calls: unknown
  tool_calls_by_type: {}
  bselective_calls: 0
  whole_file_reads: unknown
  input_tokens: unknown
  output_tokens: unknown
  reasoning_tokens: unknown
  cache_read_tokens: unknown
  fresh_total_tokens: unknown
  total_with_cache_read_tokens: unknown
  total_tool_output_chars: unknown
  target_related_tool_output_chars: unknown
  diff_added_lines: unknown
  diff_removed_lines: unknown
  matlab_runtime_verification: not_run
```

## Branch total statistics

Record combined architect+worker totals for architect/worker branches, and direct totals for direct-worker branches.

| Branch | Pattern | Stages | Duration seconds | Tool calls | bSelective calls | Whole-file reads | Fresh total tokens | Total with cache-read tokens | Tool-output chars | Target-related chars | Diff + / - | Verification |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bselective_architect_worker | architect_worker | architect,worker | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | +unknown/-unknown | not_run |

## Role plan

- Shape: worker | architect -> worker | worker -> supervisor | architect -> worker -> supervisor
- Architect context brief: <exact files/functions/regions, required changes, forbidden changes>
- Worker brief: <architect-plan.md path, allowed artifact, verification checks>
- Supervisor acceptance criteria: <compact pass/fail criteria>

## Architect handoff defaults

Default architect handoff budget: the architect plan is a context-budget artifact, not a design essay or transcript dump.

```yaml
architect_handoff_defaults:
  target_words: 350-500
  hard_max_words: 700
  max_relevant_regions: 6
  max_must_implement_bullets: 6
  no_tool_transcripts: true
  no_long_source_quotes: true
  no_full_bselective_output: true
  required_sections:
    - target_file_path
    - relevant_regions
    - must_implement
    - defer
    - do_not_implement
    - risks
    - verification_checks
```

Architect plans should include one-line region reasons only and should not paste full bSelective output.

## Branch results

| Branch | Stage/Role | Variant | Outcome | Confidence | Summary | Artifact |
|---|---|---|---|---|---|---|
| ordinary | worker | ordinary direct_worker | partial | medium | ... | <branch-output.md> |
| bselective_architect | architect | bSelective architect | partial | medium | ... | bselective-architect/architect-plan.md |

## Critcascade review

Only include for `critcascade` runs. Complete and verify one task before the next;
the architect reviews and updates the remaining plan before each next task.

- Architect-plan explain-back by a reviewer without the architect's working context: `<summary/result>`
- Strict ready-to-build decision: `ready | blocked | revise` — `<rationale>`
- `decisions.md` / authoritative decision-record cross-check: `<checked files and result>`
- Architect critic model: `<model ID>`; independent from architect: `yes | no | unknown`
- Worker critic model: `<model ID>`; independent from worker: `yes | no | unknown`
- Architect re-plan after each completed task: `<artifact/reference>`
- Critique rounds / extension blocks used: `<round count / block count>`
- Critique stop reason: `target_reached | plateau | safety_block | operator_stop`
- Critique success fields: `target_score: 8`; `stop_requires_no_critical_issues: true`; `stop_requires_no_required_issues: true`; `no_hard_round_cap: true`
- Success only when: `score >= 8 AND critical_issues == 0 AND required_changes == 0`
- Rounds: initial `1–10`; extensions are successive 10-round blocks (`11–20`, `21–30`, ...)
- Progress events: finding closed with evidence; previously open required check completed with evidence; or same-rubric score increase with rationale
- At each complete block, zero progress events means record plateau and pause/ask; any safety blocker stops immediately

| Block | Round range | Progress events (count) | Evidence/reference | Decision |
|---|---|---:|---|---|
| Initial | 1–10 | ... | ... | extend / plateau / stop |
| Extension 1 | 11–20 | ... | ... | extend / plateau / stop |

| Round | Critic | Score (1-10) | Critical issues | Required changes | Status | Decision |
|---:|---|---:|---|---|---|---|
| 1 | architect_critic | ... | ... | ... | complete | pass |
| 1 | worker_critic | ... | ... | ... | complete | revise |

- Knowledge consulted: `<bKnowledge references>`
- Concise durable lessons extracted: `<none or entries>`

## Test selection

Only include when tests were added or changed.

- Planned / actual distinct scenarios: `<count / count>`; small-component default target: `10`
- Reported issue regressions: `<issue IDs or none>`
- Small-component scenarios above 10: `<architect rationale and critic approval, or not applicable>`
- Removed or deferred speculative/duplicate cases: `<brief or none>`

| Scenario | Requirement/issue/risk | Likelihood | Impact | Test added? | Rationale |
|---|---|---|---|---|---|
| `<scenario>` | `<reference>` | plausible / remote | low / meaningful / high | yes / no | `<brief>` |

## Evidence

- `<reference>` — <short note>

## Verification (general evidence is per-criterion)

Use the table as the primary general verification record; add domain-specific
checks only where relevant.

| criterion_or_claim | evidence_or_check | expected_signal | actual_result | reference |
|---|---|---|---|---|
| `<claim>` | `<check/evidence>` | `<expected>` | `<actual>` | `<reference>` |

Generic checks may include branch-file existence or absence of conflict markers.

## Programming-only verification examples

- `[programming-only] exactly one classdef` — passed | failed | partial | not_run — <short note>
- `[programming-only] expected UI scaffolding strings` — passed | failed | partial | not_run — <short note>
- `[programming-only] diff stat against original source` — passed | failed | partial | not_run — <short note>
- `[programming-only] original source unchanged` — passed | failed | partial | not_run — <short note>
- `[programming-only] MATLAB/runtime verification` — passed | failed | partial | not_run — <short note>

## A/B/C comparison

Only include when A/B or A/B/C is enabled.

- Style: report | self_improving
- Variants: ordinary vs bselective vs architect vs bselective_architect vs cascade vs bselective_cascade
- Winner: ordinary | bselective | architect | bselective_architect | cascade | bselective_cascade | tie | inconclusive | none
- Did bSelective reduce architect discovery context? yes | no | inconclusive
- Did the worker avoid repeating discovery? yes | no | inconclusive
- Did the architect/worker split improve quality? yes | no | inconclusive
- Cost/quality tradeoff: <short note>

## bSelective context

Only include when bSelective is active or being tested.

- Mode: all_on | all_off | mixed_ab
- Adapter: ...
- Slices used: ...
- Whole-file fallbacks: ...
- Missed/insufficient context: ...

## Supervisor judgements

Only include for supervised mode.

- Supervisor <id>: accepted/rejected/revised/inconclusive — <short rationale>

## Run artifacts

- `run-spec.yaml` — <path>
- branch outputs — <paths>
- architect plans — `*/architect-plan.md` paths, if applicable
- `run-record.md` — <path>
- `tool-read-stats.md` — <path>
- `comparison.md` — <path>
- `stats-index.md` — cross-run stats index update path, if applicable

## Decisions or follow-up

- Should update workflow/prompt/default? yes/no/needs approval — <short note>
- Follow-up: <one action>
