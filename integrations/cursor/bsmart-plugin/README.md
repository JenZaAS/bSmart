# bSmart Cursor plugin

Cursor does not load the Hermes `bsmart-project` plugin. This package gives Cursor the same startup and `/project` behavior by calling the shared engine. `/role` only prints a deprecation notice.

`/project` and `/role` run `integrations/bsmart_client_adapter.py`. That adapter resolves trusted workspace paths and calls the Hermes command adapter, which calls `scripts/bsmart-project.mjs`. The session project is passed in the process environment when this conversation already selected one. Chat text cannot supply paths. `/role` calls `scripts/bsmart-role.mjs`, which does not change a project.

The `sessionStart` hook runs `bStart.py` and returns its output as `additional_context`. Cursor has a known race where that context can be dropped. The plugin rule and the workspace `AGENTS.md` hook still require one startup run, and they skip a second run when a `bSmart — Startup` block is already present.

The first reply wraps the visible startup block in a fenced code block because Cursor Markdown collapses single newlines.

## Install

Point Cursor at this directory:

`bSmart-System/integrations/cursor/bsmart-plugin`

For this SschwAdmin workspace, the same commands, rule, and startup hook are also enabled from the workspace `.cursor` directory so they work before a marketplace install. Start a new chat after enabling the hook.

Node.js must be available. Run `python3`. If it is missing or fails, use `python` (or `py -3` on Windows).
