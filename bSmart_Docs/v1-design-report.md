# bSmart v1 design report

```yaml
status: draft
created: 2026-05-31 13:54 UTC
purpose: Summarize the agreed bSmart v1 structure before GitHub publication.
```

## Agreed structure

```yaml
workspace_roots:
  system:
    path: /workspace/bSmart-System
    role: versioned GitHub repo
    update_policy: git pull may update system files only
  content:
    path: /workspace/bSmart
    role: local instance content/state
    update_policy: never overwritten by system updates
  extensions:
    path: /workspace/bSmart-Extensions
    role: optional external extension packs
  hermes_hook:
    path: /workspace/HERMES.md
    role: tiny Hermes startup hook outside bSmart
```

## System contents

```yaml
bSmart-System:
  required_files:
    - README.md
    - bSmart.md
    - bSmart_Setup.md
    - bSmart_Version.md
  required_folders:
    - bSmart_Protocols
    - bSmart_Templates
    - Docs
    - bSmart_Examples
```

## Content contents

```yaml
bSmart:
  required_files:
    - README.md
    - bSmart_Agent.md
    - bSmart_State.md
    - bSmart_TODO.md
    - bSmart_Log.md
  required_folders:
    - Projects
    - Workdocs
    - Library
```

## Ethos

```yaml
ethos:
  operator_sovereignty: Protect operator finances, data, privacy, reputation, and trust.
  intellectual_humility: Never hallucinate with confidence; mark uncertainty.
  radical_transparency: Important decisions/approvals should be traceable.
  direct_speech: Communicate briefly, precisely, and honestly.
```

## Logging

```yaml
log_file: /workspace/bSmart/bSmart_Log.md
scope:
  - setup completed
  - system updated
  - project/task started or completed
  - user confirmations
  - risk approvals
  - migration applied
not_scope:
  - full transcripts
  - secrets
  - routine tool output
```

## Fabric extension

```yaml
path: /workspace/bSmart-Extensions/Fabric
status: optional planned extension
source: https://github.com/danielmiessler/Fabric
license: MIT
setup_default: yes
```

## Important open decisions before GitHub

```yaml
operator_needed:
  - GitHub repository owner/name for the new bSmart repo
  - whether to create repo via GitHub UI or let SschwAdmin prepare commands
  - whether to archive/delete the old Hermatrix repo or just ignore it
  - when to switch live /workspace/HERMES.md from legacy /workspace/bSmart.md to /workspace/bSmart-System/bSmart.md
```
