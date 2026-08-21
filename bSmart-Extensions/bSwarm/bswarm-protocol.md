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

## 6. Role output contract

All child outputs should be concise and structured:

```yaml
role_output:
  role: implementer | reviewer | context_scout | critic | supervisor | worker
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

## 7. Statistics

Stats are part of v1. Record what is available cheaply; use `unknown` rather than spending extra tokens to measure.

Track at minimum:

- mode, intent, outcome;
- supervisor/worker counts;
- retry count;
- evidence and verification counts;
- token estimate and context pressure when available;
- bSelective slice and whole-file signals when relevant.

## 8. Final report

Keep it quick-glance:

- recommendation;
- outcome;
- key evidence;
- unresolved disagreements;
- statistics summary;
- budget/limit status;
- one next action.

Save a run record with `templates/run-record.md` when useful or requested.
