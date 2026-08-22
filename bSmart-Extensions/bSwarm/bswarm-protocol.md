# bSwarm chat protocol v1

Use this protocol when Erling asks to run a bSwarm before a dedicated command handler exists.

## 1. Draft concise run spec

Show this quick-glance summary before launching agents. Prefer the compact
workflow keyword interface unless Erling asks for internal branch/stage detail:

```text
ordinary
bSelective
architect
bSelective architect
cascade
bSelective cascade
```

Keyword meanings:

| Keyword | Meaning |
|---|---|
| `ordinary` | Direct ordinary coder; no bSelective context tooling. |
| `bSelective` | Direct bSelective-enabled coder. |
| `architect` | Ordinary architect → ordinary coder, using one compact handoff. |
| `bSelective architect` | bSelective architect → bSelective coder, using one compact handoff. |
| `cascade` | Ordinary architect-led stepwise workflow: decompose, dispatch one coder task, evaluate, re-plan, continue. |
| `bSelective cascade` | bSelective architect-led stepwise workflow with bSelective-enabled coders. |

Normalization rules:

- `ordinary` is the default direct mode and may be omitted internally.
- `architect` implies an architect followed by a coder.
- `cascade` implies architect-led stepwise execution; it is not a direct-coder mode.
- `bSelective` applies to all relevant stages by default.
- `bSelective architect` means bSelective architect and bSelective coder.
- `bSelective cascade` means bSelective architect, bSelective coders, and architect evaluation/replanning between tasks.
- Do not expose mixed bSelective architect → ordinary coder combinations as normal user-facing modes; keep them only for controlled experiments.

Internal normalization:

```yaml
ordinary:
  context_mode: ordinary
  workflow: direct
bSelective:
  context_mode: bselective
  workflow: direct
architect:
  context_mode: ordinary
  workflow: architect_handoff
  coder_context_mode: ordinary
bSelective architect:
  context_mode: bselective
  workflow: architect_handoff
  coder_context_mode: bselective
cascade:
  context_mode: ordinary
  workflow: architect_taskflow
  coder_context_mode: ordinary
bSelective cascade:
  context_mode: bselective
  workflow: architect_taskflow
  coder_context_mode: bselective
```

Then show the normalized run summary:

```yaml
bswarm_run:
  goal: <one-line goal>
  scope: <path/reference or none>
  workflow_keyword: ordinary | bSelective | architect | bSelective architect | cascade | bSelective cascade
  workflow: direct | architect_handoff | architect_taskflow
  mode: unsupervised | supervised
  intent: review | design | compare | implement | other
  ab_testing: off | report | self_improving
  bselective: all_off | all_on | mixed_ab
  statistics: on
  max_depth: 1 | 2
  max_total_child_agents: 3
  max_iterations: 5
  max_worker_attempts_per_supervisor: 5
  safety: read_only | propose_patches | approved_writes
  branches:
    ordinary:
      pattern: direct_worker
      context_mode: ordinary
      stages: [coder]
    bselective:
      pattern: direct_worker
      context_mode: bselective
      stages: [coder]
    architect:
      pattern: architect_coder
      architect_context_mode: ordinary
      coder_context_mode: ordinary
      stages: [architect, coder]
    bselective_architect:
      pattern: architect_coder
      architect_context_mode: bselective
      coder_context_mode: bselective
      stages: [architect, coder]
    cascade:
      pattern: architect_taskflow
      architect_context_mode: ordinary
      coder_context_mode: ordinary
      stages: [architect, coder, architect_evaluation]
    bselective_cascade:
      pattern: architect_taskflow
      architect_context_mode: bselective
      coder_context_mode: bselective
      stages: [architect, coder, architect_evaluation]
```

Offer: start, edit keyword, edit A/B/C branches, edit statistics, edit budgets, edit safety, cancel.

## 2. Preflight QC before launch

