# bSmart version and changelog

```yaml
current_version: 0.1.45.3-draft
updated: 2026-10-10 11:15 UTC
status: draft
```

## How to record a version

Every system change gets a new section in this file, newest first, and the `current_version` field moves with it. Pick the next free draft number. Do not reuse a number another open change has taken. A patch such as `0.1.45.2-draft` is a normal entry when the next minor number is already reserved.

The section is the changelog. Every version stays here. Add a `news` field only when the change is news-worthy: it changes the user's workflow, the commands they type, or what they see in a session. Bug fixes, refactors, encoding work, test-only changes, and other behind-the-scenes work stay in `scope` and `verification` and are not announced.

Write `news` as one short plain-language paragraph, a few sentences. Say what the user does differently. Keep the characters ASCII. Put it in that version's yaml block, before `scope`:

```yaml
news: |
  Short paragraph for the user. No changelog bullets.
```

`scripts/bsmart-release-notice` is the only announcer. Version order is numeric, so a heading that sits out of order in this file (0.1.19-draft is listed above 0.1.31-draft) is still placed by its number. A version string that is not in this file is compared by that number when it parses, and is ignored when it does not. It is not treated as older than every entry.

The record is `bSmart/State/bsmart-release-notice.yaml`. It has existed since 0.1.20, which wrote only `last_announced_version: <current>`. That old format has no `seen_news` key. When that file is present and an existing-instance signal is also present, every flagged news item through the current version is unseen. The daily check on main could record `0.1.45.1-draft` after the 0.1.45 roles change, which is newer than that news, so "that version and later" would hide it. The seen list, written when interactive `bStart` records, is what keeps the showing to once. Without a signal, the old file still means that version and later ones. A record that has `seen_news` shows only flagged news after `last_announced_version`.

`bsmart-bootstrap-workspace`, and the manual installer in `README.md`, write a fresh baseline (`baseline: fresh`, the current version, empty `seen_news`) and retry that write. Neither creates `bSmart_State.md`. A new instance therefore does not replay historical news, including when the baseline write fails. When the record is absent, the only existing-instance signals are `Roles/`, legacy `bSmart_State.md`, and `State/role-migration.json`. Those show every flagged news item through the current version once. Other files under `State/`, including `container-storage.yaml` and `bsmart-system-update.yaml`, are not signals. `ORIG_HEAD` is not a signal. An instance that already migrated before `seen_news` existed still gets the 0.1.45 note once, from `bStart`.

Only interactive `bStart` marks news seen. It runs the notice before its update check writes state. A Hermes cron job or other automation that loads `HERMES.md` and runs `bStart` should pass `--no-record` or set `BSMART_NEWS_NO_RECORD=1` (`true`, `yes`, and `on` also count). That still prints the news and does not mark it seen, so the next interactive session can relay it. `bsmart-instance-upgrade` (and therefore `bsmart-update`) and `bsmart-startup-check` may print a preview and do not record it. A failed notice does not fail the upgrade. The state file is replaced atomically, and a short lock keeps two startups from both printing.

## 0.1.45.3-draft

```yaml
release_type: public_tree_privacy
scope:
  - replace site-specific instance names, people, host labels, job ids, timezone defaults, and host paths in the public tree with placeholders
  - keep GitHub organization URLs and the license holder
  - keep explicit caller-supplied values working when a baked-in site default changes to a generic one
  - add a tree check that matches SHA-256 hashes of lowercased tokens and does not store those tokens
  - share that digest list with the Hermes runtime lookup checks, and allow no remaining matches
  - also match a windows path, a joined three-word name, and an agent name at the start of a CamelCase or digit compound
  - keep common words off that list and hash a specific identifying form instead
  - keep the dreaming cron expressions at 02:00 and 02:30 local, and say to convert them when the scheduler runs in UTC
  - record, in the protocol index, how a contributor adds a term by hash
safety:
  - the check reports a path and a digest, not the matched text
  - no file is exempt
verification:
  - python and node tests pass on Linux, Windows, and macOS for Python 3.11 and 3.12
  - tests do not pin current_version, so a later draft can move the header
```

## 0.1.45.2-draft

