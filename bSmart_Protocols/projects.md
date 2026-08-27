# bSmart Protocol: projects

```yaml
protocol:
  id: projects
  title: Projects
  purpose: Create, select, and manage local bSmart projects.
```

```yaml
paths:
  project_root_selection:
    - BSMART_PROJECT_ROOT when set to a readable/writable directory
    - /projects when readable/writable
    - ./projects when readable/writable from the current bSmart/workspace folder
    - /workspace/bSmart/Projects as legacy fallback
  state_file: /workspace/bSmart/bSmart_State.md
  state_file_local: ./bSmart/bSmart_State.md
```

```yaml
state_management:
  protocol: /workspace/bSmart-System/bSmart_Protocols/state.md
  rule: Project creation/listing may use state, but active/current project ownership and Free Mode rules are defined by the State protocol.
```

```yaml
path_resolution:
  rule:
    - resolve ./projects relative to the folder containing the startup hook, e.g. AGENTS.md
    - if /workspace/bSmart paths do not exist, use ./bSmart equivalents
    - do not fail project listing just because /workspace/bSmart/Projects is absent
```

```yaml
list_projects:
  procedure:
    - select project root using project_root_selection
    - list immediate child directories in the selected root
    - treat a child as a bSmart project when it contains project.md or README.md
    - also show plain child directories separately when they may be source/project folders without bSmart metadata
    - include the selected project root in the response so the operator can spot path mistakes
  output_style:
    - concise bullets
    - group archived folders such as _archive separately when present
```

```yaml
project_structure:
  required:
    - README.md
    - project.md
    - data/README.md
    - sandbox/README.md
    - knowledge/README.md
    - knowledge/general/
    - knowledge/code/
    - decisions.md
    - workdocs/README.md
  meaning:
    data: Raw/supporting project material such as inputs, exports, screenshots, source artifacts, and temporary research notes.
    knowledge: Curated reusable knowledge specific to this project. `knowledge/general/` holds file-independent project/domain knowledge; `knowledge/code/` holds source-specific or codebase-navigation knowledge. Use the global Library only when the material is broadly reusable across projects or the bSmart instance. `knowledge/` is preferred over `library/` inside projects to avoid confusion with software libraries.
    decisions: A single project decision file for choices, approvals, rejected options, and migration/design decisions specific to this project.
    workdocs: Project-local working documents for larger or multi-session work within this project.
    sandbox: Disposable or derived execution/build/test workspace notes; not the source of truth.
  onboarding_rule: Create these defaults for new projects to reduce friction. If a folder stays empty, keep its README as guidance rather than asking the operator to decide up front.
  existing_project_rule: Existing projects do not need a forced migration. If an existing project lacks `knowledge/`, `knowledge/general/`, `knowledge/code/`, `decisions.md`, or `workdocs/` and the operator asks to add one, create the missing standard file/folder from the corresponding template or the knowledge protocol.
```

```yaml
templates:
  project: /workspace/bSmart-System/bSmart_Templates/project.template.md
  project_knowledge_readme: /workspace/bSmart-System/bSmart_Templates/project-knowledge.README.template.md
  project_decisions: /workspace/bSmart-System/bSmart_Templates/project-decisions.template.md
  project_workdocs_readme: /workspace/bSmart-System/bSmart_Templates/project-workdocs.README.template.md
```

```yaml
project_md_required_fields:
  - project_name
  - status
  - owner
  - objective
  - agent_focus
```
