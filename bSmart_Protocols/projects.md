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
