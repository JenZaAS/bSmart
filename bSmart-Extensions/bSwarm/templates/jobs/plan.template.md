# Job plan — `<YYYY-MM-DD>-<slug>`

## Goal

`<one line>`

## Strategic note

`<2-3 lines: bigger plan, what to keep open or avoid; or one-off>`

## Change risk

- Door / blast radius: `two-way` | `one-way` / `small` | `medium` | `large` — `<one-sentence why>`

## Standards rules

- `<rules copied from CODING_STANDARDS.md or style files, or none>`

## Test plan

- Interfaces: `<public functions, methods, or entry points>`
- Cover: `<behaviours, regressions, risky edges>`
- Existing tests: `<tests that already cover the rest, or none>`
- Budget: `3-6 new tests` | `<more: one-line reason>`

## Workflow

- Keyword: `cascade` | `cascade critic` | `cascade critic audit`
- bSelective: on by default; explicit ordinary opt-out: `<yes/no>`

## Required reading

- Bundle: `none` | `<paths from knowledge/task-context-routing.md or project.md>`

## Tasks

1. `<bounded task>`
2. `<bounded task>`

## Audit points

- Design audit: after the first architect plan when `cascade critic audit` is selected.
- Code audit: after the architect task list is empty unless a task sets `audit_after_task`.
- One-way change at medium or large blast radius: design and code audit even without `cascade critic audit` (bswarm-protocol.md, section 2).

## Limits and exclusions

- Max tasks: `<number>`
- Out of scope: `<items>`
- Do not copy source trees, transcripts, or diffs into this job folder.
