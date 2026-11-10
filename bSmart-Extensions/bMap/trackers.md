# bMap trackers

## Local markdown (default)

Layout: see `bmap-protocol.md` section 3.

### Map frontmatter

```yaml
slug: <map-slug>      # same as the folder name; lowercase words joined by '-'
tracker: local        # local | github
```

### Ticket frontmatter

```yaml
type: explore      # research | prototype | explore | task
blocked_by: []        # e.g. [01, 03]
claimed_by:           # who holds the ticket now
claimed_at:           # ISO 8601 time with a zone, e.g. 2026-01-31T09:00:00Z
decided_by:           # the human who decided (explore and prototype)
undermined_by: []     # later tickets that broke this answer's premise
```

`explore` is the ticket where the agent asks and the human decides. The old
names `discussion` and wayfinder's `grilling` are lint errors that suggest
`explore`, so a map never carries two names for one type.

There is no `status` field. Status comes from the body (`bmap-protocol.md`
section 6). Lines inside fenced code blocks are never read as structure, so a
ticket can quote `## Answer` without closing itself.

Links in Decisions so far and Out of scope use `[<title>](./tickets/NN-<slug>.md)`.

### Lint checks (`bmap.py lint`)

Errors:

- map: no slug, slug differs from the folder, bad tracker, no Destination;
- map: a frontmatter key or a Note that tries to allow building;
- map: more than 12 tickets (out of scope not counted);
- ticket: bad file name, duplicate number, no frontmatter, no title, no
  Question, unknown type, or an old type name (`discussion` or `grilling`:
  write `explore`);
- ticket: both Answer and Ruled out, or an empty closing heading;
- ticket: a resolved explore or prototype ticket without `decided_by`;
- ticket: `claimed_at` that is not a time with a zone;
- graph: `blocked_by` or `undermined_by` naming a missing ticket or itself;
  any `blocked_by` cycle;
- index: a resolved ticket missing from Decisions so far; Decisions so far
  listing a missing, open, or out-of-scope ticket; an out-of-scope ticket
  missing from Out of scope;
- fog: an item that repeats a live ticket title, or whose `clears-with`
  ticket is missing or already resolved;
- a stored `status` that disagrees with the body;
- registry: a bad status or date, a duplicate slug or alias, a row without a
  map folder, a map folder without a row.

Warnings:

- 10 or more tickets (near the limit);
- a claim older than 72 hours, a claim without `claimed_at` or `claimed_by`,
  a claim left on a closed ticket;
- more than one non-research ticket claimed at once;
- a ticket blocked by an out-of-scope ticket (it can never unblock);
- a `task` whose title reads like a build step;
- a ticket listed twice in Decisions so far; a fog item without a bold title;
- a `status` field that matches the body (delete it);
- a registry row marked `done` while the map has open tickets.

Exit codes: `0` clean, `1` errors, `2` no map or registry at that path.

## GitHub issues

- The map is one issue labelled `bmap:map`. Tickets are its sub-issues,
  labelled `bmap:research`, `bmap:prototype`, `bmap:explore`, or
  `bmap:task`.
- Use GitHub's own blocking links. Claim by assigning the issue. Resolve with
  an `Answer` comment and close the issue; rule out with a `Ruled out`
  comment and close it as not planned.
- Map and ticket issues never carry a build label such as `ready-for-agent`.
  They are decisions, not build work.
- Create issues, labels, and comments only as the instance's AI GitHub
  identity from instance-local settings. Show the operator public text before
  posting, as `github-ai-access.md` requires.
- The map's frontmatter adds `repo: <owner/repo>` and `map_issue: <number>`.
  The registry still lists the map, and the map folder holds `map.md` as a
  local pointer and cache. The lint reads local files only.

### Later: a GitHub-issues build flow

Not built yet. bMap stays compatible with a sandcastle-style flow: after the
map is done and bSwarm has written the plan, build tickets become separate
issues with a build label (label-gated), a planner checks blocking links,
each issue gets one fixed branch (for example `agent/issue-<n>`), PR feedback
goes back to the same branch, and a merger step lands it. Decision tickets
never enter that flow.
