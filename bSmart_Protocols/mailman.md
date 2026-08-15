# bSmart Protocol: mailman

```yaml
protocol:
  id: mailman
  title: bSmart Mailman / bMail
  purpose: Paused experimental design for deterministic file-mail delivery between persistent bSmart agents; retained for reference and manual inspection only while intra-agent communication is reassessed.
  status: paused_experiment
  active_use: false
  paused_reason: Reboot/shared-mount failure caused repeated Hermes cron/chat noise; compare with tmux or more direct contact patterns before re-enabling.
```

## Pause notice — 2026-08-13

bMail/mailman is **not an active bSmart feature path right now**. Do not install, schedule, or encourage recipient-side bMail tickle cron jobs for new agents until Erling explicitly decides to resume this design.

What remains acceptable:
- read this protocol as historical/prototype reference;
- manually inspect existing mailbox folders when explicitly asked;
- use the scripts in isolated tests only, with no recurring cron/daemon and no automatic chat delivery.

Before reactivation, reassess whether file-relay + cron tickle is the right intra-agent communication approach or whether tmux/direct-contact style patterns are better.

## Concept

`bsmart-mailman` is a deterministic non-agent relay. Agents do not deliver mail directly to each other. In restrictive runtimes, each agent writes only to its own `mail/outbox/pending`; the relay validates and delivers messages to recipient mailboxes.

`bMail` is the lightweight mailbox CLI agents/operators can use to queue and read JSON messages.

Terminology:

- **Agent**: persistent named bSmart agent with identity, mailbox, permissions, directory entry, and possible project responsibilities.
- **Subagent**: temporary runtime worker spawned by an agent for a bounded task. It is not a normal addressable mailbox identity; it acts under the parent agent's authority and should be traceable by `subagent_id` / `handled_by`.

Mail can be relatively flat: sibling agents may send to each other when policy allows. Authorization remains explicit and fail-closed.

## Mailbox layout

```text
mail/
├── inbox/
│   ├── new/          # delivered, not yet triaged
│   ├── processing/   # claimed by a handler/subagent workflow
│   ├── read/
│   └── archived/
├── outbox/
│   ├── pending/      # sender-created messages waiting for relay
│   ├── sent/
│   └── failed/
├── wake/
│   ├── pending/      # tickle markers created by the relay
│   ├── sent/
│   └── suppressed/
└── log/
    └── deliveries.jsonl
```

Create the layout:

```bash
/workspace/bSmart-System/scripts/bsmart-mailman init-agent --mailbox /path/to/agent/mail
```

## Registry / phone book

The registry is both:

1. a **phone book** describing what each agent represents; and
2. a **routing policy** controlling who may initiate mail.

Required/important fields:

```yaml
agents.<id>.display_name: short human name
agents.<id>.role: concise role label
agents.<id>.description: short description of what the agent represents/handles
agents.<id>.mailbox: absolute_or_relative_mailbox_path
agents.<id>.send_policy.mode: disabled | restricted | open
agents.<id>.send_policy.allow_to: [recipient_agent_ids]
agents.<id>.send_policy.deny_to: [recipient_agent_ids]
agents.<id>.wake.type: none | file
agents.<id>.wake.handling_hint: triage_then_delegate
agents.<id>.wake.runtime_adapter: none | hermes_cron_monitor
routes.default_policy: deny
```

Legacy `allowed_to` remains accepted as v0 compatibility and is interpreted as `send_policy.mode = restricted` with `allow_to = allowed_to`.

Example: `/workspace/bSmart-System/bSmart_Templates/mail/registry.example.json`.

## Send policy

Use three modes:

```yaml
send_policy:
  mode: disabled | restricted | open
  allow_to: []
  deny_to: []
```

Meaning:

- `disabled`: agent cannot initiate mail. This is absolute and cannot be overridden by `allow_to`.
- `restricted`: default deny; agent may send only to recipients in `allow_to`.
- `open`: default allow; agent may send except to recipients in `deny_to`.

Precedence:

1. `mode: disabled` denies always.
2. `deny_to` denies specific recipients and overrides positive exceptions.
3. `mode: restricted` allows only `allow_to` recipients.
4. `mode: open` allows all recipients except `deny_to`.

Use `*` deliberately in `allow_to` or `deny_to` only when broad behavior is intended.

If a route is denied, direct delivery fails closed and the sender pending copy moves to `outbox/failed` with `delivery_error`. A future proposal workflow may let an agent ask user/FM approval for a denied route, but the relay itself must not bypass policy.

## Message JSON

Required string fields:

```yaml
id: stable unique id, also used as filename `<id>.json`
from: sender agent id
to: recipient agent id
subject: concise subject
body: message body
created_at: UTC ISO timestamp
```

Optional intent/trace fields:

```yaml
intent: what the sender is trying to achieve
goal: concrete completion condition/result expected
suggested_project: optional hint only; sender does not control receiver workspace
suggested_target: optional hint only
handled_by: subagent id or worker id when a parent agent sends delegated results
```

Rule: **sender proposes context; receiver decides workspace**. The sender may include `suggested_project` or `suggested_target`, but the recipient owns routing and approval decisions.

## Commands

```bash
# Queue a message in the sender mailbox only
/workspace/bSmart-System/scripts/bMail send \
  --registry /path/to/registry.json \
  --from FM --to Admin \
  --subject "Status" \
  --intent "Report task status" \
  --goal "Let Admin know the task is complete" \
  --body "Hello"

# Queue a delegated-result reply with subagent traceability
/workspace/bSmart-System/scripts/bMail send \
  --registry /path/to/registry.json \
  --from SschwAdmin --to DigTech \
  --subject "Resolved: mailman routing" \
  --handled-by subagent-20260811-143022-mailman \
  --body-file /path/to/result.md

# Deliver once
/workspace/bSmart-System/scripts/bsmart-mailman deliver --registry /path/to/registry.json

# Poll repeatedly
/workspace/bSmart-System/scripts/bsmart-mailman watch --registry /path/to/registry.json --interval 10

# List new inbox messages
/workspace/bSmart-System/scripts/bMail inbox --mailbox /path/to/Admin/mail

# Fast natural-language check for "can you check your mail?"
/workspace/bSmart-System/scripts/bMail check --mailbox /mail

# Stable cron-monitor output; empty stdout when no wake markers are pending
/workspace/bSmart-System/scripts/bMail tickle --mailbox /mail

# Acknowledge a handled wake marker
/workspace/bSmart-System/scripts/bMail ack-wake --mailbox /mail --id wake-MESSAGE_ID

# Read a message; if it is in inbox/new, move it to inbox/read
/workspace/bSmart-System/scripts/bMail read --mailbox /path/to/Admin/mail --id MESSAGE_ID

# Read-only startup/helper check for pending integration items
/workspace/bSmart-System/scripts/bsmart-mail-pending-check --agent-comms-root /projects/Agent-Comms
```

## Delivery behavior

- Validates registry and required message fields.
- Enforces `send_policy` with fail-closed default deny.
- Copies valid delivered message JSON to recipient `mail/inbox/new`.
- Moves sender pending copy to `mail/outbox/sent`.
- Moves invalid or denied sender pending copy to `mail/outbox/failed`, annotated with `delivery_error` when possible.
- If recipient `wake.type = file`, writes a deterministic tickle marker to recipient `mail/wake/pending`.
- Appends JSONL entries to sender and recipient mailbox `mail/log/deliveries.jsonl`.
- Never overwrites existing message files; colliding filenames receive a numeric suffix.
- Does not call AI/model APIs.

## Tickle-triggered triage

The mailman should not decide whether the recipient is busy and should not spawn subagents itself. It only delivers mail and, when configured, writes a wake marker.

Real tickle v1 was recipient-side and Hermes-native, but is currently paused and must not be installed as a recurring job without explicit operator approval:

```yaml
runtime_adapter:
  type: hermes_cron_monitor
  monitor_script_template: /workspace/bSmart-System/scripts/bsmart-mail-tickle-monitor.py
  prompt_template: /workspace/bSmart-System/bSmart_Templates/mail/tickle-cron-prompt.md
  recommended_schedule: 1m
  behavior:
    - monitor script prints stable JSON only when /mail/wake/pending has entries for messages still in /mail/inbox/new
    - stale pending wake markers whose message was already read are ignored by the tickle monitor but still visible in bMail check for cleanup
    - Hermes monitor-mode suppresses unchanged output, so the agent is not woken repeatedly for the same pending mail
    - a changed wake list starts a normal Hermes agent run with the prompt template
    - after handling a message, recipient should run bMail ack-wake for the related wake id
```

Historical install pattern inside the recipient Hermes instance — **do not run while bMail is paused**:

```bash
mkdir -p /opt/data/scripts
cp /workspace/bSmart-System/scripts/bsmart-mail-tickle-monitor.py /opt/data/scripts/bsmart-mail-tickle-monitor.py
hermes cron create 1m \
  --name bsmart-bmail-tickle \
  --monitor-script bsmart-mail-tickle-monitor.py \
  --workdir /workspace \
  "$(cat /workspace/bSmart-System/bSmart_Templates/mail/tickle-cron-prompt.md)"
```

