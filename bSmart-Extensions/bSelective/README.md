# bSelective MATLAB

bSelective MATLAB is a tiny prompt plus two commands for selective `.m` context retrieval.

Core rule: **When interrogating MATLAB `.m` files, extract only as much context as the task needs.** Use the full file only when that is the smallest reliable context.

## Source ideas and influences

- Operator idea/source: Erling's bSmart coding-feature design split: `bWorkflow` for reusable procedure memory, `bSelective` for selective context acquisition, and `bGauntlet`/future `bSwarm` for evidence-driven multi-agent review/orchestration.
- External inspiration: Recursive Language Models (RLM), especially treating context as a variable and inspecting external data programmatically instead of loading everything into the prompt.
- Design boundary: bSelective borrows the RLM selective/progressive context idea only. It does not borrow the Prime Agent application/harness layer. The v1 is deliberately narrower: deterministic MATLAB `.m` retrieval with explicit whole-file fallback.
- Project source note: see `/projects/bCoding-features/workdocs/bSelective-matlab-v1-progress-2026-08-21.md`.

## Commands

```text
python3 bselective_handler.py list FILE [KIND|all] [TARGET]
python3 bselective_handler.py get FILE KIND [TARGET]
```

Examples:

```text
python3 bselective_handler.py list MyClass.m all
python3 bselective_handler.py list MyClass.m functions
python3 bselective_handler.py list MyClass.m refs TraceHeaders
python3 bselective_handler.py get MyClass.m header
python3 bselective_handler.py get MyClass.m constant DefaultFormat
python3 bselective_handler.py get MyClass.m property TraceHeaders
python3 bselective_handler.py get MyClass.m function loadHeaders
python3 bselective_handler.py get MyClass.m line 127:5
python3 bselective_handler.py get MyClass.m all
```

`list all` lists extractable parts. `get all` returns the full file.

## Session use

bSelective is off by default. To turn it on for a session, paste/read `bselective-matlab.md` once; the prompt then stays in context for that session.


## Compact agent output

Use compact text list output for agent context discovery:

```bash
bselective_handler.py list DTM_ModelTemplates.m outline --format text
bselective_handler.py list DTM_ModelTemplates.m functions --format text
bselective_handler.py list DTM_ModelTemplates.m all --compact
```

The CLI `list` command defaults to compact text because tool output becomes later model input. Avoid pretty JSON for normal agent use. JSON remains available for scripts:

```bash
bselective_handler.py list DTM_ModelTemplates.m all --format json --compact
```

Default compact output avoids repeated `file`/`kind` keys, full source snippets, duplicate constants under both constants and properties, and expanded getters/setters unless explicitly requested.


## Nested control-flow hardening

`get FILE function NAME` tracks MATLAB block depth for nested `if`, `for`, `parfor`, `while`, `switch`, `try`, `spmd`, and `arguments` blocks so method/function slices do not stop at the first nested `end`. This is still a lightweight deterministic parser; use `get FILE all` as the explicit fallback when syntax is unusual or the slice looks incomplete.
