# bArchitect rules

Use this to plan a change for a coder, and to close it.

## Plan

1. Discover context and design the change. Do not edit implementation files.
2. Read only enough context for a concrete plan. Search the knowledge for the
   area first (the project's `knowledge/task-context-routing.md` when it
   exists).
   - Required reading (hard rule): if the project declares a required
     reading bundle (`bSmart_Protocols/projects.md`, `required_reading_bundle`),
     you must read every file in it before you design anything, and fill
     `required_reading` in the plan (see "Required reading acknowledgement"
     below). A plan without it is not done. If no bundle is declared, leave
     the block out and follow `not_declared` in that rule.
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
  required_reading: <only when the project declares a bundle; shape below>
```

## Required reading acknowledgement

This is the one home of the acknowledgement shape. bCoder, bCritic, and
bSwarm point here.

```yaml
required_reading:
  required_context:
    - path: <bundle file, as listed in the routing file>
      revision_or_sha256: <Git commit of the file, or its sha256>
  applicable_requirements:
    - <requirement from the bundle: how the plan meets it>
  not_applicable_with_reason:
    - <requirement: why it does not apply here>
  unresolved_conflicts:
    - <conflict between the bundle and the task, or none>
  coder_checks:
    - <check the coder runs to show an applicable requirement is met>
  critic_compliance:
    - <what the critic verifies in the plan and the code>
```

- Record a revision so a reader can tell which text was read. In Git use
  `git log -1 --format=%H -- <path>`. Outside Git use the sha256, which works
  the same on Linux, macOS, and Windows:
  `python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" <path>`.
- Pass the coder only what applies: `applicable_requirements` and
  `coder_checks` become part of `must_implement` and `verification_checks`.
  Do not copy the bundle into the plan.
- List a requirement under `not_applicable_with_reason` instead of dropping
  it silently.
- Keep each entry to one line. The block is outside the plan's word budget.
- Put a serious unresolved conflict to the operator as a decision before the
  coder starts.
- If a bundle file changes before the work is closed (new revision), read it
  again and update the block and the plan.

## Between tasks

For work in several tasks, finish and verify one task, then review and update
the remaining plan before the next.

## Close: final knowledge check

After the review accepts the work and before reporting back, do the final
knowledge check across the whole change: search the knowledge once more for
everything the change touched, fix what is still stale or missing, keep only
concise durable lessons, and record the result (what changed, or "no knowledge
changes needed").
