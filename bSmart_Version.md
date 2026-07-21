# bSmart version and changelog

```yaml
current_version: 0.1.9-draft
updated: 2026-07-17 09:21 UTC
status: draft
```

## 0.1.9-draft

```yaml
release_type: draft_update
scope:
  - make startup/storage helper scripts infer workspace/content roots from their own bSmart-System checkout, so they work from VPS /workspace and local AGENTS.md workspaces
  - document CIFS/SMB executable-bit pitfall and prefer python3 <script> invocations for bSmart Python helpers
  - replace Hermes-specific startup wording with framework-neutral "bSmart — Loading bSmart."
  - add local path-resolution guidance so local AGENTS.md agents map /workspace/bSmart-System to ./bSmart-System and /workspace/bSmart to ./bSmart
  - make project listing explicitly use the selected project root and not fail when legacy /workspace/bSmart/Projects is absent
  - add portable sandbox-root selection for local/non-container agents: BSMART_SANDBOX_ROOT, then /sandboxes, then ./sandboxes, then ./bSmart/Sandboxes
  - add portable project-root selection for local/non-container agents: BSMART_PROJECT_ROOT, then /projects, then ./projects, then /workspace/bSmart/Projects
  - add scripts/bsmart-bootstrap-workspace as the streamlined host-side initializer for new bSmart-enabled AI workspaces
  - document that all newly initialized AI agents should run bSmart by default
  - clarify that bSmart-System must live as a workspace Git checkout, not as stale image-baked content
  - allow images/start wrappers to include only a tiny first-run bootstrap hook that fetches the live workspace helper
  - standardize new-agent Compose defaults: working_dir=/workspace, TERMINAL_CWD=/workspace, HERMES_WRITE_SAFE_ROOT=/workspace
  - separate bSmart-System Git from optional instance/content Git to avoid setup ambiguity
safety:
  - helper creates only missing local content files and uses public HTTPS for bSmart-System updates
  - bSmart content Git is opt-in/local-only by default; no remote is configured unless the operator chooses it
verification:
  - helper syntax-tested and exercised against a temporary workspace with local content Git enabled
```

## 0.1.8-draft

```yaml
release_type: draft_update
scope:
  - make project-storage setup treat host sandbox-folder creation as a required pre-compose step
  - update bsmart-project-storage-check output so host prep appears before volume lines with an explicit do-not-add-yet warning
  - use sudo install -d -o 10000 -g 10000 -m 0775 for VPS-local /sandboxes host folders
  - make bSmart-enabled AI instances use HTTPS for public bSmart-System updates by default, without requiring per-container GitHub SSH secrets
  - run the daily startup check with --auto-pull so clean bSmart-System repos can fast-forward safely
safety:
  - prevents Docker/Dokploy from auto-creating missing bind-mount sources as root:root and leaving /sandboxes unwritable inside containers
  - bSmart-System auto-pull remains limited to clean, expected-branch, fast-forward-only updates; instance content under /workspace/bSmart is not auto-updated
migration_notes:
  - existing instances with root-owned sandbox bind sources can repair them with the same install -d command, then verify write access inside the container
  - existing sibling AI installs that inherited SSH remotes should switch /workspace/bSmart-System origin to https://github.com/JenZaAS/bSmart.git and unset core.sshCommand
```

## 0.1.7-draft

```yaml
release_type: draft_update
scope:
  - add first-class project storage configuration for containerized bSmart instances
  - prefer /projects as canonical project root when mounted, with /workspace/bSmart/Projects as fallback
  - add /sandboxes/<project-slug> as the preferred VPS-local per-project sandbox root
  - add instance Git setup as an explicit optional/recommended bSmart setup choice
  - add nested Git hygiene helper for ignoring external code repos inside projects
  - document daily bSmart-System update checks for /new startup
  - add concrete startup helper scripts for daily Git freshness and project-storage checks
  - document need for read-only Dokploy compose visibility to avoid blueprint/runtime drift
migration_notes:
  - existing instances must manually pull this bSmart-System update once because daily update checks did not exist in older versions
  - after update, /new should create or prompt for /workspace/bSmart/State/container-storage.yaml when missing
  - project-storage setup should guide the operator to add a /projects volume line to Compose/Dokploy
  - sandboxes should move toward /sandboxes/<project-slug>; legacy project-local sandbox folders remain valid fallback
helpers:
  - /workspace/bSmart-System/scripts/bsmart-startup-check
  - /workspace/bSmart-System/scripts/bsmart-system-update-check
  - /workspace/bSmart-System/scripts/bsmart-project-storage-check
```

## 0.1.6-draft

```yaml
release_type: draft_update
scope:
  - add bundled-extension source root under /workspace/bSmart-System/bSmart-Extensions
  - add bundled optional bSearch extension as a packaged bSmart add-on
  - distinguish bundled optional extensions from external optional extensions such as Fabric
  - update setup/docs so initialization can offer bSearch with a short explanation
migration_notes:
  - bundled extension source stays in bSmart-System
  - installed extension state lives under /workspace/bSmart-Extensions
  - existing instances can copy or sync /workspace/bSmart-System/bSmart-Extensions/bSearch into /workspace/bSmart-Extensions/bSearch to enable the extension
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
