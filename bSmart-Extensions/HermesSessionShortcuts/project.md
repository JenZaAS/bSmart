---
name: HermesSessionShortcuts
status: packaged_in_bsmart_system
owner: Erling H Jensen / SschwAdmin
objective: Package reusable Hermes session-list/resume slash shortcuts as an optional bSmart extension and Docker-image-installable plugin.
---

## Packaging model

- Canonical packaged source: `/workspace/bSmart-System/bSmart-Extensions/HermesSessionShortcuts`.
- Installed bSmart copy: `/workspace/bSmart-Extensions/HermesSessionShortcuts`.
- Hermes plugin payload: `plugins/session-shortcuts/`.

## Operational model

The plugin should be copied or synced into each Hermes instance's persistent home under `/opt/data/plugins/session-shortcuts` and enabled with `hermes plugins enable session-shortcuts --no-allow-tool-override`.

For Docker images with `/opt/data` bind-mounted, bake the payload under `/opt/hermes/bsmart-plugins/session-shortcuts` and sync it into `/opt/data/plugins` at startup.
