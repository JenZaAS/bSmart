# bSmart map

```yaml
map:
  name: bSmart_Map
  scope: bSmart logical storage and file ownership
  status: active
  path_model: relative_to_bsmart_workspace_root
  detail_lookup: python ./scripts/bMap <scope> <item>
  scopes:
    system: Generic bSmart-System map.
    instance: Instance map at ./bSmart/bSmart_InstanceMap.md when present.
    project: Project map at ./projects/<project>/bSmart_ProjectMap.md when present.
  rule: This map describes logical locations and ownership, not physical mounts.
  output: Return only the matching heading or map row plus scope and map path.
```

## Purpose

This is the authoritative logical map of the bSmart software, instance, project, runtime, and reference-information boxes. It may contain detailed file-level entries so deterministic tools can retrieve one named item without exploratory searching.

Physical storage details—Docker mounts, network shares, volumes, and host paths—belong in the instance map or runtime configuration. They must make the logical paths below available without changing the bSmart model.

## Map hierarchy

```text
bSmart-System/bSmart_Map.md
  Generic bSmart-System layout and file ownership.

./bSmart/bSmart_InstanceMap.md
  Instance-specific mapping of content, runtime, and storage.

./projects/<project>/bSmart_ProjectMap.md
  Project-specific mapping of files, components, tools, and relationships.
```

When the user says “the map” while working in a project, use that project’s `bSmart_ProjectMap.md`. Read the complete project map during that focused task; do not load it as general startup context.

## Logical roots

| Logical path | Ownership | Purpose | Default loading |
|---|---|---|---|
| `./bSmart-System` | system | Generic bSmart software | selected startup entries |
| `./bSmart` | instance | Instance-specific content and configuration | selected startup entries |
| `./projects` | project | Durable project source and project context | selected project |
| `./sandboxes` | derived/runtime | Disposable build, test, cache, and worktree material | task-dependent |

These are logical paths. A runtime may implement them as ordinary folders, mounts, volumes, or symlinks.

## bSmart-System map

| Path | Purpose | Volatility | Loading |
|---|---|---:|---|
| `./bSmart-System/bSmart.md` | Short conceptual definition of bSmart and its major boxes | low | startup |
| `./bSmart-System/bSmart_Invariants.md` | Absolute cross-runtime bSmart rules | low | startup |
| `./bSmart-System/bSmart_Map.md` | This logical system map | low | bStart routing |
| `./bSmart-System/bSmart_Features.md` | Compact feature summaries and detail lookup metadata | low | compact startup |
| `./bSmart-System/bSmart_Version.md` | System version and changelog | low | metadata check only |
| `./bSmart-System/bSmart_Setup.md` | Setup and repair procedure | low | setup only |
| `./bSmart-System/bSmart_Protocols/` | Detailed operational protocols | low | need to know |
| `./bSmart-System/bSmart_Templates/` | Templates for instance and project files | low | generation only |
| `./bSmart-System/bSmart-Extensions/` | Optional and bundled feature implementations | low | feature use only |
| `./bSmart-System/integrations/` | Runtime-specific adapters | low | active runtime only |
| `./bSmart-System/scripts/` | Deterministic helper programs and lookup tools | low | execution only |
| `./bSmart-System/tests/` | System validation | low | explicit testing only |
| `./bSmart-System/bSmart_Docs/` | Human-facing system documentation | low | explicit request only |

Instances may read bSmart-System but must not modify it during normal operation.

## Instance map

The instance map is expected at:

```text
./bSmart/bSmart_InstanceMap.md
```

It should describe only this instance’s mapping of:

- `bSmart_Agent.md`;
- `bGuardrails.md`;
- roles and role state;
- instance tasks, logs, history, and workdocs;
- instance configuration and runtime integration;
- actual project and sandbox mappings;
- enabled optional features.

It must not duplicate generic system procedures or contain secrets.

## Project map

A project map is expected at:

```text
./projects/<project>/bSmart_ProjectMap.md
```

It should describe only that project’s:

- source and documentation layout;
- project instructions and conventions;
- components and important files;
- project knowledge and workdocs;
- tools, interfaces, and external dependencies;
- build/test/runtime locations;
- project-specific guardrails.

## Standard project entries

| Path | Purpose | Loading |
|---|---|---|
| `./projects/<project>/project.md` | Project identity, objective, status, and agent focus | selected project |
| `./projects/<project>/bSmart_ProjectMap.md` | Detailed project map | map lookup or focused project-map task |
| `./projects/<project>/AGENTS.md` | Project/client-specific instructions | selected project |
| `./projects/<project>/knowledge/` | Project-specific reusable knowledge | relevant task only |
| `./projects/<project>/decisions.md` | Project decisions and approvals | relevant task only |
| `./projects/<project>/workdocs/` | Larger project work | relevant task only |
| `./projects/<project>/data/` | Supporting project material | relevant task only |
| `./projects/<project>/sandbox/` | Project-local derived material when required | task-dependent |

## Instance entries

| Path | Purpose | Volatility | Loading |
|---|---|---:|---|
| `./bSmart/bSmart_Agent.md` | Stable instance identity and access model | low | startup summary |
| `./bSmart/bGuardrails.md` | Editable instance-level behavior and preferences | medium | startup |
| `./bSmart/Roles/` | Named work roles and focus state | high | selected role |
| `./bSmart/bSmart_State.md` | Temporary compatibility/default state during migration | high | compatibility only |
| `./bSmart/bSmart_TODO.md` | Instance-level current/open tasks | high | general role only or request |
| `./bSmart/bSmart_Log.md` | Instance decision/action log | high | explicit request only |
| `./bSmart/bHistory.md` | Concise completed-work history | medium | explicit request or handoff |
| `./bSmart/Workdocs/` | Instance-level larger work | high | relevant task only |
| `./bSmart/Library/` | Instance-wide reusable knowledge | medium | bKnowledge lookup |
| `./bSmart/State/` | Instance configuration and machine/runtime state | high | bStart/tools as required |

## Loading policy values

```text
startup              required for every new session
compact_startup      summary or metadata only
selected_role        only the active role
selected_project     only the active project
feature_on_demand    only when the feature is relevant
need_to_know         only when the task requires it
explicit_request     only when the user asks
execution_only       run the script; do not load its source as context
never_automatic      never load during normal startup
```

## Deterministic lookup tools

The compact startup result should tell the agent which lookups are available:

```text
python ./scripts/bMap <scope> <item>
python ./scripts/bFeature <feature-name>
python ./scripts/bKnowledge <query>
```

The exact interfaces are defined by their respective features. Lookup tools should return only the requested entry or a compact relevant result.
