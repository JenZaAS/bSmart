# bCritic rules

Use this to review a plan, code, or any document. Be critical but fair.
Report the issues that matter; do not nit-pick every small thing. Do not edit
what you review.

## What to check

- Check against the goal, the spec, the tests, and the project's decisions
  (`decisions.md`, ADRs). Do not invent product rules; a gap is a `decision`
  issue.
- A plan: material issues in the specification.
- Code: goal coverage, bugs, speed, memory efficiency, security, robustness,
  integration, code reuse, and test coverage.
- Knowledge: check that the relevant knowledge was read and kept in step with
  the code. For a plan, check its `relevant_knowledge` pointers. For code,
  review the code and its knowledge changes together, and flag knowledge that
  is stale or missing as an issue.
- Required reading: when the project declares a required reading bundle
  (`bSmart_Protocols/projects.md`, `required_reading_bundle`), check that the
  plan (or a planless coder's report) has the `required_reading` block from
  bArchitect ("Required reading acknowledgement"), that it covers every
  bundle file, and that its `applicable_requirements`, `coder_checks`, and
  `critic_compliance` were applied. A missing or incomplete block, required
  reading that was not applied, or a serious `unresolved_conflicts` entry is a
  HOLD (below). If no bundle is declared, there is no HOLD; follow `not_declared` in that rule.

## HOLD

HOLD is the one exception to the rule that a review never blocks the work.
Only the required-reading cases above cause it.

- A HOLD is a blocking fail. The work cannot pass at any score, and the
  requester cannot accept it as it is.
- Record it as a `critical` issue: `automatic` when the reading was skipped or
  not applied, `decision` for a serious unresolved conflict. Add `HOLD` to the
  review file header and the summary line.
- It lifts only when the cause is fixed: the reading is done and applied, or
  the operator settles the conflict. The next round checks that.
- If it is still there after the last round, stop and report the work as
  blocked, not accepted.

## Score and rounds

- `score: 1-10`, 10 best, in the review file header and the summary.
- The bar is 8/10: stop at 8 or higher.
- The score and the round limit count only `automatic` and `decision` issues,
  so `optional` issues alone never keep a loop going.
- At most 5 rounds (`max_critique_rounds`). Below 8 after round 5: stop and
  report. The bar never blocks the work by itself; the requester decides.
  The only exception is a HOLD (above).
- Another round needs diagnosed issues, not vague dissatisfaction.

## Issue tags

Each issue gets a severity, a class, and a status. No other values.

| Tag | Values |
|---|---|
| severity | `critical`, `important`, `minor` (how much it matters) |
| class | `automatic`, `decision`, `optional` (who acts) |
| status | `open`, `fixed`, `deferred`, `rejected` |

| Class | Meaning | Who acts |
|---|---|---|
| `automatic` | Wrong or incomplete against the spec, decisions, tests, or an obvious local pattern | The agent fixes it |
| `decision` | Needs a product or design choice | The operator decides, then the work continues |
| `optional` | Nit, hygiene, taste, or speculative extra | Nobody by default |

The critic proposes a class; the requester (in bSwarm, the parent) may
re-sort it. Unsure means `decision`. `optional` issues never block progress
and never cause another round. They may be fixed along the way when the same
code is already being changed for an `automatic` or `decision` issue and the
fix is clearly relevant.

## Review file

Write the full review to a review file and return only the summary.

- Name: `critiques/<role>-r<n>.md`. `<role>` is what was reviewed
  (`architect`, `coder`, or a short document slug); `<n>` is the round (1-5).
  For work in several tasks add the task: `coder-t<task>-r<n>.md`.
- Where: in bSwarm, where its protocol says. Standalone in a project:
  `critiques/` in the project or workstream folder that owns the work (same
  rule as the backlog). Outside a project: a `critiques/` folder next to the
  document.
- Start from `templates/critique.template.md`. The header records role
  reviewed, round, score, HOLD, critic model, date, and the previous round's
  file.
- One heading per issue, tags in this fixed order, details below it:

  ```text
  ### C<id> [<severity>] [<class>] [<status>] <short label>
  ```

- IDs are stable. `C1`, `C2`, ... are numbered per role (and task) across its
  rounds: an issue keeps its ID in r2 through r5, and new issues take the next
  unused number. Never reuse or renumber an ID. Each round file repeats every
  issue still open from the previous round with its current status.
- Review files are part of the development log: keep them, never delete or
  rewrite them. Later changes go into the next round file or the backlog.

## Summary

The summary is the only part that enters the requester's context:

```text
critique: <role> r<n> score <1-10>/10 [HOLD] file <path>
- C1 [critical] [automatic] [open] <short label>: <one-line description>
- C2 [minor] [optional] [open] <short label>: <one-line description>
```

List every issue on one line each, with no details. The fixing role reads
only the IDs it needs from the file, for example by searching for the heading
`### C2 `. The requester or the architect may promote a `minor`/`optional`
issue when their context makes it matter; record the promotion (who, why, new
tags) under that issue in the next round file, or in the backlog entry.

## Deferred-issues backlog

When the review ends, add each issue that is still `optional` and unfixed to
the owning `deferred-issues.md` (start from
`templates/deferred-issues.template.md`). Each entry has a backlog status
(`open`, `done`, `rejected`, `later`) and links back to the review file and
ID. Mark the issue `[deferred]` in the last round file. The operator reviews
the backlog when convenient; a recurring review routine is optional.

Keep one backlog at the level that owns the module. The project sets this in
`project.md` with `deferred_issues: project | workstream` (default
`project`). The old name `bswarm_deferred_issues` still works; if both are
set, `deferred_issues` wins:

- `project`: one `<project>/deferred-issues.md`. Use it when the project is
  the module and its workstreams are features of it.
- `workstream`: one `<project>/workstreams/<workstream>/deferred-issues.md`
  per workstream. Use it when workstreams are separate modules.

If the field is missing, use `project`. Outside a project, keep the backlog
next to the document's `critiques/` folder.

Less common cases are in `critique-notes.md`.
