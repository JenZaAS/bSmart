# bSwarm run — <short title>

## Summary

- Goal: <one line>
- Outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
- Workflow keyword: ordinary | bSelective | architect | bSelective architect | cascade | bSelective cascade
- Workflow: direct | architect_handoff | architect_taskflow
- Mode: unsupervised | supervised
- A/B: off | report | self_improving
- bSelective: all_off | all_on | mixed_ab
- Branch shape: direct_worker | architect_coder | mixed
- Recommendation: <one line>
- Next step: <one line>

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
      stages: [coder]
    bselective:
      pattern: direct_worker
      stages: [coder]
    architect:
      pattern: architect_coder
      stages: [architect, coder]
      artifacts:
        architect_plan: architect/architect-plan.md
    bselective_architect:
      pattern: architect_coder
      stages: [architect, coder]
      artifacts:
        architect_plan: bselective-architect/architect-plan.md
    cascade:
      pattern: architect_taskflow
      stages: [architect, coder, architect_evaluation]
    bselective_cascade:
      pattern: architect_taskflow
      stages: [architect, coder, architect_evaluation]
      artifacts:
        architect_plan: bselective-cascade/architect-plan.md
  budgets:
    max_depth: ...
    max_total_child_agents: ...
    max_iterations: ...
    max_worker_attempts_per_supervisor: ...
  safety: ...
```

## Statistics

```yaml
run_stats:
  outcome: ...
  elapsed_seconds: unknown
  supervisor_count: ...
  architect_count: ...
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

| Branch | Stage | Duration seconds | API calls | Tool calls | Tool calls by type | bSelective calls | Whole-file reads | Input tokens | Output tokens | Reasoning tokens | Cache-read tokens | Fresh total tokens | Total with cache-read tokens | Tool-output chars | Target-related chars | MATLAB/runtime verification |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ordinary | coder | unknown | unknown | unknown | unknown | 0 | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | not_run |

Machine fields for each row:

```yaml
stage_stats:
  branch_id: ordinary
  stage: coder
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

Record combined architect+coder totals for architect/coder branches, and direct totals for direct-worker branches.

| Branch | Pattern | Stages | Duration seconds | Tool calls | bSelective calls | Whole-file reads | Fresh total tokens | Total with cache-read tokens | Tool-output chars | Target-related chars | Diff + / - | Verification |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| bselective_architect_coder | architect_coder | architect,coder | unknown | unknown | unknown | unknown | unknown | unknown | unknown | unknown | +unknown/-unknown | not_run |

## Role plan

- Shape: coder | architect -> coder | coder -> supervisor | architect -> coder -> supervisor
- Architect context brief: <exact files/functions/regions, required changes, forbidden changes>
- Coder brief: <architect-plan.md path, allowed duplicate file, verification checks>
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
| ordinary | coder | ordinary direct_worker | partial | medium | ... | <branch-output.md> |
| bselective_architect | architect | bSelective architect | partial | medium | ... | bselective-architect/architect-plan.md |

## Evidence

- `<reference>` — <short note>

## Verification

- `branch file exists` — passed | failed | partial | not_run — <short note>
- `no conflict markers` — passed | failed | partial | not_run — <short note>
- `exactly one classdef` — passed | failed | partial | not_run — <short note>
- `expected UI scaffolding strings` — passed | failed | partial | not_run — <short note>
- `diff stat against original source` — passed | failed | partial | not_run — <short note>
- `original source unchanged` — passed | failed | partial | not_run — <short note>
- `MATLAB/runtime verification` — passed | failed | partial | not_run — <short note>

## A/B/C comparison

Only include when A/B or A/B/C is enabled.

- Style: report | self_improving
- Variants: ordinary vs bselective vs architect vs bselective_architect vs cascade vs bselective_cascade
- Winner: ordinary | bselective | architect | bselective_architect | cascade | bselective_cascade | tie | inconclusive | none
- Did bSelective reduce architect discovery context? yes | no | inconclusive
- Did coder avoid repeating discovery? yes | no | inconclusive
- Did architect/coder improve quality? yes | no | inconclusive
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
