# bSwarm project jobs package

A **job** is one bounded cascade run that an operator can reopen later. A workstream may point at a job, but the job folder is the durable quick-glance record.

## Layout

```text
jobs/
├── README.md
└── <YYYY-MM-DD>-<slug>/
    ├── report.md
    ├── plan.md
    └── notes.md        # optional
```

Use Markdown. Keep the slug short and stable. `report.md` is the first file an operator opens.

## Rules

- **Update in place**; do not append a new report for every round.
- Write/update the job package after the design audit, after each architect task, and after the final code audit.
- Keep reports short; the one-page shape is a guide, not a hard limit.
- `report.md` contains **External-audit bullets only** (class + status), never an internal-critic dump.
- **optional findings: count only** unless the operator asks for detail.
- **Do not vendor source trees or diffs** (or chat transcripts) in the job folder; link to commits, ADRs, or workstreams instead.
- The parent agent re-sorts auditor proposals into `automatic`, `decision`, or `optional`. Unsure means `decision`.

## Required report sections

Job (date, slug, goal, workflow keyword, outcome, commit, report link) · scope in/out · architect tasks · operator decisions · automatic (count + one line) · open decisions · optional count · each external auditor and each finding (actual model ID, design or code, automatic/decision/optional + status; stop reason) · evidence · trust / not verified · next.

## Classification

| Class | Meaning |
|---|---|
| `automatic` | Agent/architect acts without waiting for the operator. |
| `decision` | The operator must decide before the run continues. |
| `optional` | Informational; does not continue the auditor list. |

External auditors propose classes; the parent agent owns the final classification.
