# Shared /project command runtime

The portable, Node-stdlib implementation is `scripts/bsmart-project-core.mjs`.
Both agent-chat adapters and Electron must call this engine, not duplicate command logic.

The engine receives `projectsRoot`, `archiveRoot`, and `home`. Optional `session` is `{project, workstream}` for this call only. The engine does not read or write `Roles/current_role.md`. Optional `context.sessionId` stores that session's selection in `home/State/sessions/<id>.json` so a stateless harness can continue one conversation; bStart never reads those files, and one id is never used as another session's selection. Pass `handoff` when leaving a project. `bSmart_State.md` is not read by project commands; role migration is `bsmart-instance-upgrade`.

## API and transport

```js
import { execute } from './scripts/bsmart-project-core.mjs';
const context = {
  projectsRoot: '/explicit/projects',
  archiveRoot: '/explicit/archives',
  home: '/explicit/home'
};
execute({command: '/project list', context, session: {project: null, workstream: null}});
// {status:'ok', projectsRoot:'/explicit/projects', projects:[{name,path,kind:'bsmart'|'plain'}], diagnostic:...}
execute({command: '/project Example', context});
// {status:'ok', selection:{project:'Example',workstream:null}, diagnostic:...}
const result = execute({command:'/project rename NewName', context});
// {status:'pending',pending:{id,operation,project,target,newName,expiresAt,choices:['yes','no']},diagnostic:...}
execute({command:'/project yes',context,confirmation:{id:result.pending.id,answer:'yes'}});
// Alternative durable CLI continuation: command:'/project yes UUID' (or no UUID).
```

`execute` is synchronous and returns `status: ok|pending|cancelled|error` and a human-readable `diagnostic`. Retire success additionally returns `archivePath`. Selection is canonical state, not an adapter-local preference. Errors do not throw across the public API.

CLI: `node scripts/bsmart-project.mjs '<JSON request>'`, or pipe one JSON request to stdin. Exactly one JSON result is emitted on stdout; exit 1 for error, 0 otherwise. Paths must be explicitly resolved by the caller; no implicit live-project defaults. The projects root and the home directory used for pending confirmations must exist. Legacy `bSmart_State.md` is not a project-command input.

## Commands

- `/project help`: show the complete `/project` command list with short explanations.
- `/project`, `/project list`: active index rows. `/project list --all` includes archived rows.
- `/project NAME [WS]`: select a project in this session, optionally an existing workstream. Quote multiword names. Leaving another project requires a handoff note.
- `/project ws WS`: select an existing workstream of the session project.
- `/project free`: leave the session project after writing its handoff.
- `/project add NAME`: create the standard project skeleton, append an active index row, and select it in this session.
- `/project add ws WS`: create `workstreams/WS/README.md` and select it in this session.
- `/project label LABEL`, `/project describe TEXT`, `/project alias WORDS`: update the index row for the session project.
- `/project rename NEWNAME`: confirm, rename the exact session project and its index row.
- `/project retire`: confirm, verified full archive, mark the index row archived, enter Free mode.
- `/project delete`: confirm, remove the exact session project and its index row, enter Free mode.
- `/project index` and `/project index repair`: compare the index with folder names, then add lines for folders the index does not name.
- `/project yes ID` and `/project no ID` continue a pending operation across processes. The pending id names the project; it is not a selector for other sessions.
- `/role`: deprecation notice only. It does not change a project.

Selection resolution: exact spelling first, then unique case/punctuation normalization, then unique edit distance <=1 for normalized input length >=4. Ties and missing names are errors. Destructive commands never resolve fuzzy targets: they read the exact current selection and accept no target argument. Unsafe, reserved, traversal, symlink and colliding names are rejected.

## New retirement safety policy (not a legacy contract)

