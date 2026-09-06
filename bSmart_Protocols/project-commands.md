# Shared /project command runtime

The portable, Node-stdlib implementation is `scripts/bsmart-project-core.mjs`.
Both agent-chat adapters and Electron must call this engine, not duplicate command logic.

## API and transport

```js
import { execute } from './scripts/bsmart-project-core.mjs';
const context = {
  projectsRoot: '/explicit/projects',
  stateFile: '/explicit/home/bSmart_State.md',
  archiveRoot: '/explicit/archives',
  home: '/explicit/home' // optional; pending storage otherwise beside stateFile
};
execute({command: '/project list', context});
// {status:'ok', projectsRoot:'/explicit/projects', projects:[{name,path,kind:'bsmart'|'plain'}], diagnostic:...}
execute({command: '/project Example', context});
// {status:'ok', selection:{project:'Example',workstream:null}, diagnostic:...}
const result = execute({command:'/project rename NewName', context});
// {status:'pending',pending:{id,operation,project,target,newName,expiresAt,choices:['yes','no']},diagnostic:...}
execute({command:'/project yes',context,confirmation:{id:result.pending.id,answer:'yes'}});
// Alternative durable CLI continuation: command:'/project yes UUID' (or no UUID).
```

`execute` is synchronous and returns `status: ok|pending|cancelled|error` and a human-readable `diagnostic`. Retire success additionally returns `archivePath`. Selection is canonical state, not an adapter-local preference. Errors do not throw across the public API.

CLI: `node scripts/bsmart-project.mjs '<JSON request>'`, or pipe one JSON request to stdin. Exactly one JSON result is emitted on stdout; exit 1 for error, 0 otherwise. Paths must be explicitly resolved by the caller; no implicit live-project defaults. Projects root and state/pending parent directories must exist. State basename must be `bSmart_State.md`.

## Commands

- `/project`, `/project list`: immediate non-hidden directories including plain folders; never recursively scan siblings.
- `/project NAME [WS]`: select project, optionally existing workstream. Quote multiword names.
- `/project ws WS`: select existing workstream of current project.
- `/project add NAME`: create the standard project skeleton and always select/open it.
- `/project add ws WS`: create `workstreams/WS/README.md` and select it.
- `/project rename NEWNAME`: confirm, rename exact current directory and project metadata, update canonical state.
- `/project retire`: confirm, verified full archive, remove current project, enter Free Mode.
- `/project delete`: confirm, remove exact current project without archive, enter Free Mode.
- `/projcet` is the explicit prefix alias. `/project yes ID` and `/project no ID` continue a pending operation across processes.

Selection resolution: exact spelling first, then unique case/punctuation normalization, then unique edit distance <=1 for normalized input length >=4. Ties and missing names are errors. Destructive commands never resolve fuzzy targets: they read the exact current selection and accept no target argument. Unsafe, reserved, traversal, symlink and colliding names are rejected.

## New retirement safety policy (not a legacy contract)

No older close/retire contract was identified in the shared protocols. This implementation introduces a conservative full-project archive outside projectsRoot, including all workdocs, knowledge, decisions and other contents. It copies into a fresh uniquely named archive and verifies directory/file inventories, file sizes and SHA-256 content hashes against both the approved manifest and source at that instant. This is byte/inventory verification, not an `fsync` durability guarantee or preservation of every ACL/xattr. Any copy/verification failure aborts source removal; a partial archive may remain for diagnosis. Symlinks and special files anywhere in a destructive target are rejected, not followed.

Rename/retire/delete first persist `.bsmart-project-pending.json` with mode 0600. Approval is bound to context paths, exact target identity, state bytes, complete content manifest and a five-minute expiry. A matching Yes/No consumes the record; stale/expired/replayed approvals fail. One outstanding prompt per home; a new prompt supersedes the previous one. Callers must render the explicit target and require a real user Yes/No; never auto-confirm. Delete/retire use a same-filesystem quarantine rename, commit canonical state, then remove quarantine; pre-commit failures roll back when possible. A post-commit cleanup failure remains `status: ok` with `cleanupWarning` and `quarantinePath`, rather than falsely reporting no change. Lock-cleanup failure likewise augments the operation result, while an original operation error remains primary. The state-side lock serializes cooperating processes; after a crashed process, verify no operation is running before manually removing a stale `.project-lock` file.

**Operational limits:** this is not an OS security boundary against concurrent uncooperative filesystem writers. Quiesce project writers for destructive operations. Hashing is chunked, but full hashing/copying may still be expensive, especially dependencies: Electron must spawn the CLI in a child process, never run this synchronous engine in its renderer or main event loop. Multi-file mutation is rollback-oriented but not fully crash-transactional; a process crash or failed rollback may need operator reconciliation. Archives verify bytes/inventory at verification time, not durability or all platform ACLs/xattrs. Do not test destructive actions on live projects.

## Verification

`node --test tests/test-project.mjs` uses isolated temporary projects and state only, including cross-process CLI confirmation. `python3 -m unittest tests/test_bsmart_project_plugin.py -v` verifies the Hermes adapter, both spellings, and real cross-process Yes/No continuation with temporary state. Workstream ownership and state shape are defined by [state.md](state.md).

## Hermes chat adapter

The upgrade-safe plugin package is `integrations/hermes/bsmart-project-plugin/`. Install it into the active Hermes profile with:

```sh
mkdir -p /opt/data/plugins/bsmart-project
cp integrations/hermes/bsmart-project-plugin/plugin.yaml integrations/hermes/bsmart-project-plugin/__init__.py /opt/data/plugins/bsmart-project/
```

The adapter resolves context only from `BSMART_PROJECT_ROOT`, `BSMART_STATE_FILE`, `BSMART_ARCHIVE_ROOT`, and `BSMART_SYSTEM_ROOT`, with the documented defaults; chat arguments cannot supply paths. It invokes the JSON CLI without a shell. Hermes user plugins are opt-in: if `hermes plugins list --plain --no-bundled` reports `bsmart-project` as disabled, an operator must explicitly run `hermes plugins enable bsmart-project` (which edits profile configuration). Existing Hermes processes are intentionally not restarted during installation: after enablement, start a new CLI session or restart the gateway later for plugin discovery.
