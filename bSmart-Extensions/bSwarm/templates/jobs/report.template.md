# Job report — `<YYYY-MM-DD>-<slug>`

## Job

- Goal: `<one line>`
- Date: `<YYYY-MM-DD>`
- Slug: `<slug>`
- Workflow keyword: `cascade` | `cascade critic` | `cascade critic audit`
- Outcome: `reached` | `partial` | `blocked` | `inconclusive`
- Commit: `<commit or none>`

## Scope

- In: `<paths or references>`
- Out: `<explicit exclusions>`

## Change risk

- Door / blast radius: `two-way` | `one-way` / `small` | `medium` | `large` — `<one-sentence why>`
- Extra review: `none` | `stricter critic` | `stricter critic + audit <model id or not launched: reason>`
- Outcome: `passed` | `<open decision or HOLD id>`
- Raised or confirmed by: `<role, one line>`

## Architect tasks

- `<task>` — `<status>`

## Operator decisions

- `<decision or none>`

## Automatic

- Count: `<number>`
- `<one-line summary>`

## Open decisions

- `<decision needed or none>`

## Optional findings

- Count: `<number>`

## External audits

### Auditor: `<actual model id or not launched>` — design

- Model ID: `<actual model id or not launched>`
- Finding: `<finding>` — Class: `automatic` | `decision` | `optional` — Status: `<status>`
- Stop reason: `<reason or none>`

### Auditor: `<actual model id or not launched>` — code

- Model ID: `<actual model id or not launched>`
- Finding: `<finding>` — Class: `automatic` | `decision` | `optional` — Status: `<status>`
- Stop reason: `<reason or none>`

Optional findings: count only — `<number>`.

## Knowledge changes

- `<path: one-line change, or no knowledge changes needed>`
- Glossary: `<term: change, candidates listed, no glossary changes needed, or no glossary>`
- ADRs consulted: `<ADR ids, none matched, or no ADRs>`

## Review axes

- Spec: `ok` | `<issue ids>`
- Standards: `ok` | `<issue ids>` | `none (no coding standards)`
- Standards candidates: `<rule or check: evidence, review ids>` | `none` (report-only)

## Tests

- New tests: `<number>` against budget `<3-6 or justified number>`; regression tests added: `<ids or none>`
- Test issues flagged: `<issue ids or none>`
- Prune or architecture proposals: `<report path or none>` (proposals only; nothing applied)

## Required reading

Only when the project declares a bundle; otherwise `not declared`.

- Bundle: `<paths or not declared>`
- Acknowledgement: `<architect-plan.md link or missing>`
- Coder checks: `<passed / failed, one line>`
- Critic compliance: `<met / HOLD, one line>`

## Evidence

- `<commit, ADR, workstream, test, or other link>` — `<short note>`

## Trust / not verified

- `<what is supported by evidence>`
- `<what was not verified>`

## Next

- `<one next action>`
