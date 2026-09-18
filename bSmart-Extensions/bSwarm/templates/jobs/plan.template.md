# Job plan — `<YYYY-MM-DD>-<slug>`

## Goal

`<one line>`

## Workflow

- Keyword: `cascade` | `cascade critic` | `cascade critic audit`
- bSelective: on by default; explicit ordinary opt-out: `<yes/no>`

## Tasks

1. `<bounded task>`
2. `<bounded task>`

## Audit points

- Design audit: after the first architect plan when `cascade critic audit` is selected.
- Code audit: after the architect task list is empty unless a task sets `audit_after_task`.

## Limits and exclusions

- Max tasks: `<number>`
- Out of scope: `<items>`
- Do not copy source trees, transcripts, or diffs into this job folder.
