# bSmart Protocol: bHistory

```yaml
protocol:
  id: history
  title: bHistory
  purpose: Keep a concise bullet-point diary of meaningful completed work.
  use_when:
    - recording a completed task, milestone, or accepted change
    - looking up what was done without reading a full transcript
```

## Boundary

bHistory is a short **completed-work diary** for one bSmart instance.

- It records what was done, not what should be done next.
- It is not a decision log, TODO list, workdoc, chat transcript, or backup manifest.
- Important decisions remain in the Decision Log.
- Detailed reasoning and evidence remain in Workdocs or referenced project files.
- Pending work and status remain in `bSmart_TODO.md`.

## Entry format

Use one concise bullet per meaningful completed item:

```md
- YYYY-MM-DD — <short completed action>. References: `<path>`; `<path>`.
```

Rules:

- Use plain language and one sentence where possible.
- Prefer action verbs: added, fixed, verified, migrated, published, archived.
- Include only enough context to identify the result.
- Add references only when they help locate useful detail; do not copy the detail into bHistory.
- Do not include secrets, routine checks, full commands, long explanations, or internal tool output.
- Do not add unfinished, postponed, rejected, or merely proposed work.
- Correct an old entry by adding a new concise correction rather than rewriting history silently.

## Storage and loading

```yaml
storage:
  instance_file: /workspace/bSmart/bHistory.md
  template: /workspace/bSmart-System/bSmart_Templates/bHistory.template.md
loading:
  default: do not load the full diary during every session
  recent: load the recent tail when a handoff or completion summary needs it
  lookup: search bHistory when the operator asks what was completed or requests historical context
```

Keep bHistory append-oriented and small. If it becomes large, summarize older entries into a dated compact section while retaining references to the detailed source records.
