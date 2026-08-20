# bWorkflow

bWorkflow is the bSmart reusable workflow/procedure memory extension.

It answers: **How do we reliably perform this task?**

## Storage model

- Packaged runtime source: `/workspace/bSmart-System/bSmart-Extensions/bWorkflow`
- Installed runtime mirror: `/workspace/bSmart-Extensions/bWorkflow`
- Instance workflow content: `/workspace/bSmart/Workflows`

The runtime parses Markdown directly. Markdown is the v1 source of truth; no generated JSON/XML/cache index is authoritative.

## Command examples

```bash
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows list
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows list mathworks
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows list mathworks.segy
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows search segy
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows get mathworks.segy.load
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows section mathworks.segy.load Steps
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows log-run mathworks.segy.load success --date 2026-08-20
python3 bworkflow_handler.py --root /workspace/bSmart/Workflows reset-counters mathworks.segy.load --reason "Updated workflow" --date 2026-08-20 --git-commit unknown
```

## Status

Initial v1 prototype implemented:

- hierarchical listing: domains, topics, workflow entries
- lightweight list filtering
- metadata search
- exact workflow retrieval
- exact section retrieval
- compact run counter updates
- counter reset with lifecycle history entry