```yaml
release_type: user_facing_release_news
scope:
  - mark a version as user-facing news with an optional news paragraph in this file; unflagged versions stay in the changelog only
  - show that news once, oldest first, for every flagged version after the instance's last announced version
  - keep the record in bSmart/State/bsmart-release-notice.yaml; an old file with no seen_news key includes that version, and with Roles/, legacy bSmart_State.md, or the role-migration marker it shows every flagged item through the current version once
  - record a fresh baseline from bootstrap and the manual installer, retry that write, do not create bSmart_State.md, and ignore State cache files and ORIG_HEAD
  - let bStart --no-record and BSMART_NEWS_NO_RECORD=1 print news without marking it seen, for a Hermes cron job or other automation that loads HERMES.md
  - compare versions numerically, and ignore an unparseable version instead of treating it as older than every entry
  - surface a preview from startup check and instance upgrade without recording it; a notice failure does not fail the upgrade
  - tell the agent, in the startup instructions, to relay the news briefly in its next reply
  - add the 0.1.45-draft news paragraph for the move from roles to session projects
verification:
  - bStart prints news once and records it; a second bStart is silent
  - skipped versions accumulate every flagged news item in between, oldest first, including when headings are out of numeric order
  - a version without news is not announced
  - a version string missing from this file is not treated as older than every entry
  - bootstrap, then bStart with its system-update state write, prints no historical news
  - container-storage.yaml, bsmart-system-update.yaml, and ORIG_HEAD do not by themselves show historical news
  - an old-format notice file at 0.1.45-draft includes the 0.1.45 news
  - an old-format notice file at 0.1.45.1-draft plus Roles/ shows the 0.1.45 news once
  - bStart --no-record and BSMART_NEWS_NO_RECORD=1 print news and leave the record unchanged
  - a bootstrap whose baseline write fails does not create bSmart_State.md, and the following bStart prints no historical news
  - instance upgrade prints a preview and leaves the record unmarked; the following bStart records it
  - an instance with Roles/, legacy bSmart_State.md, or a role-migration marker and no notice file is shown the 0.1.45 news once by bStart
  - the same notice appears from the Hermes bSmart-System/bStart.py layout and the workspace-root bStart.py layout
  - python and node tests pass on Linux, Windows, and macOS for Python 3.11 and 3.12
```

## 0.1.45.1-draft

```yaml
release_type: containerized_hermes_protocol
scope:
  - add a Hermes runtime protocol for every host, with Compose, pull_policy, image build, and s6 limited to orchestrated Docker
  - keep host blueprint, built image, live Compose, and the running container distinct, and require an allowlisted update harness when the host provides one
  - require pull_policy never as a service-level sibling of image for every host-local image; next-line placement is a readability convention because Compose ignores key order, and separate image-build, sanity-container, and runtime success
  - keep bSmart system and instance updates from being treated as an image rebuild or a live Compose change
  - keep state.db corruption in an incident-only section: recover from a stopped copy, use recover --output, convert the copy with journal_mode=DELETE, and move state.db with its wal and shm aside before placing that single file as the container user
  - chown a bootstrapped workspace without following symlinks, and fail when requested ownership cannot be applied
  - use <host-agent-root> and <host-share-root> placeholders in public install and secret-mount examples
  - link the protocol from the protocol index, system map, feature registry, setup, startup manifest, and README
  - stop the project-storage helper from inventing a host sandbox path out of a share folder name, and print the container uid and gid as placeholders the operator confirms
safety:
  - the protocol is generic and contains no site agent names, credentials, or host-specific helper paths
  - no deployment, image build, or orchestrator change is performed by this version
verification:
  - lookup tests confirm the protocol is indexed and retrievable through bMap and the Setup feature card
  - python and node tests pass on Linux, Windows, and macOS for Python 3.11 and 3.12
```

## 0.1.45-draft

