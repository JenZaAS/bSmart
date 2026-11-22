# bADR

Reusable Architecture Decision Records for bSmart projects.

## Purpose

bADR gives projects a standard ADR folder, a searchable index, and two templates (short and full) so architectural decisions can be recorded without reinventing the format. How agents read ADRs (keyword search by the architect, independent check by the critic, nothing for the coder but copied rules) is in `bSmart_Protocols/design-context.md`, section 2.

## When to write an ADR

Only when all three gates are true:

1. Hard to reverse: changing your mind later is costly.
2. Surprising without context: a future reader will wonder why.
3. A real trade-off: there were genuine alternatives.

Do not write one for routine implementation choices. Most work writes no ADR.

## Project installation

From the bSmart workspace root, run:

```text
python ./bSmart-System/bSmart-Extensions/bADR/scripts/install-badr.py ./projects/<project-name>
```

The installer is create-only by default. It creates:

```text
docs/adr/README.md          # the index agents search
docs/adr/template.md        # full template
docs/adr/template-short.md  # short template, 1-3 sentences
```

It does not overwrite existing files. Use `--force` only when deliberately replacing bADR-managed files. A project that keeps ADRs elsewhere passes `--adr-path <folder>` and sets the same `adr_path` in `project.md`.

## ADR workflow

1. Check the three gates. If one fails, record the choice in `decisions.md` or the plan instead.
2. Copy `template-short.md` (default) or `template.md` (weighty decisions) to the next sequential number.
3. Add the record to the index in the same step: link, status, keywords, one-sentence decision.
4. Link the ADR from the implementation change or workstream document.
5. Mark changed decisions `Superseded`; do not rewrite historical decisions.

## Status values

`Proposed` · `Accepted` · `Rejected` · `Deprecated` · `Superseded`

## Storage boundary

ADR files belong to the project because they describe project architecture. The bADR feature source and templates belong in `bSmart-System`; generated project ADRs belong in the project itself.

Do not put secrets, credentials, or confidential values into ADRs unless the project has an explicitly approved secure documentation policy.
