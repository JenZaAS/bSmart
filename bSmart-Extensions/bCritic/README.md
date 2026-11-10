# bCritic

bCritic is the critic role as a small standalone skill. It reviews a plan,
code, or any Markdown document, scores it, and keeps the review as a
development log. bSwarm's critics always follow it.

Status: draft, optional. Works on its own, with or without bSwarm. Install it
together with bSwarm, which uses it.

## Files

| File | Purpose |
|---|---|
| `critic.md` | The critic rules: checks, score, rounds, issue tags, review file, summary, backlog. |
| `critique-notes.md` | Less common cases. |
| `templates/critique.template.md` | Blank review file. |
| `templates/deferred-issues.template.md` | Blank deferred-issues backlog. |

## Use

Say "bCritic this <file or plan>". The agent reads `critic.md`, writes the
review file, and returns the short summary.
