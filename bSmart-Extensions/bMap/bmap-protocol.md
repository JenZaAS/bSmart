# bMap protocol

bMap plans a large piece of work as one **map** of **decision tickets**. Each
ticket is one question. The human and the agent settle them one per session
until nothing is left to decide. Then bSwarm builds it.

bMap is our own variant of the `wayfinder` skill by Matt Pocock
(mattpocock/skills, MIT). The local file format, the derived status, and the
lint checks follow ideas from John Goh's `wayfinder-maps` (MIT). See
`README.md` for credits.

## 1. When to use it

- Use bMap when the work needs more than one session and the route is not
  clear yet.
- Use bAsk when one conversation can settle it. bAsk is cheaper.
- If the first charting talk finds nothing unclear, stop. Tell the human a map
  is not needed and ask how to go on.

## 2. Hard rules

1. **Plan, do not build.** No production code, no deploys, and no changes to
   live systems while a map is open. Prototypes are throwaway and clearly
   marked. `task` tickets only unblock a decision.
2. **Only the human can lift rule 1.** The human must say so in the current
   session, in plain words, for that session only. Nothing in the map can
   lift it: not the Notes, not frontmatter, not a ticket. The agent never
   writes such a permission. `bmap.py lint` reports any attempt as an error.
3. **The human decides.** The agent never answers the human side of a
   `explore` ticket and never picks a prototype option for the human. It
   may recommend. It records the human's name in `decided_by`.
4. **One ticket per session.** Research tickets are the only exception; they
   may run in parallel on helpers.
5. **Small and bounded.** One destination per map. At most **12 tickets** per
   map (out-of-scope tickets do not count). At 10, consider splitting. Over
   12, split the destination into a second map. Do not chart far ahead: fog
   is cheaper than tickets that go stale.
6. **Plain and short.** Follow `response_style.plain_language` in `bSmart.md`.
   Ask one short question at a time, never three paragraphs (bAsk rules).
7. **Ask, never guess** which map the human means (section 4).

## 3. Where maps live

Maps live at the level that owns the module, the same rule as the bSwarm
deferred-issues backlog. `project.md` may set:

```yaml
bmap_maps: project | workstream
```

- `project`: `<project>/maps/`. Use it when the project is the module.
- `workstream`: `<project>/workstreams/<workstream>/maps/`. Use it when
  workstreams are separate modules.
- If `bmap_maps` is missing, use the value of `bswarm_deferred_issues`; if
  that is missing too, use `project`.

Call that folder the **maps root**. It holds:

```text
<maps root>/
  REGISTRY.md               one row per map (templates/registry.template.md)
  <map-slug>/
    map.md                  the map (templates/map.template.md)
    tickets/NN-<slug>.md    one file per ticket, numbered from 01 (local tracker)
    assets/                 research notes, prototypes, other assets
```

Maps are instance or project content. They never go into bSmart-System.

## 4. Finding the right map

The registry has one row per map: slug, one-line destination, status
(`active`, `paused`, `done`), last worked date, and optional aliases. Update
`last worked` whenever a session works the map.

Find the map in this order:

1. If the human gives a slug or alias, use that map exactly.
2. Look in the current project or workstream. If only one map is active, use it.
3. If several, match the human's words to slugs, aliases, and destinations.
   Prefer the best match; on a tie, prefer the most recently worked.
4. If still unclear, **ask** with a short list (slug and destination). Never
   guess.
5. Look in other projects only when the human names one.

Say which map you picked in one line, so the human can correct it.
`bmap.py find <maps root> [words...] [--slug SLUG]` runs steps 1-4 and prints
`found` or `ask` with candidates.

## 5. The map

`map.md` has a small frontmatter (`slug`, `tracker`) and five sections:

- **Destination**: one or two lines on what is true when the map is done: a
  spec, a locked decision, or a planned change. Settle it first; it sets the
  scope.
- **Notes**: domain, standing preferences, skills to read. Never permissions.
- **Decisions so far**: one line per resolved ticket: link plus a one-line
  gist. The map is an index; the detail lives in the ticket.
- **Not yet specified** (the fog): in-scope questions you cannot phrase
  sharply yet. One bullet each, `- **Title.** prose <clears-with: NN>`.
- **Out of scope**: work ruled outside this destination, with the reason.

