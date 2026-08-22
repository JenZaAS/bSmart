# bSwarm

bSwarm is the bSmart chat-driven multi-agent orchestration protocol.

It answers: **How do we coordinate multiple AI perspectives to produce a better, evidenced result than one linear agent pass?**

## Status

V1 is a chat-driven protocol, not a command handler. Use it by drafting a concise run specification, optionally editing grouped settings, launching Hermes subagents where useful, and writing a Markdown run record.

## Modes

Compact user-facing workflow keywords:

- `ordinary` — direct ordinary coder; no bSelective context tooling.
- `bSelective` — direct bSelective-enabled coder.
- `architect` — ordinary architect → ordinary coder, using one compact handoff.
- `bSelective architect` — bSelective architect → bSelective coder, using one compact handoff.
- `cascade` — ordinary architect-led stepwise workflow.
- `bSelective cascade` — bSelective architect-led stepwise workflow with bSelective-enabled coders.

Mixed architect/coder context modes are internal experimental overrides, not normal user-facing modes.

Top-level modes:

- `unsupervised` — coordinator launches workers or branch stages directly.
- `supervised` — coordinator/supervisors validate outputs and retry only for diagnosed gaps.

Explicit subagent stage modes:

- `supervisor` — creates/validates run folders, duplicates allowed files, dispatches stages, verifies child self-reports, and records statistics. It does not directly edit target implementation files unless explicitly asked.
- `architect` — discovers context and writes a concise implementation plan. It must not edit implementation files. Its handoff is a default context-budget artifact: target 350-500 words, hard max 700 words, max 6 relevant regions, max 6 `must_implement` bullets, no tool transcripts, no long source quotes, and no full bSelective output.
- `coder` — implements in the allowed branch duplicate file and verifies the result.

`gauntlet` is retained only as the source/metaphor for pressure-testing.

## A/B styles

- `report` — compare variants and report findings; no automatic change.
- `self_improving` — bounded iterative refinement of a tested artifact; requires explicit limits.

## bSelective combinations

- `all_off` — ordinary context gathering.
- `all_on` — all relevant subagents use bSelective.
- `mixed_ab` — some branches use bSelective and some do not, to evaluate its value.

## Branch patterns

- `direct_worker` — one ordinary coder/worker plans and edits directly in its duplicate file.
- `architect_coder` — architect discovers context and writes `architect-plan.md`; coder implements from that plan.
- `architect_taskflow` — architect decomposes, dispatches one bounded coder task, evaluates, re-plans, then continues within cascade limits.

Example A/B/C run shape:

```yaml
branches:
  ordinary:
    pattern: direct_worker
    context_mode: ordinary
    stages:
      - coder
  bselective:
    pattern: direct_worker
    context_mode: bselective
    stages:
      - coder
  architect:
    pattern: architect_coder
    architect_context_mode: ordinary
    coder_context_mode: ordinary
    stages:
      - architect
      - coder
  bselective_architect:
    pattern: architect_coder
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages:
      - architect
      - coder
  cascade:
    pattern: architect_taskflow
    architect_context_mode: ordinary
    coder_context_mode: ordinary
    stages:
      - architect
      - coder
      - architect_evaluation
  bselective_cascade:
    pattern: architect_taskflow
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages:
      - architect
      - coder
      - architect_evaluation
```

## Use

1. Read `bswarm-protocol.md`.
2. Create a short run spec from `templates/run-spec.yaml`.
3. Show the concise summary to Erling before launch.
4. For editable evaluation runs, duplicate the original target into per-branch files under the run folder.
5. Keep prior generated-run archive paths out of worker prompts unless explicitly comparing against old generated code.
6. Run the selected bSwarm through chat/delegation.
7. Save architect plans as `*/architect-plan.md` where applicable.
8. Save a run record using `templates/run-record.md`, including per-stage and branch-total statistics.

## Source ideas and influences

- Operator idea/source: Erling's bSmart coding-feature sequence: `bWorkflow`, `bSelective`, then `bSwarm`.
- External inspiration: RLM / Prime Intellect Prime Agent concepts such as context-as-variable, programmatic inspection, specialist sub-agents, and evidence-oriented harnesses.
- Boundary: bSwarm borrows coordination and context-management ideas; it is not a Prime Agent clone and does not imply hidden continual self-improvement.
