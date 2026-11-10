# bMap

bMap plans a large piece of work, too big for one session, as one map of
decision tickets. The human and the agent settle one ticket per session until
nothing is left to decide. Then bSwarm builds it.

Status: draft, optional. Off until the operator turns it on.

## What it does

- One map per destination, with a short list of decisions so far, a fog list
  ("not yet specified"), and an out-of-scope list.
- Four ticket types: explore, prototype, research, task. Blocking links
  show which tickets can be taken now.
- Plan, do not build. Only the human can allow building, in the session.
- Small maps: at most 12 tickets.
- A registry per project or workstream, so the agent finds the right map or
  asks.
- Local markdown files or GitHub issues as the tracker.
- A finished map hands off to bSwarm: architect, critic check, then build.

## Files

| File | Purpose |
|---|---|
| `bmap-protocol.md` | The rules: when to use, hard rules, location, finding a map, tickets, sessions, handoff, estimates. |
| `trackers.md` | Local file format, the lint checks, and GitHub issues. |
| `bmap.py` | `lint`, `status`, and `find`. Python 3 standard library; Linux, Windows, macOS. |
| `templates/map.template.md` | Blank map. |
| `templates/ticket.template.md` | Blank ticket. |
| `templates/registry.template.md` | Blank map registry. |

Filled maps and registries belong in the project (`<project>/maps/` or a
workstream's `maps/`), never in this folder.

## Use

1. Read `bmap-protocol.md`.
2. Find the maps root (`bmap-protocol.md` section 3) and the map (section 4):
   `python3 bmap.py find <maps root> <words>`.
3. Chart a new map, or work one ticket.
4. Check it: `python3 bmap.py lint <map folder>`.
5. Explore tickets use bAsk (`../bAsk/`).

## Turn it on

Copy or sync this folder into the instance's extensions root, as for other
bundled extensions (`bSmart_Docs/extensions.md`). bAsk is needed for
explore tickets; turn it on too.

## Credits

- Method: `wayfinder` by Matt Pocock, https://github.com/mattpocock/skills (MIT).
  bMap is a variant in our own words, not a copy.
- Local file format, derived status, and lint check ideas: `wayfinder-maps` by
  John Goh, https://github.com/rengwu/wayfinder-maps (MIT). `bmap.py` is a
  separate implementation and copies no code.
- Map slugs, a per-project map list, and "report, do not guess": ideas from
  `wayfinder-local` by wearyscary, https://github.com/wearyscary/wayfinder-local.
  That repo has no license, so only the ideas are used; no text or code.
