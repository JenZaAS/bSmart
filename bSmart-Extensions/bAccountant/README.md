# bAccountant

Optional bSmart feature that gives an agent an accountant-oriented role and connects it to accounting software.

Status: v1, read-only. Disabled by default.

## Initial integration

- Tripletex, through the official Tripletex-hosted MCP server (`https://mcp.tripletex.no`), read-only.
- This folder contains **no Tripletex integration code**. v1 is protocol, policy, agent instructions, task templates and record templates around the official server. Any future adapter code for Tripletex must be written solely in-house by the maintainers; do not copy community MCP servers or other third-party Tripletex code into it, and treat outside contributions to an adapter with care, because the Visma/Tripletex customer terms claim rights in integration technology that was not developed solely by the customer.

## Safety baseline

- Disabled by default.
- Read-only mode is the default and overrides all other modes. v1 is read-only only.
- Every accounting-program interaction is logged.
- Uncertainty means ask; fail closed on errors, stale data, missing audit records, or ambiguous results.
- No change to existing accounting without explicit human approval.
- Salary mode prepares only; it never executes or submits payroll.
- Bookkeeping mode handles only approved unprocessed vouchers (`bilag`).
- No legal assurance: bSmart and the agent never claim that a setup is legally compliant. The legal basis for processing accounting data with an AI tool is the user's and their company's responsibility.

## v1 files

| File | Purpose |
|---|---|
| `tripletex-mcp-readonly.md` | Protocol: what v1 does, read-only scope, prerequisites, how to connect per client, privacy checklist, disconnect and revoke. |
| `init-flow.md` | Guided, resumable step-by-step initialization, starting with a privacy and responsibility warning. |
| `tool-policy.md` | Default-deny tool policy: how tools are classified, what is always blocked, how the real tool list is recorded on first connect. |
| `agent-instructions.md` | Rules for the accountant agent: never write, never request salary or ID data, fail closed, approval rules for future writes. |
| `starter-tasks.md` | Generic read-only task templates to exercise the connection. |
| `templates/tool-inventory.template.md` | Record of the tool list an instance actually sees. |
| `templates/init-record.template.md` | Initialization progress record. |
| `templates/session-log.template.md` | Per-session interaction log. |

Filled copies of the templates belong in the instance's or project's own data area (for example `<project>/data/tripletex-mcp/`), never in this folder. Keep this folder data-neutral: no personal data, company names, organisation numbers, account data, user-specific settings, agent names or real paths.

## Onboarding

Follow [`bAccountant-onboarding.md`](../../bSmart_Protocols/bAccountant-onboarding.md). Ask one question at a time. Use selectable options where practical, put the recommended option first, explain why briefly, and allow a custom answer or postponement.

Onboarding has two stages:

1. **Initial stage:** identity, country, business, accounting bureau, division of labour, Tripletex connection, permissions, modes, and safety preferences. The Tripletex connection itself is set up with [`init-flow.md`](init-flow.md).
2. **Later stage:** research and confirm country-specific law, accounting procedures, and especially VAT rules, based on the collected business context.

Tripletex capabilities should be checked before implementing duplicate features.