```yaml
release_type: session_scoped_projects
news: |
  Roles are gone. Each session starts in Free mode. Work happens in projects and
  workstreams, selected for this session with /project. Each project keeps its
  own handoff, which you write when switching away. projects/INDEX.md lists the
  projects. /role now only points to /project. Existing roles were migrated where
  unambiguous (anything skipped is listed as a question).
scope:
  - remove the instance-wide role selector; projects are the unit
  - keep the active project and workstream in the session, starting in Free mode, and never guess
  - store durable focus and handoff in the project, with a separate handoff per workstream
  - write the old project's handoff before switching, then print a compact startup block
  - keep a central projects/INDEX.md updated only by project commands
  - have bStart read that index, list active projects, generate a missing index, and flag mismatches
  - deprecate /role with a short pointer to /project
  - tag real work as "bSmart [<scope>]: <ops> - <note>"
  - back up Roles/ and bSmart_State.md, then merge unambiguous handoffs without overwriting existing text
  - write the migration manifest before changing a handoff, skip non-UTF-8 handoffs, and keep later notes unless the file still matches what migration wrote
  - run role migration once per instance; the marker is written even when questions remain, and deleting it is how a skipped handoff is retried
  - restore removes the migration marker, so the next update migrates again unless the system copy is downgraded
  - remove a retired or deleted project from the session only when that session was on it
  - refuse bsmart-instance-upgrade's /workspace default unless the process is already inside it, and name that workspace before changing it
  - keep unrecognised role fields in the instance review file and the backup, not in the project handoff
  - remember the project for Hermes, Cursor, Claude, Codex, and the shell adapter, and accept an exact /project delete|retire|rename NAME plus handoff: text
migration:
  - bsmart-update and bsmart-instance-upgrade run the migration and print questions for ambiguous roles
  - restore with bsmart-instance-upgrade --restore-session-projects <backup-directory>
  - before merging this change, tag the current main commit: git tag -a pre-session-projects -m "bSmart before session-scoped projects"
  - after the merge commit, tag the release: git tag -a 0.1.45 -m "bSmart 0.1.45 session-scoped projects"
  - do not push those tags unless the operator wants them on the remote; this repo records versions in bSmart_Version.md
verification:
  - session selection does not write Roles/current_role.md
  - two sessions can select different projects without changing each other
  - a missing index is created and a present index is not rewritten by startup
  - switching projects appends a handoff and leaves existing handoff text in place
  - migration backs up Roles/ and restores those bytes
  - python and node tests pass on Linux, Windows, and macOS for Python 3.11 and 3.12
```

## 0.1.44.1-draft

```yaml
release_type: startup_output_encoding
scope:
  - reconfigure bStart stdout and stderr to UTF-8, and escape characters when a stream cannot change encoding, so a legacy pipe code page cannot abort startup
  - keep that behavior in the workspace-root bStart.py that bsmart-instance-upgrade installs, because that copy is this same file
  - decode session-start hook input and bStart output as UTF-8, and launch bStart with UTF-8 stdio
verification:
  - bStart exits 0 under PYTHONIOENCODING=cp1252:strict when printed content contains U+2610
  - the session-start hook preserves that character in its UTF-8 context payload
  - python and node tests pass on Linux, Windows, and macOS
```

## 0.1.44-draft

```yaml
release_type: harness_independent_install
scope:
  - skip the Hermes /project adapter when the hermes CLI and an existing Hermes profile are both absent, without creating ~/.hermes
  - let bsmart-update and bsmart-startup-check finish on non-Hermes harnesses
  - resolve bStart.py from both bSmart-System and the workspace-root copy
  - prefer python3 in startup hooks; if python3 is missing or fails, use python or py -3 on Windows
  - add bsmart-project-storage-check --configure-internal for workspace-local ./projects storage
  - store internal storage paths as workspace-relative ./projects and ./sandboxes, and still honor absolute paths already in a spec
  - prefer the sibling bSmart content root over a hardcoded /workspace path when both exist
  - choose the checkout sibling workspace in bsmart-update before falling back to /workspace
  - share default_content_root across the checkout scripts that write instance state
  - require the hermes CLI only when the adapter still needs to be enabled; an already current and enabled adapter stays successful without the CLI
  - launch a Windows hermes .cmd shim as one ComSpec /d /s /c command so paths with spaces are not re-quoted
  - realpath a configured projects root once, then reject symlinks and junctions below it, including a broken link
  - resolve the instance project root from BSMART_PROJECT_ROOT, then container-storage.yaml, then /projects and ./projects, in bStart, the client adapter, and the Hermes /project plugin
  - let an installed Hermes /project plugin read that spec from /workspace/bSmart-System when BSMART_SYSTEM_ROOT is unset
  - write bProtective state with POSIX mode 0o600, and on Windows call System32\\icacls.exe with a read/write/delete grant and a 10 second timeout
  - keep update and startup state in the instance that was started when several instances share a machine, including a symlinked bSmart-System
verification:
  - integration check returns success and creates no Hermes home when hermes is absent
  - integration check still installs and enables the adapter when a hermes CLI is present
  - workspace-root and in-system bStart.py copies both resolve the workspace
  - --configure-internal writes container-storage.yaml with ./projects and ./sandboxes and creates those directories
  - an existing absolute storage spec still resolves to that absolute path
  - findmnt absence stays a skipped host-mount inference
  - existing unittest and node project tests pass
  - two instances on one filesystem keep bsmart-system-update.yaml and startup state in the instance that was started
  - python and node tests pass on Linux, Windows, and macOS
  - an enabled current Hermes adapter returns success when hermes is not on PATH
  - a symlinked projects root can create a project, and a symlinked or broken project directory is rejected
  - startup, the client adapter, and the Hermes plugin follow container-storage.yaml when BSMART_PROJECT_ROOT is unset
  - an installed Hermes plugin copy under hermes-home/plugins/bsmart-project reads the spec when BSMART_SYSTEM_ROOT is unset
  - the Windows icacls invocation uses System32\\icacls.exe, grants (R,W,D), and a timeout does not fail the write
```

