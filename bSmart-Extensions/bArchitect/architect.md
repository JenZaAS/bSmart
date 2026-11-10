# bArchitect rules

Use this to plan a change for a coder, and to close it.

## Plan

1. Discover context and design the change. Do not edit implementation files.
2. Read only enough context for a concrete plan. Search the knowledge for the
   area first (the project's `knowledge/task-context-routing.md` when it
   exists).
3. Write a short plan (`architect-plan.md` when files are used). It is a
   context budget for the coder, not a design essay. Defaults:

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

4. Give a one-line reason for each relevant region. Keep `must_implement`,
   `defer`, and `do_not_implement` sharply separated.
5. Point the coder to the relevant knowledge entries in `relevant_knowledge`.

Plan format:

```yaml
architect_plan:
  target_file_path: <file the coder may change>
  budget: <the defaults above, or the override>
  relevant_regions:
    - function_or_section: <name>
      lines: <start-end or start-?>
      why: <one-line reason only>
  relevant_knowledge:
    - <knowledge path: one-line reason, or none found>
  must_implement:
    - <required change, max 6 bullets>
  defer:
    - <explicitly postponed item or none>
  do_not_implement:
    - <forbidden change or none>
  risks:
    - <top risks>
  verification_checks:
    - <checks the coder runs>
```

## Between tasks

For work in several tasks, finish and verify one task, then review and update
the remaining plan before the next.

## Close: final knowledge check

After the review accepts the work and before reporting back, do the final
knowledge check across the whole change: search the knowledge once more for
everything the change touched, fix what is still stale or missing, keep only
concise durable lessons, and record the result (what changed, or "no knowledge
changes needed").