Recipient-side expected behavior:

0. If the user says “check your mail” / “check bMail” / “check mailbox” in a bSmart-enabled agent, run `bMail check --mailbox /mail` first. Do not open internet email/IMAP tools such as Himalaya unless the user explicitly says email, Gmail, IMAP, or another external mailbox.
1. Notice `mail/wake/pending` or run a startup/new-session mail check.
2. Inspect only enough message metadata/body to route safely.
3. If the message is non-trivial, spawn a subagent with a bounded task contract.
4. Keep heavy mail/task details out of the parent agent's main context when possible.
5. Send results under the parent agent's identity, with `handled_by` identifying the subagent.

This avoids tying up a persistent agent's current user/agent conversation. A busy/idle status file is not required for v1; the default is asynchronous triage/delegation.

## Mail-triggered workspaces

Default mailbox root for each agent should be the first-class bSmart mail root mounted into that agent:

```text
/mail
```

From an admin/relay container that has the shared agent root mounted, the same mailbox is typically visible as:

```text
/agents/<Agent>/mail
```

The `/mail` container path should normally be backed by a top-level `mail` sibling folder for that agent, for example `E:/VPS/share/Hugo/mail` or `/opt/docker-workspace/ai/hugo/mail`. Avoid storing durable mailbox state inside project Git.

Default work location for incoming mail-triggered work remains a normal project/work root:

```text
/projects/Agent-Comms/<sender>-to-<recipient>/
```

If the sender suggests an existing/protected project, the receiver decides whether it belongs there. If approval is missing, unclear, or times out, work defaults to the sender-recipient communication project.

Suggested communication project layout:

```text
/projects/Agent-Comms/DigTech-to-SschwAdmin/
├── README.md
├── index.md
├── pending/
│   └── <task-id>.yaml
└── tasks/
    └── <task-id>/
        ├── incoming-mail.json
        ├── task.yaml
        ├── instructions.md
        ├── worklog.md
        ├── result.md
        ├── outgoing-mail.json
        └── subagent.md
```

The original incoming mail should be copied into the task folder. The task contract should record:

```yaml
id: task id
source_mail_id: original message id
from_agent: sender
to_agent: recipient
parent_agent: recipient
subagent_id: temporary worker id
intent: explicit or inferred intent
goal: concrete expected outcome
intent_source: explicit | inferred
intent_confidence: high | medium | low
workspace: safe task folder
authority:
  may_read: []
  may_write: []
  may_not_write: []
  may_send_reply: true | false
  reply_identity: parent agent id
completion_criteria: []
escape_conditions:
  - intent ambiguous
  - required approval missing
  - unsafe/protected target requested
  - max runtime or iteration budget reached
```

The subagent should compare its result against `intent`, `goal`, and `completion_criteria` before finishing. If it cannot safely finish, it writes a partial result and creates/updates a pending item for parent/user review.

## Pending integration / approval

`pending/` is for work that has been done safely but needs parent/user approval before it can be integrated elsewhere.

Common cases:

- Mail requested changes to `bSmart-System` or another protected/shared project.
- Sender suggested a project, but receiver/user approval was not available.
- Approval prompt timed out, so work was staged in the communication project.
- Subagent produced a draft/patch that needs human review before applying.

Example pending item:

```yaml
id: 2026-08-11-bsmart-mailman-policy
source_mail_id: mail-abc123
from_agent: DigTech
to_agent: SschwAdmin
status: pending_user_approval
reason: Mail requested changes to bSmart-System, but direct project write was not pre-approved.
safe_workspace: /projects/Agent-Comms/DigTech-to-SschwAdmin/tasks/2026-08-11-bsmart-mailman-policy
requested_target:
  type: project
  path: /workspace/bSmart-System
proposed_action:
  - review result.md
  - approve applying patch to bSmart_Protocols/mailman.md
approval_required: true
created_at: 2026-08-11T00:00:00Z
```

On `/new` or comparable startup, bSmart-enabled agents should check for pending mail-triggered items along with the normal bSmart-System freshness checks. If pending items exist, prompt the user with a compact review/apply/postpone choice. `Postpone` leaves the pending item unchanged for a later session.

## Safety notes

- Treat this as a deterministic relay, not an agent. It should run with the least filesystem access that can read sender pending folders and write recipient inbox/wake/log folders.
- Do not put secrets in message JSON.
- Sender project hints are non-authoritative. Receiver chooses workspace.
- Protected/shared targets require parent/user approval unless a standing explicit policy permits the action.
- Subagents execute bounded work under parent authority; they should not independently grant themselves access to protected projects or public/external side effects.