## 0.1.43-draft

```yaml
release_type: remove_project_typo_alias
scope:
  - remove the /projcet command from the shared engine and from Hermes, Cursor, Codex, and Claude
  - keep /project as the only project slash command
verification:
  - project plugin tests no longer register projcet
  - client plugin tests confirm the Cursor projcet command file is absent
```

## 0.1.42-draft

```yaml
release_type: client_plugins
scope:
  - add Cursor, Codex, and Claude plugins that call the shared /project and /role engines
  - run bStart from client session hooks, with AGENTS.md still requiring one startup
  - leave the Claude plugin unverified until it can be tested in the Claude app
verification:
  - client plugin unit tests pass
  - isolated /project add and /role help pass through the shared adapter
```

## 0.1.41-draft

```yaml
release_type: command_help_clarity
scope:
  - explain the role concept in /role help
  - implement the documented /project help command
  - add regression coverage for both help surfaces
verification:
  - project/role Node tests pass
  - prior system, bSwarm, and bStart tests remain green
```

## 0.1.40-draft

```yaml
release_type: mounted_git_ownership_compatibility
scope:
  - handle Git safe-directory checks for mounted repositories
  - accept the selected branch and upstream during freshness checks
  - make bStart Git status work under differing container filesystem ownership
verification:
  - Git ownership/branch smoke check passes
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.39-draft

```yaml
release_type: container_git_and_branch_compatibility
scope:
  - handle mounted bSmart-System repositories with differing filesystem ownership
  - accept the selected branch and its upstream during freshness checks unless a branch is explicitly required
  - support named non-main instance testing on redesign/deterministic-startup without a false main-branch warning
verification:
  - system update helper compiles and runs
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.38-draft

```yaml
release_type: refresh_stale_managed_project_plugin
scope:
  - detect stale installed bsmart-project plugin files
  - back up and refresh the managed plugin during bsmart-update
  - ensure role-owned project context reaches /project commands
verification:
  - project plugin tests pass
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.37-draft

```yaml
release_type: preserve_bstart_first_reply
scope:
  - require startup hooks to preserve bStart output and command-help lines
  - prevent instance-specific greeting policies from replacing the startup summary
  - synchronize the rule through existing-instance update backups
verification:
  - system, project, bSwarm, and bStart tests remain green
```

## 0.1.36-draft

```yaml
release_type: automatic_known_instance_migrations
scope:
  - apply the known startup-reply compatibility migration during bsmart-update
  - back up bSmart_Agent.md before the narrow exact replacement
  - reserve approval prompts for ambiguous or broader instance changes
verification:
  - upgrade migration test passes
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.35-draft

```yaml
release_type: low_friction_instance_profile_migration
scope:
  - detect known outdated bSmart_Agent.md startup-reply sections during update
  - print a narrow proposed replacement without silently changing instance content
  - require one explicit operator approval before applying the instance-local patch
verification:
  - upgrade review test passes
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.34-draft

```yaml
release_type: explicit_pull_then_update_workflow
scope:
  - add bsmart-update as the deterministic post-pull finalization command
  - distinguish Git pull from instance startup integration and content repair
  - document pull, update, restart, /new, and Hi as the standard sequence
