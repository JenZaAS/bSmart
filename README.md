# bSmart-System

```yaml
name: bSmart-System
status: draft-v1
purpose: Portable system layer for bSmart-enabled Hermes workspaces.
system_root: /workspace/bSmart-System
content_root: /workspace/bSmart
extensions_root: /workspace/bSmart-Extensions
license: MIT
```

## What this repo contains

```yaml
contains:
  - reusable bootstrap instructions
  - setup and update procedures
  - protocols
  - templates
  - docs
  - examples
  - version and changelog

excludes:
  - local agent identity
  - local projects
  - local TODOs
  - local workdocs
  - local logs
  - secrets
  - Hermes runtime state
```

## Standard workspace layout

```text
/workspace/
├── bSmart-System/       # this git repo; safe to update
├── bSmart/              # local content/state; not overwritten by system updates
├── bSmart-Extensions/   # optional extension packs, e.g. Fabric
└── HERMES.md            # tiny Hermes hook outside bSmart
```

## Update rule

```yaml
system_update_rule:
  allowed_to_modify:
    - /workspace/bSmart-System
  must_not_modify_without_approval:
    - /workspace/bSmart
    - /workspace/bSmart-Extensions
    - /workspace/HERMES.md
    - /opt/data/SOUL.md
```

See:
- `bSmart.md` for runtime bootstrap instructions.
- `bSmart_Setup.md` for first-time setup.
- `bSmart_Version.md` for version history and migration notes.
- `bSmart_Docs/system-vs-content.md` for the separation model.
