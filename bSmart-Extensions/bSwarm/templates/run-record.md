# bSwarm run — <short title>

## Summary

- Goal: <one line>
- Outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
- Mode: unsupervised | supervised
- A/B: off | report | self_improving
- bSelective: all_off | all_on | mixed_ab
- Recommendation: <one line>
- Next step: <one line>

## Run specification

```yaml
bswarm_run:
  goal: ...
  scope: ...
  mode: ...
  intent: ...
  ab_testing: ...
  bselective: ...
  statistics: on
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
```

## Role plan

- Shape: programmer | architect -> programmer | programmer -> supervisor | architect -> programmer -> supervisor
- Architect context brief: <exact files/functions/regions, required changes, forbidden changes>
- Supervisor acceptance criteria: <compact pass/fail criteria>

## Branch results

| Branch | Role | Variant | Outcome | Confidence | Summary |
|---|---|---|---|---|---|
| A | worker | none | partial | medium | ... |

## Evidence

- `<reference>` — <short note>

## Verification

- `<method/reference>` — passed | failed | partial | not_run — <short note>

## A/B comparison

Only include when A/B is enabled.

- Style: report | self_improving
- Variants: A vs B [...]
- Winner: A | B | tie | inconclusive | none
- Reason: <short reason>
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

## Decisions or follow-up

- Should update workflow/prompt/default? yes/no/needs approval — <short note>
- Follow-up: <one action>
