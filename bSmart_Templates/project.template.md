# Project: <project-name>

```yaml
project:
  name: <project-name>
  short_name: <short-name>
  status: Planning
  owner: <owner>
  objective: <one-sentence-objective>
  agent_focus: <what-the-agent-should-focus-on>
  # Optional: files that must be read before architecture or code work.
  # Format and rule: bSmart_Templates/required-reading-default.md.
  required_reading_bundle: []
  # Optional design context (bSmart_Protocols/design-context.md):
  # adr_path: docs/adr/          # ADR folder; default docs/adr/
  # glossary_path: glossary/     # project (parent) glossary; default glossary/
  # module_repos: []             # module code repos outside this folder; their glossary/ folders are checked too
  # coding_standards: []         # existing style files to review against, besides CODING_STANDARDS.md
  # one_way_examples: []         # changes that are always one-way doors
  # Optional test tiers (bSmart_Protocols/test-tiers.md):
  # test_tiers_manifest: test-tiers.txt   # tag manifest in the code repo
  # test_tiers_trigger: routine           # what starts the special tier: routine (default) or ci
```

## Project structure

- `data/` — raw/supporting project material.
- `knowledge/` — curated reusable knowledge specific to this project.
  - `knowledge/README.md` — knowledge scope and storage guidance.
  - `knowledge/task-context-routing.md` — task-to-knowledge routing; load only the relevant bundle.
  - `knowledge/index.md` — topics only, one line each; each topic folder has its own `index.md`.
  - `knowledge/code/` — code knowledge; language-agnostic notes here, language notes in `code/<language>/`.
  - `knowledge/tools/` — apps, services, and external references, one subfolder each.
  - `knowledge/general/` — last resort when no better topic fits.
  - Rules: `bSmart_Protocols/knowledge.md`.
- `decisions.md` — project-specific decisions and approvals.
- `glossary/` — optional; the project's shared language, created with the first confirmed term. Not inside `knowledge/`.
- `docs/adr/` — optional; Architecture Decision Records (bADR), or the folder in `adr_path`.
- `workdocs/` — project-local working documents, investigations, and handoffs; not the final home for concise knowledge items.
- `sandbox/` — disposable/derived execution or test area; not the source of truth.

## Context routing

Before coding, debugging, testing, designing, or documenting this project, consult `knowledge/task-context-routing.md`. Load only the task-specific knowledge bundle it identifies; do not load the complete knowledge tree by default.

## Current focus

## Tasks

## Notes
