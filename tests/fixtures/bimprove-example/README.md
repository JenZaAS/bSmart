# bImprove unit-test fixture

A made-up two-phase case used only by `tests/test_bimprove.py` with a fake agent CLI. It is not a shipped case: real cases, answer keys and score history live in the operator's own project (see `bSmart-Extensions/bImprove/improve.md`, "Add a new case").

# Test kit: knowledge-ab

A short, knowledge-only test of `bSmart_Protocols/knowledge.md`. No coding.
The project (`harbor-app`), the client and the "Tidewell API" are made up.

- `instance/`: the clean test instance every run starts from (empty knowledge,
  four source files in `sources/`, a short `AGENTS.md`).
- `phaseA/`: storing. The worker gets a small research task and is not told
  to save anything. The answer key checks that it saved the key facts on its
  own, in the right place, without noise or leaks.
- `phaseB/`: retrieving. `overlay/` adds the right notes. The worker is asked
  a question about the topic. The answer key checks that it looks in
  knowledge first and reads little.
- `kit.json`: phases, the target MD, the system files copied into each run,
  and size estimates for the approval card.

The worker never sees the answer keys: `bimprove.py` copies only `instance/`
(and the overlay) into each fresh run folder.

Phase B's read limit is 8: the shortest correct path through the two-level
indexes is 7 files (project index, topic index, note; Library index,
`tools/index.md`, topic index, note).