verification:
  - update helper preserves instance content/state
  - prior system, project, bSwarm, and bStart tests remain green
```

## 0.1.33-draft

```yaml
release_type: existing_instance_startup_upgrade
scope:
  - add an explicit instance-upgrade helper for existing workspaces
  - back up and synchronize canonical startup hooks
  - install workspace-root bStart.py without changing instance content/state
  - update fresh bootstrap to install bStart.py and the current hook
verification:
  - isolated upgrade test passes
  - system, project, bSwarm, and bStart tests remain green
```

## 0.1.32-draft

```yaml
release_type: final_role_project_runtime_reconciliation
scope:
  - make the selected role file the sole active owner of project, workstream, focus, and handoff state
  - add /role help, /role list, /role set, and /role add through the shared runtime
  - make /project and /project ws resolve and update the selected role
  - preserve bSmart_State.md for explicit migration and review, including unknown legacy fields
  - verify role-file collision locking and synchronize map, protocol, template, adapter, and tests
verification:
  - role/project Node tests pass
  - Python system, bSwarm, and bStart tests pass
```

## 0.1.19-draft

```yaml
release_type: safety_feature
scope:
  - add disabled-by-default bProtective Hermes pre-tool guard
  - block catastrophic terminal commands deterministically
  - escalate risky terminal commands to Hermes operator approval
  - require confirmation to enable or disable bProtective
  - document bProtective in setup, help, feature registry, and operations protocol
verification:
  - focused bProtective tests pass
  - Hermes plugin manifest and registration are validated
```

## 0.1.31-draft

```yaml
release_type: deterministic_startup_entrypoint
scope:
  - add bStart.py as the session entrypoint
  - perform safe bSmart-System auto-update checks and post-update integrity verification
  - silently recover the role selector and General role
  - resolve one role, project, and optional workstream
  - load selected Markdown context and emit the compact startup summary
  - add CLAUDE.md as an identical canonical launcher hook
verification:
  - isolated bStart tests pass
  - system and bSwarm tests pass
  - launcher templates remain identical
```

## 0.1.30-draft

```yaml
release_type: map_maintenance_contract
scope:
  - reflect role-owned state, role files, and `.bLock` artifacts in bSmart_Map.md
  - list the role protocol and template in the system map
  - require same-change map updates for logical structure, ownership, loading, and state-model changes
  - add regression coverage for map completeness and maintenance guidance
verification:
  - map entries resolve to existing system files
  - system and bSwarm tests pass
```

## 0.1.29-draft

```yaml
release_type: role_owned_state_and_concurrency
scope:
  - define one always-available General role and one role file per operational hat
  - make role files the active owners of project, workstream, focus, and handoff state
  - retire bSmart_State.md as an active source and retain it only for explicit migration
  - allow multiple roles to work on the same project without project-wide locks
  - define narrow per-file `.bLock` collision handling with bounded retries and operator override
verification:
  - role and concurrency protocols exist and are indexed
  - no remaining active protocol treats bSmart_State.md as authoritative
  - prior system and bSwarm tests remain green
```

## 0.1.28-draft

```yaml
release_type: instance_guardrails
scope:
  - add the instance-editable bGuardrails template
  - keep guardrails below bSmart_Invariants.md in authority
  - create and route bGuardrails as instance content without modifying existing profiles automatically
  - add communication, task-label, approval, context, and feature-preference defaults
verification:
  - guardrails template regression test passes
  - setup and missing-content paths reference the template
  - prior system and bSwarm tests remain green
```

## 0.1.27-draft

```yaml
release_type: instance_backup_policy
scope:
  - prompt before creating local Git for an instance without Git
  - explain that local history can later be connected to a remote repository
  - require operator review of dirty instance content before pre-update backup commits
  - define separate pre-update and post-update commits and remote pushes
verification:
  - instance Git protocol and setup document agree
  - no force-push or silent unrelated-content commit is allowed
```

## 0.1.26-draft

```yaml
release_type: instance_profile_structure
scope:
  - reduce bSmart_Agent.md to stable identity, verified access, paths, feature pointers, and ownership links
  - move generic safety and operational guidance to invariants and protocols
  - update the reusable bSmart_Agent template to prevent mixed policy/state profiles
verification:
  - existing instance facts preserved or routed to canonical system protocols
  - profile backup created before restructuring
  - prior system and bSwarm tests remain green