Before launching any run, do a short preflight QC and show blocking warnings
instead of starting a run that is likely to fail. For `architect`,
`bSelective architect`, `cascade`, and especially `bSelective cascade`, this is
mandatory if the run expects the architect subagent itself to dispatch coder
subagents. Earlier staged handoff runs can work with lower spawn depth because
the parent/supervisor runs architect first, then manually hands the plan to a
coder; that is `supervisor_mediated_architect_handoff`, not nested architect
dispatch.

Record the detected CLI/runtime adapter. bSwarm is portable, but nested
delegation checks are adapter-specific:

- `hermes` adapter: check live Hermes config and the current tool schema.
- `opencode`, `codex`, `claude`, or unknown adapter: do not assume Hermes
  nested delegation exists; require an adapter-specific nested-worker mechanism
  or downgrade to a supervisor-mediated cascade after telling the user.

Hermes cascade preflight checks:

```yaml
preflight_qc:
  adapter: hermes | opencode | codex | claude | unknown
  required_for_nested_architect_dispatch:
    delegation.orchestrator_enabled: true
    delegation.max_spawn_depth: ">= 2"
    delegation.child_timeout_seconds: ">= planned_timeout_seconds"
  recommended_for_bselective_cascade:
    delegation.child_timeout_seconds: 1200
```

If a required check fails, stop and report a concise settings warning with the
exact observed value and the suggested command when known, for example:

```text
bSwarm preflight blocked: nested architect dispatch needs Hermes delegation.max_spawn_depth >= 2.
Observed: delegation.max_spawn_depth = 1.
Suggested fix: hermes config set delegation.max_spawn_depth 2, then start /new or /restart before rerunning.
```

Do not silently continue as a true nested architect/cascade run when the adapter
cannot verify nested child dispatch. Either ask the user to fix settings, or
explicitly switch the run spec to `supervisor_mediated_architect_handoff` or
`supervisor_mediated_cascade` and record that it is not true nested
architect-dispatch.

## 3. Defaults

Use these unless Erling changes them:

- simple spec/review work: `mode: unsupervised`, `max_depth: 1`, `max_total_child_agents: 3`;
- high-assurance work: `mode: supervised`, `max_depth: 2`, `max_total_child_agents: 4`;
- `max_iterations: 5`;
- `max_worker_attempts_per_supervisor: 5`;
- `statistics: on`;
- `safety: read_only`.

## 4. Top-level modes

### unsupervised

Coordinator launches workers or branch stages directly.

Use for breadth, speed, independent perspectives, and most A/B/C comparison runs.

### supervised

Coordinator acts as supervisor mode or launches supervisors/evaluators. Each supervisor launches or evaluates worker attempts.

Use when correctness/evidence matters enough to justify extra cost.

Supervisor retry rules:

- retry only for a diagnosed gap;
- retry only within `max_worker_attempts_per_supervisor`;
- return `partial`, `not_reached`, or `inconclusive` instead of looping;
- never launch another bSwarm.

## 5. Explicit subagent modes

These are stage semantics for bSwarm-style Hermes test runs. Name them explicitly in prompts and run records.

### Supervisor mode

Purpose: orchestration and statistics only.

Rules:

- creates/validates the run folder;
- creates duplicate branch files when the test permits file edits;
- dispatches branch workers/stages;
- does not directly edit target implementation files unless explicitly asked;
- shields prior generated-code artifacts: do not include previous generated-run paths in worker prompts;
- collects per-branch and per-stage stats;
- writes run artifacts:
  - `run-spec.yaml`;
  - branch output files;
  - `architect-plan.md` files, if applicable;
  - `run-record.md`;
  - `tool-read-stats.md`;
  - `comparison.md`;
  - cross-run stats index updates such as `/projects/DigSoftware/workstreams/dd1d/ab-testing/stats-index.md`.

Supervisor verification must not trust child self-reports until directly checked:

- branch file exists;
- diff stats are available;
- no conflict markers;
- exactly one `classdef` for MATLAB class duplicates;
- original source unchanged;
- runtime/test status recorded if available.

### Architect mode

Purpose: context discovery and implementation design, not direct coding.

