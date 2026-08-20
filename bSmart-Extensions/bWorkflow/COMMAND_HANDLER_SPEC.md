# bWorkflow command handler spec

## Principles

- Use Markdown files directly as the authoritative data source.
- Keep retrieval progressive and token-conscious.
- Avoid full-tree reads unless explicitly requested or needed for debugging.
- Keep learned instance workflows in `/workspace/bSmart/Workflows`, not in bSmart-System.

## Python API

```python
list_workflows(scope=None, filter=None, root=None)
search_workflows(query=None, scope=None, root=None, keyword=None, title=None, associated_file=None, workflow_id=None)
get_workflow(id, root=None)
get_workflow_section(id, section, root=None)
log_workflow_run(id, result, root=None, date=None)
reset_workflow_counters(id, reason, root=None, date=None, git_commit=None)
```

## CLI

```text
bworkflow_handler.py [--root PATH] list [scope] [--filter TEXT]
bworkflow_handler.py [--root PATH] search [query] [--scope SCOPE] [--keyword TEXT] [--title TEXT] [--associated-file PATH] [--workflow-id ID]
bworkflow_handler.py [--root PATH] get ID
bworkflow_handler.py [--root PATH] section ID SECTION
bworkflow_handler.py [--root PATH] log-run ID success|failure [--date DATE]
bworkflow_handler.py [--root PATH] reset-counters ID --reason TEXT [--date DATE] [--git-commit REF]
```

## ID interpretation

- `domain` lists top-level domain catalogue entries.
- `domain.topic` identifies a topic file.
- `domain.topic.action` identifies a workflow entry.

## Markdown expectations

Top-level and domain catalogues use list blocks:

```md
- ID: mathworks
  Path: mathworks/
  Title: MathWorks workflows
  Summary: MATLAB and MathWorks procedures.
  Keywords: matlab, mathworks
```

Workflow entries start with:

```md
## WORKFLOW mathworks.segy.load
```

Metadata lines are `Key: value`; `Associated files` is an indented list.
