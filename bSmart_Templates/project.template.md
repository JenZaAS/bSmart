# Project: <project-name>

```yaml
project:
  name: <project-name>
  short_name: <short-name>
  status: Planning
  owner: <owner>
  objective: <one-sentence-objective>
  agent_focus: <what-the-agent-should-focus-on>
```

## Project structure

- `data/` — raw/supporting project material.
- `knowledge/` — curated reusable knowledge specific to this project.
  - `knowledge/README.md` — knowledge scope and storage guidance.
  - `knowledge/task-context-routing.md` — task-to-knowledge routing; load only the relevant bundle.
  - `knowledge/general/` — file-independent project/domain knowledge.
  - `knowledge/code/` — concise source-specific or codebase-navigation knowledge.
- `decisions.md` — project-specific decisions and approvals.
- `workdocs/` — project-local working documents, investigations, and handoffs; not the final home for concise knowledge items.
- `sandbox/` — disposable/derived execution or test area; not the source of truth.

## Context routing

Before coding, debugging, testing, designing, or documenting this project, consult `knowledge/task-context-routing.md`. Load only the task-specific knowledge bundle it identifies; do not load the complete knowledge tree by default.

## Current focus

## Tasks

## Notes
