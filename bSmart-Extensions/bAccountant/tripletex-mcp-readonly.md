# bAccountant v1 protocol: read-only access through the official Tripletex MCP

Status: draft v1. Scope: **read-only**. Applies to any agent harness and operating system.

This is a practical protocol, not legal advice. The authoritative sources are Tripletex's own documentation and the terms the account admin accepts; link to them, do not copy them.

## 0. Guided initialization

To set bAccountant up for an agent, follow the step-by-step flow in `init-flow.md`: a privacy and responsibility warning, then admin enables the beta, add the server in the client the onboarding is running in, sign in, switch tools off, review the tool list, enable approved read tools, and verify. The flow is resumable and can be aborted at any step. The sections below are its reference material.

## 1. What v1 does

- Connects an agent's MCP client to the **official, Tripletex-hosted** MCP server so the agent can **read** accounting data and answer questions about it (balances, ledger postings, invoices, reports).
- Logs every interaction with the accounting system (see `templates/session-log.template.md`).
- Gives the operator a controlled way to learn what the server offers before any write capability is considered.

v1 does **not**:

- create, change, delete, approve, send, submit or file anything;
- touch payroll, employees, salary, tax cards, A-melding, tax returns or national identity numbers;
- run its own Tripletex integration code (the server is Tripletex's; bAccountant v1 only adds policy, instructions and logging around it);
- use community or third-party MCP servers for Tripletex.

## 2. Facts about the server

| Item | Value |
|---|---|
| Endpoint | `https://mcp.tripletex.no` (remote only; no local install, no published server source) |
| Transport | MCP streamable HTTP |
| Authentication | OAuth sign-in through Visma Connect with the user's own Tripletex login. No API tokens to create or store. The client receives a time-limited access token tied to that user; when it expires the user signs in again. |
| Permissions | Exactly the signed-in Tripletex user's own rights. There is no separate read-only scope known at the time of writing; check this on first connect. |
| Accounts | Live (production) accounts only. The Tripletex test environment is **not** reachable through the MCP server; test against the REST test API instead. |
| Cost | Free during the beta; pricing may apply at general availability. |
| Release notes | Public release notes: https://github.com/Tripletex/tripletex-mcp/releases (watch them: new tools, including write tools, are added often). |
| Official docs | https://developer.tripletex.no/tripletex-mcp-beta/ and the Tripletex help centre. |

Important: the server's toolset is large and **includes write and filing tools** (for example sending invoices, approving hours, submitting A-melding). Read-only is therefore something bAccountant must enforce on the client side; the server does not enforce it.

## 3. Prerequisites (done by humans, never by the agent)

1. **Decision recorded** in the project: which Tripletex company, which human user signs in, which AI client and plan, and the accepted data-protection position (with or without a data-processing agreement for the AI chain).
2. **Admin enables the beta**: a Tripletex account administrator turns on *Tripletex MCP (beta)* under *Company > My subscription > Integrations* and accepts the MCP terms. The agent must not do this.
3. **Signing user**: a named person signs in with their own Tripletex login. No shared logins, no "bot user" accounts, no passwords given to an agent.
4. **Client prepared**: the AI client's tool controls are understood (how to switch individual tools off or deny them) **before** the first sign-in.
5. **Only trusted MCP servers in the same session**: remove or disable untrusted MCP servers in the client while Tripletex is connected (exfiltration risk named in the MCP terms).

## 4. Connecting, per client

Add the Tripletex MCP server in the agent framework or client the onboarding is running in. If onboarding runs in Codex, add it in Codex. If it runs in a Grok Bot agent, add it there as a connector. Do the same for any other client: add the server there.

All clients use the same URL and the same browser sign-in. Choose a server name such as `tripletex`; it becomes the prefix of tool names in some clients. Never put credentials or tokens into these files: the sign-in handles that.

The snippets below are examples, not a recommendation. No client is the default. If the client the onboarding is running in is not listed (Codex and a Grok Bot agent included), follow Generic MCP client.

### Generic MCP client

Any client that supports MCP streamable HTTP with OAuth (dynamic client registration) can connect to `https://mcp.tripletex.no`. Clients Tripletex does not recognise show an extra "do you trust this client" step at sign-in. The client must allow per-tool blocking, or the operator must place a filtering proxy in front of it; otherwise do not use it for v1.

### Claude (web/desktop) and ChatGPT

Add a custom connector / remote MCP server with URL `https://mcp.tripletex.no` and OAuth authentication, complete the sign-in, and use that client's per-tool controls if it has them. If it cannot switch individual tools off, do not use it for bAccountant v1.

### Claude Code

```bash
claude mcp add --transport http tripletex https://mcp.tripletex.no
```

Then run `/mcp` inside Claude Code and complete the sign-in. Enforce the denylist with permission rules in Claude Code settings, for example:

```json
{
  "permissions": {
    "deny": [
      "mcp__tripletex__<write-or-sensitive-tool-name>"
    ]
  }
}
```

Add one entry per denied tool from the recorded inventory (see `tool-policy.md`). Keep "ask before running" on for the remaining Tripletex tools until the inventory is reviewed.

### Cursor

Project-level (`<project>/.cursor/mcp.json`) or user-level (`<user-config-dir>/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "tripletex": {
      "url": "https://mcp.tripletex.no"
    }
  }
}
```

Then open Cursor's MCP settings, start the sign-in for `tripletex`, complete the Visma Connect login in the browser, and **before first use** switch off every tool that is not on the allowlist (Cursor lists each tool of a server with its own toggle).

## 5. Tool policy (summary)

Default deny. Only tools explicitly reviewed as read-only **and** outside the sensitive domains are enabled. Full rules, sensitive domains and the first-connect recording procedure: `tool-policy.md`.

## 6. Privacy checklist (before every working session)

- [ ] The client session has only trusted MCP servers enabled.
- [ ] Only allowlisted Tripletex tools are enabled; script mode and all write, payroll, employee and client-account tools are off.
- [ ] The session is scoped to one company (the one recorded in the project).
- [ ] The request does not ask for employee, salary, payslip, tax card, A-melding, tax return or national ID data.
- [ ] Ledger and report queries exclude personnel-cost and payroll accounts unless the operator explicitly approved otherwise.
- [ ] Results kept in logs are minimised: no copied personal data, no full customer or supplier lists, no national ID numbers, no tokens.
- [ ] The AI client's privacy settings match the recorded decision (for example privacy mode on, no training on data).
- [ ] Nothing from Tripletex is sent as "feedback" to Tripletex or to the AI provider.

If any box cannot be ticked, do not start the session.

## 7. Health and failure handling

- Sign-in expired, permission errors, partial results, timeouts or a read-only/suspended account: stop, report to the operator, do not retry in a loop.
- A tool appears that is not in the recorded inventory: treat it as denied until reviewed.
- The agent can reach data it should not: stop, report to the operator (who decides whether to report to Tripletex).

## 8. Disconnect and revoke

Do all three when the experiment ends, when the client is unused for a while, or immediately if anything looks compromised:

1. **In the client**: remove or disable the `tripletex` MCP server (Cursor: delete the entry from `mcp.json` or switch the server off; Claude Code: `claude mcp remove tripletex`; other clients: remove the connector).
2. **In Visma Connect**: remove the access token for the MCP client under the account's connected apps/sessions at https://accountsettings.connect.visma.com/.
3. **In Tripletex (optional, admin)**: switch *Tripletex MCP (beta)* off under *Company > My subscription > Integrations* if nobody in the company should use it.

Record the date of disconnect in the project's own log.

## 9. Path to write capability (not in v1)

Writes are legally significant: invoices, payments and public filings created through Tripletex are binding. Any later write mode needs, at minimum: a recorded decision, a data-processing agreement covering the AI chain, per-item human approval bound to an exact preview, an audit trail, and a rollback or correction routine. See `agent-instructions.md` section 6.
