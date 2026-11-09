# bSwarm critique files: edge cases

The routine flow is in `bswarm-protocol.md` section 7. These notes cover the
less common cases.

- **Critic cannot write files.** Some adapters run critics read-only. The
  critic then returns the full review as its output, and the parent agent
  writes it unchanged to the critique file before routing the summary. Record
  in the run record that the parent wrote the file.
- **External auditors.** Auditors (section 3) may use the same file format
  with the prefix `A` instead of `C` and the file name
  `audit-<design|code>-<n>.md`. The job report still lists auditor findings
  as described in `templates/jobs/`.
- **Duplicate issues.** When two IDs turn out to be the same issue, keep the
  lower ID, mark the other `[rejected]`, and note "duplicate of C<id>" under
  it. Do not renumber.
- **Reopened issue.** An issue marked `fixed` that comes back keeps its ID and
  returns to `[open]`, with a one-line note on why.
- **Severity vs class.** Severity says how much the issue matters; class says
  who acts. They usually match (`minor` is usually `optional`), but the parent
  sorts the class (section 3) and only the class drives the stop rule.
- **Backlog status vs file status.** A backlog entry starts as `open`. When it
  is later fixed, set it to `done` and link the commit; the old critique file
  stays as written.
- **Format.** Tagged Markdown is used because it is readable for people and
  searchable with a plain text search. A machine-readable export (for
  example JSON) can be generated from the headings later if a tool needs it;
  the Markdown file stays the source.