Architect handoff is a context-budget artifact for the coder, not a design essay. This compact handoff is a default bSwarm role behavior; future run prompts do not need to restate it unless they deliberately override the budget.

Default architect handoff budget for prototype/evaluation runs:

```yaml
architect_handoff_defaults:
  target_words: 350-500
  hard_max_words: 700
  max_relevant_regions: 6
  max_must_implement_bullets: 6
  no_tool_transcripts: true
  no_long_source_quotes: true
  no_full_bselective_output: true
```

Rules:

- must not edit implementation files;
- reads only enough context to produce a concrete implementation plan;
- writes a concise `architect-plan.md` for coder handoff;
- treats the handoff as a context-budget artifact for the coder;
- uses one-line reasons for relevant regions;
- keeps `must_implement`, `defer`, and `do_not_implement` sharply separated;
- for bSelective architect branches, use bSelective first where possible:
  - `list FILE all --compact`;
  - `list FILE functions --format text`;
  - targeted `get FILE function NAME`;
  - avoid whole-file fallback unless necessary and record it if used;
- for ordinary architect branches, use ordinary file/search tools only; no bSelective and no code-knowledge file unless the run explicitly permits it;
- keep output small enough to pass to coder without broad tool-output context.

Architect plan contract:

```yaml
architect_plan:
  target_file_path: <allowed duplicate file>
  budget:
    target_words: 350-500
    hard_max_words: 700
    max_relevant_regions: 6
    max_must_implement_bullets: 6
    no_tool_transcripts: true
    no_long_source_quotes: true
    no_full_bselective_output: true
  relevant_regions:
    - function_or_section: <name>
      lines: <start-end or start-?>
      why: <one-line reason only>
  must_implement:
    - <required change, max 6 bullets>
  defer:
    - <explicitly postponed item or none>
  do_not_implement:
    - <forbidden change or none>
  risks:
    - <top risks>
  verification_checks:
    - <branch file exists/no conflict markers/etc.>
```

### Coder mode

Purpose: implement the architect plan in the allowed duplicate file.

Rules:

- edits only the branch duplicate file;
- receives the design brief and architect plan;
- should not re-run broad discovery unless the architect plan is insufficient;
- if it needs more context, it may do targeted reads/searches and must report them;
- must not inspect previous generated-run archives unless explicitly permitted;
- reports concise summary, changed file, diff stats, tool/read behavior, caveats.

Coder verification checklist:

- branch file exists;
- no conflict markers;
- exactly one `classdef`;
- expected UI scaffolding strings present;
- diff stat against original source;
- original source unchanged;
- runtime/test status recorded if available.

## 6. A/B/C testing

A/B model:

```text
same goal + same rubric + different variant settings -> compare outcome/evidence/cost
```

Styles:

- `report`: compare and report; default for research/comparison.
- `self_improving`: bounded iterative improvement; requires `max_iterations`.

Common templates:

- mode comparison: `unsupervised` vs `supervised`;
- bSelective comparison: ordinary context vs bSelective-guided context;
- workflow comparison: workflow A vs workflow B;
- prompt/rubric comparison: prompt A vs prompt B;
- staged-context comparison: direct ordinary worker vs bSelective architect/coder vs ordinary architect/coder.

For DD1D-style A/B/C runs, use the keyword normalization unless deliberately
testing an internal override. The normal compact branch names are:

```yaml
branches:
  ordinary:
    pattern: direct_worker
    context_mode: ordinary
    stages: [coder]
  bselective:
    pattern: direct_worker
    context_mode: bselective
    stages: [coder]
  architect:
    pattern: architect_coder
    architect_context_mode: ordinary
    coder_context_mode: ordinary
    stages: [architect, coder]
  bselective_architect:
    pattern: architect_coder
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages: [architect, coder]
  cascade:
    pattern: architect_taskflow
    architect_context_mode: ordinary
    coder_context_mode: ordinary
    stages: [architect, coder, architect_evaluation]
  bselective_cascade:
    pattern: architect_taskflow
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages: [architect, coder, architect_evaluation]
```

