# bSmart Startup

This workspace may be shared by Codex on the host and OpenCode in Docker. Before
handling user input, identify the runtime and resolve paths accordingly:

- Docker: if `/.dockerenv` exists, use `/workspace` as the workspace root.
- Host: use the directory containing this file as the workspace root.
- Projects: use a usable `BSMART_PROJECT_ROOT` if set; otherwise use `/projects`
  in Docker or `<workspace>/projects` on the host.
- Sandboxes: use a usable `BSMART_SANDBOX_ROOT` if set; otherwise use
  `/sandboxes` in Docker or `<workspace>/sandboxes` on the host, but only if the
  directory exists. Do not create one without approval.

Verify paths before using them. When bSmart documents refer to `/workspace/...`,
map those references to the resolved workspace paths above.

Do not modify `bSmart-System` by default. Report any required system changes and
wait for explicit operator approval before editing that repository.

Read `<workspace>/bSmart-System/bSmart.md` immediately and follow its startup
sequence before responding. This includes reading `bSmart_Agent.md`,
`bSmart_State.md`, `bSmart_TODO.md`, and relevant protocols.

The first response must start with `bSmart — Loading bSmart.`, then say
`Hi! Welcome back.`, report Mode, active project, and current workstream when
present, include `Info keywords: help, features, setup, projects, tasks, safety.`,
and ask whether to continue the current TODO item.
