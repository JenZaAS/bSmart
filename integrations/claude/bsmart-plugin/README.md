# bSmart Claude plugin

This package is not yet verified in the Claude app. It follows the Claude Code plugin layout so it can be tested later with:

```text
claude --plugin-dir bSmart-System/integrations/claude/bsmart-plugin
```

It does not load the Hermes plugin. `/project` and `/role` are command files that run `integrations/bsmart_client_adapter.py`. The SessionStart hook runs `bStart.py`. A startup skill covers a session where the hook did not inject context.

The hook command tries `python3`, then `python`, then `py -3`, and expands `${CLAUDE_PLUGIN_ROOT}`.

Node.js must be available for `/project` and `/role`.
