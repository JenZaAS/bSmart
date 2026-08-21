# bSwarm chat protocol v1

Use this protocol when Erling asks to run a bSwarm before a dedicated command handler exists.

## 1. Draft concise run spec

Show this quick-glance summary before launching agents:

```yaml
bswarm_run:
  goal: <one-line goal>
  scope: <path/reference or none>
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
```

Offer: start, edit mode/roles, edit A/B, edit statistics, edit budgets, edit context/bSelective, edit safety, cancel.

## 2. Defaults

Use these unless Erling changes them:

- simple spec/review work: `mode: unsupervised`, `max_depth: 1`, `max_total_child_agents: 3`;
- high-assurance work: `mode: supervised`, `max_depth: 2`, `max_total_child_agents: 4`;
- `max_iterations: 5`;
- `max_worker_attempts_per_supervisor: 5`;
- `statistics: on`;
- `safety: read_only`.

## 3. Modes

### unsupervised

Coordinator launches workers directly.

Use for breadth, speed, or independent perspectives.

### supervised

Coordinator launches supervisors/evaluators. Each supervisor launches or evaluates worker attempts.

Use when correctness/evidence matters enough to justify extra cost.

Supervisor retry rules:

- retry only for a diagnosed gap;
- retry only within `max_worker_attempts_per_supervisor`;
- return `partial`, `not_reached`, or `inconclusive` instead of looping;
- never launch another bSwarm.

## 4. A/B testing

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
- prompt/rubric comparison: prompt A vs prompt B.

## 5. bSelective

Modes:

- `all_off`: no bSelective.
- `all_on`: bSelective for all relevant subagents.
- `mixed_ab`: bSelective on/off variants; usually `ab_testing: report`.

When active, record adapter, slices, whole-file fallbacks, and missing context.

## 6. Recommended run shapes

Choose the smallest role chain that fits the task:

- 1 agent: `programmer` — simple direct implementation.
- 2 agents: `architect -> programmer` — large files or unclear context.
- 2 agents: `programmer -> supervisor` — simple work needing review.
- 3 agents: `architect -> programmer -> supervisor` — important or risky work.

For bSelective-heavy runs, the architect should own most context discovery. The programmer should receive the exact target file, exact functions/line regions, required changes, forbidden changes, and concise relevant context. This reduces repeated broad reading and makes bSelective more useful.

## 7. Roles

### Supervisor

Quality/evidence role. Responsibilities:

- define acceptance criteria;
- review outputs;
- judge pass/fail/revise;
- avoid broad implementation.

### Architect

Context/design role. Responsibilities:

- read knowledge first;
- use bSelective sparingly;
- identify files/functions/regions;
- write a precise programmer brief;
- avoid diving into all details.

### Programmer

Implementation role. Responsibilities:

- follow architect brief;
- edit target/duplicate files;
- run available checks;
- report diff, verification, and risks;
- avoid re-architecting unless blocked.

## 8. Role output contract

All child outputs should be concise and structured:

```yaml
role_output:
  role: architect | programmer | supervisor | implementer | reviewer | context_scout | critic | worker
  branch_id: <id>
  parent_branch_id: <id or none>
  outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
  confidence: low | medium | high
  summary: <1-3 bullets or short paragraph>
  evidence: [top 3-5]
  verification: [compact list]
  risks: [top 3]
  missing_context: [top 3]
  recommended_next_step: <one action or none>
  statistics_delta:
    tool_calls: unknown
    bselective_used: true | false
    selective_slice_count: 0
    whole_file_reads: unknown
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

## 9. Statistics

Stats are part of v1. Record what is available cheaply; use `unknown` rather than spending extra tokens to measure.

Track at minimum:

- mode, intent, outcome;
- supervisor/architect/programmer/worker counts;
- retry count;
- evidence and verification counts;
- token estimate and context pressure when available;
- bSelective slice and whole-file signals when relevant.

For bSelective/bSwarm comparison runs, also record context stats when cheaply available:

```yaml
context_stats:
  bselective_calls: N
  whole_file_reads: N
  tool_output_chars_total: N
  target_related_tool_output_chars: N | unknown
  fresh_input_tokens: N | unknown
  output_tokens: N | unknown
  reasoning_tokens: N | unknown
  cache_read_tokens: N | unknown
```

Tool-output characters matter because tool output becomes later model input context. If exact token counts are unavailable, record character counts and mark tokens `unknown`.

## 10. Final report

Keep it quick-glance:

- recommendation;
- outcome;
- key evidence;
- unresolved disagreements;
- statistics summary;
- budget/limit status;
- one next action.

Save a run record with `templates/run-record.md` when useful or requested.
