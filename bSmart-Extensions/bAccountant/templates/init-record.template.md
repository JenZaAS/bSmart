# bAccountant initialization record (instance record)

Copy into the instance's or project's own data area (for example `<project>/data/tripletex-mcp/init-record.md`). Record dates and statuses only. Never record tokens, passwords, accounting data or personal data.

Statuses: `pending`, `done`, `failed`, `aborted`, `skipped (reason)`.

- AI client and plan type: <client; individual / team / business>
- DPA in place for that plan: <yes / no / unknown>

| Step | Description | Status | Date | Notes |
|---|---|---|---|---|
| 0 | Privacy and responsibility warning shown (warning version: <n>) | pending | | optional record |
| 1 | Admin enabled Tripletex MCP (beta) and accepted terms | pending | | |
| 2 | Server added in the client | pending | | |
| 3 | User signed in via Visma Connect with own login | pending | | |
| 4 | All / write tools switched off | pending | | |
| 5 | Tool list recorded and reviewed (`tool-inventory.md`) | pending | | |
| 6 | Only approved read tools enabled | pending | | |
| 7 | Starter task 0 passed | pending | | |

Initialization complete: <date or "no">

## Aborts and changes

- <date>: <what happened, e.g. aborted at step N; client, plan or company changed and warning shown again>