```

## 0.1.25-draft

```yaml
release_type: setup_protocol_boundary
scope:
  - add the compact protocol index and map it as startup metadata
  - define ownership between setup, protocols, startup routing, invariants, instance content, and projects
  - link setup domains to their canonical detailed protocols without removing setup prompts/defaults
verification:
  - all indexed protocols exist
  - setup protocol links resolve
  - prior system and bSwarm tests remain green
```

## 0.1.24-draft

```yaml
release_type: system_boundary_refinement
scope:
  - establish bSmart_Invariants.md as the absolute cross-runtime system contract
  - separate invariants from startup routing and instance-editable guardrails
  - update the map and startup sequence to load the invariant boundary
verification:
  - invariant file exists and is referenced by bSmart.md and bSmart_Map.md
  - prior system and bSwarm tests remain green
```

## 0.1.23-draft

```yaml
release_type: deterministic_startup_and_dreaming_revision
scope:
  - add the generic bSmart map and feature lookup tools
  - add compact machine-readable feature index entries
  - include the revised Dreaming no-op and change-only reporting contract
  - document bootstrap and setup behavior for the revision
verification:
  - system lookup tests pass
  - existing system and bSwarm tests pass
  - Dreaming protocol contains the exact no-op response contract
```

## 0.1.22-draft

```yaml
release_type: reporting_refinement
scope:
  - make Dreaming report only actual findings, changes, or actionable asks
  - require the exact no-op message `bDreaming has nothing to report.`
  - align daily and weekly Dreaming cron prompts with the concise reporting contract
verification:
  - canonical Dreaming protocol updated
  - daily and weekly scheduler jobs updated and remain enabled
```

## 0.1.21-draft

```yaml
release_type: usability_refinement
scope:
  - explain the concrete purpose of startup maintenance before tool approval
  - name bSmart-System updates, bHistory repair, and /project installation explicitly
safety:
  - keep healthy maintenance checks silent after the explanatory pre-action note
verification:
  - startup protocol and action-note wording read back after update
```

## 0.1.20-draft

```yaml
release_type: maintenance_and_onboarding
scope:
  - add automatic create-only bHistory repair for existing instances
  - add quiet standard-content checks on every /new
  - add automatic installation and enablement of the managed Hermes /project adapter
  - add one-time per-instance release notices for new bSmart-System versions
  - keep heavier Git and storage checks once-per-UTC-day throttled
safety:
  - existing instance content is never overwritten by standard-content repair
  - managed plugin changes report when a Hermes restart or relaunch is required
verification:
  - quiet healthy checks produce no output
  - missing adapter installation and enablement tested in an isolated temporary Hermes home
```

## 0.1.18-draft

```yaml
release_type: usability_refinement
scope:
  - keep bQAbuild one-question-at-a-time interaction
  - expose current position, total question count, and remaining questions
safety:
  - no change to decision capture or build-brief approval boundaries
verification:
  - bQAbuild tests verify progress metadata
```

## 0.1.17-draft

```yaml
release_type: feature_classification
scope:
  - promote bQAbuild from optional bundled extension to standard active bSmart feature
  - register bQAbuild in the bSmart manifest, feature registry, and extension documentation
safety:
  - keep the packaged handler separate from instance-local Q&A session state
  - preserve the boundary that generated briefs do not authorize edits, publication, deployment, or deletion
verification:
  - feature and extension registries read back with matching active/bundled_feature status
```

## 0.1.16-draft

```yaml
release_type: feature_update
scope:
  - add optional bQAbuild question-and-answer scoping extension
  - record one-question-at-a-time decisions in instance-local state
  - generate a concise implementation brief only after all configured questions are answered
safety:
  - keep session state outside the public bSmart-System repository
  - do not edit source code, commit, publish, deploy, or store secrets
verification:
  - bQAbuild unit tests pass
  - real CLI lifecycle creates state and a generated brief
```

## 0.1.15-draft

```yaml
release_type: wording_refinement
scope:
  - make concise, direct responses the default for all bSmart agents
  - instruct agents not to overexplain and to expand only when asked, required, or needed for safety/correctness
safety:
  - preserve exact commands, paths, diffs, warnings, approvals, uncertainty, and blockers
verification:
  - read back the updated response_style block in bSmart.md
