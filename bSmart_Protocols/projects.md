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
```

```yaml
project_md_required_fields:
  - project_name
  - status
  - owner
  - objective
  - agent_focus
```
