# bSelective MATLAB

When interrogating MATLAB `.m` files, extract only as much context as the task needs.

Ask: for this task, what is the smallest reliable context from this file?

Prefer targeted context: header/help, constants, properties, functions/methods, getters/setters, line context, references, or lists of these.

Use:

```text
bselective list FILE [KIND|all] [TARGET]
bselective get FILE KIND [TARGET]
```

Examples:

```text
bselective list MyClass.m all
bselective get MyClass.m header
bselective get MyClass.m property Name
bselective get MyClass.m function doThing
bselective get MyClass.m line 127:5
bselective get MyClass.m all
```

`list all` lists extractable parts. `get all` reads the whole file.
Whole-file reads are allowed when they are the smallest reliable context.

Source note: bSelective is inspired by Erling's bSmart selective-context design and by RLM context-as-variable ideas. This prompt implements only the narrow MATLAB selective-retrieval rule; it does not borrow the Prime Agent application/harness layer.