No older close/retire contract was identified in the shared protocols. This implementation introduces a conservative full-project archive outside projectsRoot, including all workdocs, knowledge, decisions and other contents. It copies into a fresh uniquely named archive and verifies directory/file inventories, file sizes and SHA-256 content hashes against both the approved manifest and source at that instant. This is byte/inventory verification, not an `fsync` durability guarantee or preservation of every ACL/xattr. Any copy/verification failure aborts source removal; a partial archive may remain for diagnosis. Symlinks and special files anywhere in a destructive target are rejected, not followed.

Rename/retire/delete first persist `.bsmart-project-pending.json` with mode 0600. Approval is bound to context paths, exact target identity, state bytes, complete content manifest and a five-minute expiry. A matching Yes/No consumes the record; stale/expired/replayed approvals fail. One outstanding prompt per home; a new prompt supersedes the previous one. Callers must render the explicit target and require a real user Yes/No; never auto-confirm. Delete/retire use a same-filesystem quarantine rename, commit canonical state, then remove quarantine; pre-commit failures roll back when possible. A post-commit cleanup failure remains `status: ok` with `cleanupWarning` and `quarantinePath`, rather than falsely reporting no change. Lock-cleanup failure likewise augments the operation result, while an original operation error remains primary. The index lock `projects/INDEX.md.bLock` serializes cooperating processes; after a crashed process, verify no operation is running before manually removing a stale `INDEX.md.bLock` file. Handoff writes use `handoff.md.bLock` the same way.

**Operational limits:** this is not an OS security boundary against concurrent uncooperative filesystem writers. Quiesce project writers for destructive operations. Hashing is chunked, but full hashing/copying may still be expensive, especially dependencies: Electron must spawn the CLI in a child process, never run this synchronous engine in its renderer or main event loop. Multi-file mutation is rollback-oriented but not fully crash-transactional; a process crash or failed rollback may need operator reconciliation. Archives verify bytes/inventory at verification time, not durability or all platform ACLs/xattrs. Do not test destructive actions on live projects.

## Verification

`node --test tests/test-project.mjs` uses isolated temporary projects and state only, including cross-process CLI confirmation. `python3 -m unittest tests/test_bsmart_project_plugin.py -v` verifies the Hermes adapter and real cross-process Yes/No continuation with temporary state. Workstream ownership and state shape are defined by [state.md](state.md).

## Hermes chat adapter

The upgrade-safe plugin package is `integrations/hermes/bsmart-project-plugin/`. Install it into the active Hermes profile with:

```sh
mkdir -p /opt/data/plugins/bsmart-project
cp integrations/hermes/bsmart-project-plugin/plugin.yaml integrations/hermes/bsmart-project-plugin/__init__.py /opt/data/plugins/bsmart-project/
```

The adapter resolves context only from `BSMART_PROJECT_ROOT`, `BSMART_STATE_FILE`, `BSMART_ARCHIVE_ROOT`, and `BSMART_SYSTEM_ROOT`, with the documented defaults; chat arguments cannot supply paths. It invokes the JSON CLI without a shell. The bSmart `/new` startup check installs and enables this managed adapter when missing, then reports that a new CLI session or gateway restart is needed for discovery.

## Cursor, Codex, and Claude adapters

These clients do not load the Hermes plugin. They call the same engines through `integrations/bsmart_client_adapter.py`, which sets trusted path variables and reuses the Hermes adapter. Chat arguments cannot supply paths.

| Client | Package | Invocation | Verification |
|---|---|---|---|
| Cursor | `integrations/cursor/bsmart-plugin/` | `/project`; `/role` is deprecated | enabled in this workspace from `.cursor/` |
| Codex | `integrations/codex/bsmart-plugin/` | `$bsmart-project`; `$bsmart-role` is deprecated | install from `.agents/plugins/marketplace.json` and trust the startup hook |
| Claude | `integrations/claude/bsmart-plugin/` | `/project`; `/role` is deprecated | not yet verified in the Claude app |

`python3 -m unittest tests/test_bsmart_client_plugins.py -v` checks the adapter, hook payload, manifests, and that the plugin hook script matches `integrations/client_session_start.py`.
