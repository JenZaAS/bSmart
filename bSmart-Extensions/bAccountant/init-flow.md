# bAccountant v1 guided initialization (read-only Tripletex MCP)

Run this flow whenever a user asks to initialize, set up or connect bAccountant for an agent. It is part of `tripletex-mcp-readonly.md` and follows the rules in `agent-instructions.md`.

## Rules for the flow

- **One step at a time.** Explain the step, say who does it (user, admin or agent), then wait for the user to confirm it is done before moving on. Never do two steps in one turn.
- **Humans act in Tripletex, Visma Connect and the client's sign-in.** The agent only explains, checks and records. It never enables anything in Tripletex, never handles passwords or tokens, and never adds the server to a client unless the user explicitly asks it to and the client allows it.
- **Warning first.** Always show the step 0 warning at the start of initialization (also when resuming after a change of client, plan or company). It is information only; the user does not have to accept it to continue.
- **Record as you go.** Keep progress in the instance's own data area: `<project>/data/tripletex-mcp/init-record.md` (copy from `templates/init-record.template.md`). Record dates and statuses only; no personal data, tokens or accounting data.
- **Resumable.** On start, read the init record and continue at the first step not marked `done`. Where possible, re-check reality rather than trusting the record (for example: is the server present in the client, does the tool list match the inventory). If the record and reality disagree, tell the user and redo the affected step.
- **Abortable.** If the user says stop, abort or cancel at any point: stop immediately, mark the current step `aborted` with the date, list what was already done, and offer the undo steps (`tripletex-mcp-readonly.md` section 8: remove the server from the client, revoke the token in Visma Connect, optionally switch the beta off). Never continue an aborted flow without the user asking to resume.

## Step 0 - Privacy and responsibility warning (show, then continue)

Show this warning in full and clearly marked as a warning. Then continue with step 1 when the user is ready. Optionally record in the init record that it was shown, with the date.

> **WARNING - read before connecting your accounting data to an AI tool**
>
> 1. **Your data goes to your AI provider.** Everything the agent reads from Tripletex (balances, postings, invoices, reports) is sent to the AI tool you use and its model provider. Whether a data-processing agreement (DPA) covers this depends on your plan. Some providers offer no DPA on individual or personal plans (for example, Cursor's individual plans have none), while team or business plans may include one. Without a DPA, your account data is processed by that provider without the contractual protections a DPA gives.
> 2. **Keep salary and ID data out.** Salary data and national identity numbers (for example the Norwegian fodselsnummer and D-number) must be kept out wherever possible. bAccountant v1 switches off payroll and employee tools and will not ask for this data, but some reports or postings can still contain it.
> 3. **Invoices and ledgers contain personal data too.** Names, email addresses, phone numbers and other details of customer and supplier contacts (and of sole traders) are personal data under the GDPR, even when they appear inside invoices or ledger postings.
> 4. **The legal responsibility is yours.** Making sure there is a valid legal basis for this processing (GDPR, a DPA with the AI provider where needed, transfers outside the EU/EEA, and the Tripletex/Visma terms) is the responsibility of you and your company. It is **not** the responsibility of bSmart or of this agent, and neither gives legal advice or any assurance of compliance.
> 5. **Read-only, and you can stop at any time.** This setup is read-only. You can abort now or later, and disconnect and revoke access whenever you want.

Warning version: 1 (2026-10-11).

## Step 1 - Admin enables the beta (admin, in Tripletex)

A Tripletex account administrator turns on **Tripletex MCP (beta)** under **Company > My subscription > Integrations** and accepts the MCP terms. Ask the user to confirm it is done (record only that it was confirmed, not account details).

## Step 2 - Add the server in the client (user)

Add `https://mcp.tripletex.no` as a remote MCP server named `tripletex` in the AI client, using the snippet for that client in `tripletex-mcp-readonly.md` section 4. Disable any MCP servers the user does not fully trust for sessions where Tripletex is enabled. Confirm before continuing.

## Step 3 - Sign in (user)

The user starts the client's sign-in for `tripletex` and logs in through Visma Connect **with their own Tripletex login**. The agent never sees or asks for the password. Confirm the sign-in completed.

## Step 4 - Switch tools off (user, guided by the agent)

Before any tool is used, switch off all Tripletex tools in the client, or at minimum every write, sending, approval, payroll, employee and script tool (see `tool-policy.md` section 2). If the client cannot switch individual tools off, stop the flow here and record why.

## Step 5 - Record and review the tool list (agent and user together)

Follow `tool-policy.md` section 4: copy the tool list into `<project>/data/tripletex-mcp/tool-inventory.md`, propose a classification (`allow` / `deny` / `review`), and go through it with the user. The user confirms the final classification.

## Step 6 - Enable approved read tools only (user)

The user enables only the tools classified `allow`. The agent asks the user to confirm that everything else stays off.

## Step 7 - Verify (agent)

Run starter task 0 (`starter-tasks.md`). It passes when the signed-in user and the company are the expected ones and only `allow` tools are enabled. On pass, record the completion date in the init record and create the first session log entry. On failure, record what failed and go back to the relevant step.

Initialization is complete when steps 1-7 are `done` (step 0 only needs to have been shown).
