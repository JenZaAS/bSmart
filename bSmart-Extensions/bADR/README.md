# bADR

Reusable Architecture Decision Records for bSmart projects.

## Purpose

bADR gives projects a standard `docs/adr/` structure, index, template, and creation workflow so architectural decisions can be recorded without reinventing the format.

Use an ADR for decisions with durable consequences for repository structure, module boundaries, interfaces, data flow, runtime/startup behavior, compatibility, deployment, or maintainability. Do not use one for routine implementation choices.

## Project installation

From the bSmart workspace root, run:

```text
python ./bSmart-System/bSmart-Extensions/bADR/scripts/install-badr.py ./projects/<project-name>
```

The installer is create-only by default. It creates:

```text
docs/adr/README.md
docs/adr/template.md
```

It does not overwrite existing files. Use `--force` only when deliberately replacing bADR-managed files.

## ADR workflow

1. Read `docs/adr/README.md` and related ADRs.
2. Copy `template.md` to the next sequential number.
3. Record context, decision, alternatives, consequences, scope, and related decisions.
4. Link the ADR from the implementation change or workstream document.
5. Mark changed decisions `Superseded`; do not rewrite historical decisions.

## Status values

`Proposed` · `Accepted` · `Rejected` · `Deprecated` · `Superseded`

## Storage boundary

ADR files belong to the project because they describe project architecture. The bADR feature source and templates belong in `bSmart-System`; generated project ADRs belong in the project itself.

Do not put secrets, credentials, or confidential values into ADRs unless the project has an explicitly approved secure documentation policy.