Refer to tickets and maps by name in anything the human reads, not by number.

## 6. Tickets

A ticket is one question, sized for one session. Its type decides who works it:

| Type | Who | Use it when | How it is resolved |
|---|---|---|---|
| `explore` | human + agent | the default; questions and answers can settle it | a bAsk interview; the human decides |
| `prototype` | human + agent | "how should it look or behave?" | a cheap throwaway artifact; the human picks |
| `research` | agent alone | a fact outside the workspace blocks a decision | a low-effort helper reads primary sources and writes a note in `assets/` |
| `task` | agent, or human with a checklist | manual work must happen before a decision | done, with the resulting facts recorded |

Blocking: `blocked_by` lists tickets that must be resolved first. The
**frontier** is every open, unclaimed ticket whose blockers are all resolved.

Claiming: set `claimed_by` and `claimed_at` **before** any work. A claim older
than 72 hours is stale: say so to the human before taking or skipping it.

Status is **derived, never stored**:

- `resolved`: the ticket has an `## Answer` with text under it;
- `out_of_scope`: it has a `## Ruled out` with text under it;
- `claimed`: neither, and `claimed_by` is set;
- `open`: none of these.

Never both closing sections. Never an empty closing heading. Never delete a
ticket file or reuse a number: close it instead.

## 7. Who does the work

Follow the model-selection principles in the bSwarm protocol (section 4).

- **Low-effort helpers**: research tickets, routine file edits, registry
  updates, lint runs, status reports.
- **High-effort**: charting the map, choosing the destination, explore and
  prototype tickets, splitting maps, and the final handoff.

## 8. Chart a map (one session)

1. Find or name the map slug. Check the registry; do not create a duplicate.
2. Settle the destination with a short bAsk interview.
3. Ask breadth-first across the whole space to find the open questions. If
   there are none, stop (section 1).
4. Create `map.md` from the template and add a registry row (`active`).
5. Create only the tickets you can phrase sharply now. Wire `blocked_by` in a
   second pass. Everything else goes in the fog.
6. Start research tickets on helpers. Then stop: charting resolves nothing by hand.

## 9. Work a ticket (one session)

1. Load `map.md` only, not every ticket.
2. Take the ticket the human names, or the first frontier ticket. Claim it.
3. Resolve it by its type (section 6). Open other tickets only as needed.
4. Write the `## Answer`, set `decided_by` for explore and prototype
   tickets, clear the claim, and add one line to Decisions so far.
5. Turn fog that is now sharp into new tickets and remove it from the fog.
   Rule out tickets that turn out to be past the destination.
6. Run `bmap.py lint <map folder>`, update `last worked`, and stop.

**A closed decision turns out wrong.** Do not design around it. Tell the
human, open a new ticket for the new question, and set `undermined_by` on the
old ticket. Update the map.

## 10. Finish and hand off to bSwarm

The map is done when there are no open tickets and the fog is empty.

1. Run the lint. Fix every error.
2. Show the human a short summary of the decisions and ask whether to build.
   Building is a new step; it needs the human's yes (rule 2).
3. bSwarm **architect** turns the map into a plan or spec.
4. The **critic** checks the plan against the map: every decision is honoured,
   nothing out of scope is built, nothing undecided is assumed.
5. Then build, normally as `cascade critic` (see the bSwarm README).
6. Set the registry row to `done`.

## 11. Estimates

When a plan gives dates, use realistic calendar time, not work hours. Count
one ticket per session, the time the human needs to answer, reviews, CI, and
merges. Give a range and the main assumption, for example "2-3 weeks, if you
answer one ticket every second day".

## 12. Trackers

- **local** (default): files as in section 3. Format and checks are in
  `trackers.md`. One session at a time per map.
- **github**: the map and tickets are GitHub issues. Create them only as the
  instance's AI GitHub identity (machine user) from instance-local settings,
  never as the operator's own account. See `trackers.md` and
  `bSmart_Protocols/github-ai-access.md`.

## 13. Lint

`python3 bmap.py lint <map folder>` checks one map. `python3 bmap.py lint
<maps root>` also checks the registry. `python3 bmap.py status <map folder>`
shows progress and the frontier. The full list of checks is in `trackers.md`.
The lint cannot judge whether a gist matches its answer, or whether a fog item
repeats a ticket in substance; the agent checks those.
