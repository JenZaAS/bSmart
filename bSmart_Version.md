# bSmart version and changelog

```yaml
current_version: 0.1.1-draft
updated: 2026-06-05 23:37 UTC
status: draft
```

## 0.1.1-draft

```yaml
release_type: draft_update
scope:
  - add optional shared bSmart collaboration group setup
  - default shared group name is bsmart
  - setup may add selected local users to the group
  - setup applies group ownership, group write access, setgid directories, and default ACLs to approved bSmart-managed roots
  - reusable instructions avoid hardcoded site-local user names
safety:
  - operator reviews group, users, and roots before host-side permission changes
  - runtime, backup, and application data folders are not blanket-changed
```

## 0.1.0-draft

```yaml
release_type: first_draft
scope:
  - system/content split
  - central version/changelog file
  - structured key/value system manifest
  - bSmart Ethos
  - lightweight content log
  - optional extensions root
  - Fabric extension concept
migration_notes:
  - legacy workspace-root bSmart files should not be moved automatically
  - create /workspace/bSmart-System as system repo candidate
  - create /workspace/bSmart as local content root
  - keep /workspace/HERMES.md as minimal Hermes hook
  - update HERMES.md only after operator approval
```

## Future update operation

```yaml
operation: update_bSmart_System
steps:
  - read bSmart_Version.md current version
  - git fetch from configured remote
  - show incoming changelog/migration notes
  - ask operator approval
  - git pull or checkout approved version
  - run bSmart doctor/check
  - report whether content migration is optional or required
constraints:
  - never overwrite /workspace/bSmart content automatically
  - never edit /opt/data/SOUL.md automatically
  - keep HERMES.md minimal
```
