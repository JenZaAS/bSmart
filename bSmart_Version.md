# bSmart version and changelog

```yaml
current_version: 0.1.5-draft
updated: 2026-06-06 10:30 UTC
status: draft
```

## 0.1.5-draft

```yaml
release_type: draft_update
scope:
  - simplify bSmart content-root folder names by removing redundant bSmart_ prefixes inside /workspace/bSmart
  - standard content folders are now Docs, Library, Projects, and Workdocs
  - keep bSmart_ prefixes on root content files such as bSmart_Agent.md, bSmart_State.md, bSmart_TODO.md, and bSmart_Log.md
migration_notes:
  - rename existing content folders from bSmart_Docs, bSmart_Library, bSmart_Projects, and bSmart_Workdocs to Docs, Library, Projects, and Workdocs
  - update references after renaming
```

## 0.1.4-draft

```yaml
release_type: draft_update
scope:
  - define a bSmart secret-storage boundary for Hermes/service containers
  - prefer deployer-native read-only secrets or /opt/docker-workspace/<service>/secrets mounted as /run/secrets:ro
  - explicitly avoid /workspace/secrets, bSmart repos/content folders, and project folders for credentials
safety:
  - private keys require 0600-style permissions
  - collaboration-group permission scripts must not recurse into secret directories
```

## 0.1.3-draft

```yaml
release_type: draft_update
scope:
  - refine bSmart tool approval guardrails for Python/output workflows
  - allow bounded creation of a small number of harmless new output files in approved work folders without repeated extra prompts
  - distinguish harmless new output files from overwrites, deletes, moves, permission changes, sensitive content, executable/deploy-affecting content, and file floods
safety:
  - creating many files, writing outside approved work folders, or writing sensitive/executable/deploy-affecting content still requires explicit operator approval
```

## 0.1.2-draft

```yaml
release_type: draft_update
scope:
  - add generic bSmart tool approval model for low-friction operation
  - recommend Hermes approvals.mode smart during setup when appropriate
  - define bSmart guardrails as the actual safety boundary
  - allow read-only inspection and local no-side-effect Python analysis without repeated extra prompts
  - require explicit operator approval for writes, permission changes, deploy/runtime changes, installs, credentials, sensitive data, external publication, and destructive actions
safety:
  - framework approval mode does not replace bSmart guardrails
  - disabling framework approvals entirely is only for explicitly trusted local/sandboxed environments
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
