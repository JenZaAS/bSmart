# bSmart Protocol: projects

```yaml
protocol:
  id: projects
  title: Projects
  purpose: Create, select, and manage local bSmart projects.
```

```yaml
paths:
  projects_root: /workspace/bSmart/Projects
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