```

## 0.1.14-draft

```yaml
release_type: feature_update
scope:
  - add a separate operator-triggered local-agent onboarding protocol for host and Docker agents
  - derive local agent paths from the current session and confirm the agent root once
  - use fixed sibling bSmart, projects, and sandboxes folders
  - support configurable admin and specialist agent names with derived identifiers
  - add optional Codex, OpenCode client/CLI, and Claude client/CLI installation with working-directory verification
  - define isolated Hermes homes, Docker identities, mounts, and staged shortcut launch
  - hand off bSmart feature onboarding to the launched agent instead of duplicating it
  - defer optional per-agent instance Git setup until the final workflow stage
  - clarify Dreaming's purpose in the bSmart setup prompt
safety:
  - local-only scope excludes VPS, Dokploy, EPS, and cloud deployment
  - no secrets are placed in system files, shortcuts, repositories, or chat
  - existing profiles, homes, containers, shortcuts, and nested sandboxes are inspected before changes
  - container recreation, broad mounts, credential changes, publication, and migrations remain approval-gated
verification:
  - edited sections read back after correction
  - documentation references and path boundaries checked
```

## 0.1.13-draft

```yaml
release_type: feature_update
scope:
  - create `knowledge/task-context-routing.md` for new projects
  - add a compact context-routing pointer to generated `project.md`
  - document task-bundle selection, on-demand loading, and legacy-flow verification
  - provide a reusable generic routing template without imposing domain-specific bundles
safety:
  - keeps routing project-local rather than adding project details to global startup files
  - limits default context loading to the smallest relevant knowledge bundle
verification:
  - project runtime regression tests pass
  - generated project structure and routing pointer verified
```


## 0.1.12-draft

```yaml
release_type: portability_fix
scope:
  - make local startup checks usable from read-only Windows/non-Linux checkouts
  - treat unavailable Linux findmnt probing as a skipped host-mount inference
  - treat daily state files as best-effort caches rather than a prerequisite for Git checks
  - document the direct-Git fallback behavior in the startup manifest
safety:
  - no deployment, mount, or host-side changes
verification:
  - Python helpers compile successfully
  - storage check completes without findmnt-dependent failure
  - Git update and startup checks continue when state paths are unwritable
```

## 0.1.11-draft

```yaml
release_type: draft_update
scope:
  - add canonical State protocol for active/current project ownership, Free Mode, state changes, and drift handling; feature-specific protocols should reference it rather than restating the rule
  - remove a previously considered external secret-service provider from public bSmart-System because current terms make it unsuitable for this use
  - keep secret-provider onboarding focused on portable local file mounts, Docker/Dokploy/deployer secrets, environment variables, external vault/provider integrations allowed by their terms, and manual handling
  - update instance Git onboarding so credential handoff remains generic and does not suggest that removed provider
  - update sanitized secret-provider defaults template to use /run/secrets local file mounts
  - add Improvement Scout as a visible user-facing bSmart feature distinct from bSearch and Dreaming
  - add bundled bSelective prototype for MATLAB-first selective source-context retrieval
  - document bWorkflow and bSelective in the bundled extension manifest
safety:
  - avoids steering third-party bSmart users toward a provider whose terms may not permit the intended secret-management use
  - preserves the no-secret-values-in-Git/docs/logs/chat boundary
verification:
  - searched bSmart-System for removed provider references after edit
  - read back State and Dreaming protocol edits and verified the admin instance still records its host label in bSmart_State.md
  - verified the feature registry now lists Improvement Scout and describes its source-list/proposal workflow
  - bSelective unit tests pass in both packaged and installed extension copies
  - exercised bSelective CLI against a temporary MATLAB class for summary and exact method-source retrieval
```

## 0.1.10-draft

```yaml
release_type: draft_update
scope:
  - add generic secret-provider onboarding protocol for local mounts, deployer secrets, environment variables, external vaults, and manual handling
  - add sanitized example defaults templates for instance Git and secret-provider setup
  - add generic instance Git onboarding protocol that separates no Git, local Git, existing remote, and create/request remote flows from auth choices
  - allow instance-local defaults files to suggest repo/provider/auth values without hardcoding those values into public bSmart-System
  - let instance Git onboarding hand off to secret-provider onboarding when Git credentials are needed and no provider is configured yet
  - strengthen public-system neutrality: no hardcoded operator GitHub user, organization, repo pattern, host path, token name, SSH key name, endpoint, or secret value in reusable bSmart-System docs
