# bSwarm

bSwarm is the bSmart chat-driven multi-agent orchestration protocol.

It answers: **How do we coordinate multiple AI perspectives to produce a better, evidenced result than one linear agent pass?**

## Status

V1 is a chat-driven protocol, not a command handler. Use it by drafting a concise run specification, optionally editing grouped settings, launching Hermes subagents where useful, and writing a Markdown run record.

## Modes

- `unsupervised` — coordinator launches workers directly.
- `supervised` — coordinator launches supervisors/evaluators, each supervising worker attempts.

`gauntlet` is retained only as the source/metaphor for pressure-testing.

## A/B styles

- `report` — compare variants and report findings; no automatic change.
- `self_improving` — bounded iterative refinement of a tested artifact; requires explicit limits.

## bSelective combinations

- `all_off` — ordinary context gathering.
- `all_on` — all relevant subagents use bSelective.
- `mixed_ab` — some branches use bSelective and some do not, to evaluate its value.

## Use

1. Read `bswarm-protocol.md`.
2. Create a short run spec from `templates/run-spec.yaml`.
3. Show the concise summary to Erling before launch.
4. Run the selected bSwarm through chat/delegation.
5. Save a run record using `templates/run-record.md`.

## Source ideas and influences

- Operator idea/source: Erling's bSmart coding-feature sequence: `bWorkflow`, `bSelective`, then `bSwarm`.
- External inspiration: RLM / Prime Intellect Prime Agent concepts such as context-as-variable, programmatic inspection, specialist sub-agents, and evidence-oriented harnesses.
- Boundary: bSwarm borrows coordination and context-management ideas; it is not a Prime Agent clone and does not imply hidden continual self-improvement.
