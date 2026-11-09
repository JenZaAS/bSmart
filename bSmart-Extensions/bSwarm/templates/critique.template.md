# Critique — <role reviewed> r<n>

<!-- Copy to bswarm-runs/<run>/critiques/<role>-r<n>.md (multi-task cascade:
     <role>-t<task>-r<n>.md). Keep this file; never delete or rewrite it.
     Tags, IDs and rules: bswarm-protocol.md section 7. -->

- Role reviewed: `architect` | `coder`
- Task: `<task id or none>`
- Round: `<1-3>`
- Score: `<1-10>`/10 (counts only `automatic` and `decision` issues)
- Critic model: `<model id actually used>`
- Date: `<YYYY-MM-DD>`
- Reviewed artifact: `<relative path, commit, or plan file>`
- Previous round: `<relative path to r<n-1> file or none>`

## Issues

<!-- One heading per issue, tags in this fixed order:
     ### C<id> [critical|important|minor] [automatic|decision|optional] [open|fixed|deferred|rejected] <short label>
     Keep IDs from earlier rounds; new issues take the next unused number.
     Repeat every issue still open from the previous round. -->

### C1 [<severity>] [<class>] [open] <short label>

- Where: `<file/section/lines>`
- Problem: <what is wrong, against which spec, test, or ADR>
- Suggested fix: <smallest change that resolves it>
- Verify: <how the fixing role or parent can check it>

## Notes

<!-- Optional: promotions (who, why, new tags), status changes with reason. -->