Mixed combinations such as bSelective architect → ordinary coder may be used as
internal experimental overrides, but should not be offered as normal user-facing
keywords.

Cascade safeguards:

```yaml
cascade_defaults:
  max_tasks: 4
  max_coder_attempts_per_task: 1
  max_patch_calls_per_coder: 3
  stop_after_acceptance: true
  re_evaluate_after_each_task: true
```

## 7. bSelective

Modes:

- `all_off`: no bSelective.
- `all_on`: bSelective for all relevant subagents.
- `mixed_ab`: bSelective on/off variants; usually `ab_testing: report`.

When active, record adapter, slices, whole-file fallbacks, and missing context.

For bSelective-heavy architect/coder runs, the architect should own most context discovery. The coder should receive the exact target file, exact functions/line regions, required changes, forbidden changes, and concise relevant context. This reduces repeated broad reading and makes bSelective more useful.

## 8. Safety / contamination rules

For generated-code evaluation runs:

- never edit the real/original target source unless explicitly approved;
- duplicate source into branch files under the new run folder;
- do not include previous generated-run paths in worker prompts;
- do not allow workers to inspect `previous-generated-runs/` unless the test explicitly compares against old generated code;
- do not compare to prior generated code until after all workers finish;
- direct workers and coders edit only their allowed duplicate file;
- architects do not edit implementation files.

## 9. Recommended run shapes

Choose the smallest role chain that fits the task:

- 1 agent: `coder` — simple direct implementation.
- 2 agents: `architect -> coder` — large files or unclear context.
- 2 agents: `coder -> supervisor` — simple work needing review.
- 3 agents: `architect -> coder -> supervisor` — important or risky work.

## 10. Role output contract

All child outputs should be concise and structured:

```yaml
role_output:
  role: architect | coder | supervisor | worker
  branch_id: <id>
  stage: architect | coder | supervisor | direct_worker
  parent_branch_id: <id or none>
  outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
  confidence: low | medium | high
  summary: <1-3 bullets or short paragraph>
  changed_files: [<paths or none>]
  artifacts: [<architect-plan.md/branch-output.md/etc.>]
  evidence: [top 3-5]
  verification: [compact list]
  risks: [top 3]
  missing_context: [top 3]
  recommended_next_step: <one action or none>
  statistics_delta:
    duration_seconds: unknown
    api_calls: unknown
    tool_calls: unknown
    tool_calls_by_type: {}
    bselective_calls: 0
    bselective_used: true | false
    selective_slice_count: 0
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
    matlab_runtime_verification: not_run | passed | failed | partial
```

Supervisor judgement adds:

```yaml
supervisor_judgement:
  worker_branch_id: <id>
  goal_reached: true | false | partial | inconclusive
  acceptance_rationale: <compact>
  identified_gaps: [top gaps]
  retry_requested: true | false
  retry_reason: <compact or none>
  final_branch_recommendation: accept | reject | revise | inconclusive
```

## 11. Statistics

Stats are part of v1. Record what is available cheaply; use `unknown` rather than spending extra tokens to measure.

Collect both per-stage and combined per-branch stats:

- duration seconds;
- API calls;
- tool calls;
- tool calls by type;
- bSelective calls;
- whole-file reads/fallbacks;
- input tokens;
- output tokens;
- reasoning tokens;
- cache-read tokens;
- fresh total tokens = input + output + reasoning;
- total with cache-read tokens;
- total tool-output chars;
- target-related tool-output chars;
- diff added/removed lines;
- whether MATLAB/runtime verification ran.

Architect/coder runs should make it possible to answer:

- did bSelective reduce architect discovery context?
- did the coder avoid repeating discovery?
- did architect/coder split improve quality vs direct ordinary?
- did the split reduce or increase total tokens/tool calls?

## 12. Final report

Keep it quick-glance:

- recommendation;
- outcome;
- key evidence;
- unresolved disagreements;
- stage and branch statistics summary;
- budget/limit status;
- one next action.

Save a run record with `templates/run-record.md` when useful or requested.
