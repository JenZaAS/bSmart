# bCoder rules

Use this to implement a change, alone or from a plan.

## Before coding

1. Read the task and the plan, if there is one. Change only what they allow.
2. Search the knowledge for anything relevant to your task, starting from any
   pointers you were given (`relevant_knowledge` in a plan, or the project's
   `knowledge/task-context-routing.md`).
3. Do not repeat broad discovery the plan already did. If the plan is not
   enough, make targeted reads or searches and report them.
4. Required reading (hard rule): when the project declares a required
   reading bundle (`bSmart_Protocols/projects.md`, `required_reading_bundle`),
   you must follow it. If none is declared, follow `not_declared` in that rule.
   - With a plan: follow its `required_reading` block (bArchitect, "Required
     reading acknowledgement") and run its `coder_checks`. If the plan has no
     such block, stop and report it; do not make up the architecture.
   - Without a plan: read the bundle yourself before coding and put the same
     block in your report.

## Coding

5. Edit only the files you are allowed to edit.
6. Run the relevant tests or checks, and record what ran.

## Before handing in

7. Update the knowledge before handing in your work: apply `knowledge_upkeep`
   in `bSmart.md` to the files, functions, and features you touched.
8. Check: no conflict markers, only allowed files changed, diff stat ready,
   test or runtime status recorded if available.
9. Report briefly: summary, changed files, diff stat, knowledge changes (or
   "no knowledge changes needed"), tests, extra reads, caveats, and, when a
   bundle is declared, the `coder_checks` results.
