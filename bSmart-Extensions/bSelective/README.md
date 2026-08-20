# bSelective MATLAB

bSelective MATLAB is a tiny prompt plus two commands for selective `.m` context retrieval.

Core rule: **When interrogating MATLAB `.m` files, extract only as much context as the task needs.** Use the full file only when that is the smallest reliable context.

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
