# bAccountant

Optional bSmart feature that gives an agent an accountant-oriented role and connects it to accounting software.

## Initial integration

- Tripletex through MCP.

## Safety baseline

- Disabled by default.
- Read-only mode is the default and overrides all other modes.
- Every accounting-program interaction is logged.
- Uncertainty means ask; fail closed on errors, stale data, missing audit records, or ambiguous results.
- No change to existing accounting without explicit human approval.
- Salary mode prepares only; it never executes or submits payroll.
- Bookkeeping mode handles only approved unprocessed vouchers (`bilag`).

## Onboarding

Follow [`bAccountant-onboarding.md`](../../bSmart_Protocols/bAccountant-onboarding.md). Ask one question at a time. Use selectable options where practical, put the recommended option first, explain why briefly, and allow a custom answer or postponement.

Onboarding has two stages:

1. **Initial stage:** identity, country, business, accounting bureau, division of labour, Tripletex connection, permissions, modes, and safety preferences.
2. **Later stage:** research and confirm country-specific law, accounting procedures, and especially VAT rules, based on the collected business context.

Tripletex capabilities should be checked before implementing duplicate features.
