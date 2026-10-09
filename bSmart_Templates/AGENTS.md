Run `python3 bSmart-System/bStart.py` exactly once at the beginning of every new session, including after `/new`, before replying or taking any action. If `python3` is missing or fails, use `python bSmart-System/bStart.py` (or `py -3 bSmart-System/bStart.py` on Windows). If the session context already contains a `bSmart — Startup` block from this run or from a bSmart client plugin hook, do not run it again. In the first reply, preserve the bStart startup lines and command-help lines; do not replace them with a custom greeting or reduced summary. Follow the startup result and its loaded context.

Hierarchy:
- `bSmart-System/bSmart.md`: shared system rules and bStart contract.
- `bSmart/bSmart_Agent.md`: stable instance identity and access facts.
- selected role file: current role/project/workstream state.
- project files: project-scoped instructions and facts.

Do not duplicate system/project rules here. Do not delete or rewrite this hook for task-specific instructions.