safety:
  - secret values remain excluded from bSmart-System, bSmart content, project folders, logs, workdocs, and chat
  - instance defaults may be committed only when they contain no secret values or sensitive endpoint details
verification:
  - new protocol files written and linked from bSmart.md, bSmart_Setup.md, and README.md
```

## 0.1.9-draft

```yaml
release_type: draft_update
scope:
  - update README top-level presentation with bSmart definition, linked feature overview, setup procedure, install flow, and feature detail sections
  - add progressive help contract for `/new` greeting and keyword/number drill-down behavior
  - expose help/info/features commands in the feature registry display rules
  - add Dreaming as an opt-in bSmart feature/protocol for scheduled instance-local content cleanup, conflict detection, token-saving compaction, hidden backups, review/undo manifests, Dream Project, and Nap handoff
  - clarify that Dreaming affects instance content (`/workspace/bSmart`), not reusable bSmart-System (`/workspace/bSmart-System`)
  - allow clear low-risk Dreaming changes to be auto-applied only with hidden backups, while unclear/project/destructive/system/runtime changes require operator review
  - document Daily Dreaming defaults for low-token recent-session content review around 04:00 in the operator's local timezone
  - document Weekly Dreaming defaults for broader Friday-night/Saturday stale/conflict/compaction review with bounded token use
  - add Security Watch as an opt-in/admin-owned bSmart feature and protocol for low-noise read-only VPS/container drift checks
  - clarify the minimal manual bSmart bootstrap shape and strengthen the HERMES.md hook so agents actually load bSmart.md before answering
  - add compact sensitive-action expansion for bSmart pre-action notes: only sensitive/approval-likely actions get a short meaning/risk/approval-scope hint, while routine notes stay brief
  - clarify GitHub AI runtime pattern: export GIT_SSH_COMMAND in container env for normal git operations, keep GH_TOKEN file-based per command by default, and look in local bSmart docs for instance-specific implementation details before proposing setup
  - make startup/storage helper scripts infer workspace/content roots from their own bSmart-System checkout, so they work from VPS /workspace and local AGENTS.md workspaces
  - document CIFS/SMB executable-bit pitfall and prefer python3 <script> invocations for bSmart Python helpers
  - replace Hermes-specific startup wording with framework-neutral "bSmart — Loading bSmart."
  - add local path-resolution guidance so local AGENTS.md agents map /workspace/bSmart-System to ./bSmart-System and /workspace/bSmart to ./bSmart
  - make project listing explicitly use the selected project root and report setup_required when no supported root is usable
  - add portable sandbox-root selection for local/non-container agents: BSMART_SANDBOX_ROOT, then /sandboxes, then ./sandboxes, then ./bSmart/Sandboxes
  - add portable project-root selection for local/non-container agents: BSMART_PROJECT_ROOT, then /projects, then ./projects
  - add scripts/bsmart-bootstrap-workspace as the streamlined host-side initializer for new bSmart-enabled AI workspaces
  - document that all newly initialized AI agents should run bSmart by default
  - clarify that bSmart-System must live as a workspace Git checkout, not as stale image-baked content
  - allow images/start wrappers to include only a tiny first-run bootstrap hook that fetches the live workspace helper
  - standardize new-agent Compose defaults: working_dir=/workspace, TERMINAL_CWD=/workspace, HERMES_WRITE_SAFE_ROOT=/opt/data:/workspace:/projects:/sandboxes
  - separate bSmart-System Git from optional instance/content Git to avoid setup ambiguity

  - make same-day bSmart-System update throttling explicit: if --auto-pull is skipped because startup already ran today, print the exact --force --auto-pull command and document when to use it

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
  - use sudo install -d with the container uid and gid and mode 0775 for host sandbox folders
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
  - use /projects as the canonical container project root, with local ./projects for local agents
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
  - prefer deployer-native read-only secrets or <host-secrets-path> mounted as /run/secrets:ro
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
  - show user-facing news for versions flagged since this instance last updated
  - ask operator approval
  - git pull or checkout approved version
  - run bSmart doctor/check
  - report whether content migration is optional or required
constraints:
  - never overwrite /workspace/bSmart content automatically
  - never edit /opt/data/SOUL.md automatically
  - keep HERMES.md minimal
```
