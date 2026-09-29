# bSmart Cursor plugin

Cursor does not load the Hermes `bsmart-project` plugin. This package gives Cursor the same startup, `/project`, and `/role` behavior by calling the shared engines.

`/project` and `/role` run `integrations/bsmart_client_adapter.py`. That adapter resolves trusted workspace paths and calls the Hermes command adapter, which calls `scripts/bsmart-project.mjs` and `scripts/bsmart-role.mjs`. Chat text cannot supply paths.

The `sessionStart` hook runs `bStart.py` and returns its output as `additional_context`. Cursor has a known race where that context can be dropped. The plugin rule and the workspace `AGENTS.md` hook still require one startup run, and they skip a second run when a `bSmart — Startup` block is already present.

The first reply wraps the visible startup block in a fenced code block because Cursor Markdown collapses single newlines.

## Install

Point Cursor at this directory:

`bSmart-System/integrations/cursor/bsmart-plugin`

For this SschwAdmin workspace, the same commands, rule, and startup hook are also enabled from the workspace `.cursor` directory so they work before a marketplace install. Start a new chat after enabling the hook.

Node.js must be available. Use `python` on Windows and `python3` where that is the only interpreter.
