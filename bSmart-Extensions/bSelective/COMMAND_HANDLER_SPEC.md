# bSelective MATLAB command handler spec

## Prompt file

The agent-facing prompt is `bselective-matlab.md`. Keep it short enough to paste into a session.

bSelective is off by default. Turning it on for a session means reading/pasting that prompt once.

## CLI

```text
bselective_handler.py list FILE [KIND|all] [TARGET]
bselective_handler.py get FILE KIND [TARGET]
```

`KIND` values:

- `all`
- `header` / `help`
- `outline`
- `constants` / `constant`
- `properties` / `property`
- `functions` / `function`
- `methods` / `method`
- `getter` / `setter`
- `line` / `context`
- `refs` / `references`

Rules:

- `list all` returns available extractable parts, not full source.
- `get all` returns the full file.
- `get line 127:5` returns line 127 plus 5 lines around it.
- Prefer `list` before `get` when the exact target name is uncertain.
- The tool is read-only.
