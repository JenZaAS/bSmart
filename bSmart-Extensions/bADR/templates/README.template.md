# Architecture Decision Records

This directory contains the architectural decisions that shape this project.

## When to write an ADR

Only when all three are true:

1. Hard to reverse: changing your mind later is costly.
2. Surprising without context: a future reader will wonder why.
3. A real trade-off: there were genuine alternatives.

Most work writes no ADR. Use [`template-short.md`](template-short.md) (1-3
sentences) by default and [`template.md`](template.md) when the alternatives
really matter.

## How agents use this index

The architect searches the records list below with keywords from the job and
reads only the matching ADRs. The critic does the same, independently. Keep
the keywords current so the search finds the right records. Rules:
bSmart_Protocols/design-context.md, section 2.

## How to add a record

1. Copy a template to the next sequential number, with a short kebab-case
   title, for example `0003-cache-ownership.md`.
2. Add one line to the records list in the same step.
3. Once accepted, do not rewrite its decision. Mark it `Superseded` and write
   a new ADR when the decision changes.

## Status values

`Proposed` · `Accepted` · `Rejected` · `Deprecated` · `Superseded`

## Records

One line each: link, status, keywords, one-sentence decision.

<!-- Example line (replace, do not keep):
- [ADR-0001](0001-cache-ownership.md) - Accepted - cache, ui, storage - Only the storage layer writes the cache.
-->

No ADRs recorded yet.
