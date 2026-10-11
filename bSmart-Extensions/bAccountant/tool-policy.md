# bAccountant v1 tool policy (read-only, default deny)

The official Tripletex MCP server exposes many tools, including write, approval, sending and filing tools, and the list changes with each release. bAccountant v1 therefore uses **default deny**: a tool is enabled only after it has been recorded and reviewed as read-only and outside the sensitive domains.

Tool names must be **confirmed on first connect**. Names mentioned below as examples come from Tripletex's public release notes and may change; the recorded inventory is authoritative for an instance.

## 1. Enforcement layers

Use all that the client offers; prompts alone are not enforcement.

1. **Client tool controls** (primary): switch off or deny every non-allowlisted tool (Cursor per-tool toggles; Claude Code `permissions.deny` with `mcp__<server>__<tool>`; equivalent elsewhere).
2. **Tripletex user rights**: the server acts with the signed-in user's rights. Fewer rights means less exposure. Do not create shared or bot users to achieve this.
3. **Agent instructions** (`agent-instructions.md`): the agent refuses write and sensitive requests even if a tool is reachable.
4. **Logging**: every tool call is logged, so a policy breach is visible.

## 2. Always denied in v1

Deny regardless of name details:

| Category | Recognise by | Why |
|---|---|---|
| Writes of any kind | verbs such as create, update, delete, execute, set, register, upload, link, post, invoice, credit, order (as a verb), withdraw | v1 is read-only |
| Sending, approving, filing | send, submit, approve, unapprove, reject, remind, deliver | legally binding actions |
| Payroll and salary | salary, wage, payslip, payout, payroll, tax card, A-melding, holiday balance, hourly rate, month overview with payout controls | salary data out of scope |
| Employees and HR | employee, employment, HR, occupation code | personal data and national ID numbers |
| Expenses and travel | expense, travel expense, mileage, per diem, receipt | employee personal data |
| Hours | hour entries, timesheet, week approval | employee data, many are writes |
| Script mode | the run-script tool (for example `tripletex_run_script`) | runs many calls in one step and can reach other tools, which bypasses per-tool blocking |
| Client accounts | create/link client account, pricing for client accounts, list client administrators | accounting-office functions, not in scope |
| Feedback | the feedback tool (for example `submit_feedback`) | content may be reused by Tripletex; risk of leaking data |
| Payment set-up | outgoing payment types and similar | financial services are restricted by the developer terms |

## 3. Candidates for the allowlist (only after review)

Read tools in non-sensitive domains, typically with verbs get, search, list, fetch, query:

- ledger postings and open postings search;
- balance sheet and standard reports (with care: some reports break figures down per employee; do not request those);
- customer and supplier invoice search and details;
- customer and supplier lookup (records may contain sole traders' personal data: minimise what is shown and logged);
- accounting period status, accounting dimensions, departments;
- logged-in user info and current date/time helpers (needed to verify identity and company).

If the server exposes MCP tool annotations (`readOnlyHint`, `destructiveHint`), record them, but do not rely on them alone.

## 4. First-connect recording procedure

Done once per instance after the first sign-in, and again after each Tripletex release that adds tools:

1. Before using any tool, keep every Tripletex tool **switched off** (or set the client to ask before each call).
2. Export or copy the tool list the client shows: name, description, and annotations if shown.
3. Copy `templates/tool-inventory.template.md` into the instance's own data area (for example `<project>/data/tripletex-mcp/tool-inventory.md`) and fill one row per tool.
4. Classify each tool: `allow` (read-only, not sensitive), `deny` (write, sensitive or unclear), or `review` (needs a human decision). Unclear means deny.
5. Have the operator confirm the classification. Record the date, the server release (from the release notes) and who confirmed.
6. Apply the result in the client (toggles or deny rules). Re-check the client shows only allowlisted tools as enabled.
7. Record whether the client supports per-tool switching. If it does not, stop and report; do not use that client for v1.
8. Only then run the first starter task (`starter-tasks.md`, task 0).

## 5. Ongoing

- Check the release notes before each working period. New tools are denied until classified.
- If a tool's behaviour turns out to differ from its classification, move it to `deny` and note why.
