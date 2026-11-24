# bImprove

Optional. Improves bSmart's own instruction files (core MDs) from mistakes
that agents actually made. The AI proposes; you approve every change.

- A bCritic review answers one more question: "Could a better core MD have
  prevented this?"
- At the end of a run you get one card per likely case, with its size in
  tokens, plan quota, and minutes. Nothing happens unless you say start.
- The failing part is rerun unchanged 3 times (the baseline). If the mistake
  does not repeat, the case closes as "not an MD problem".
- The coach writes a copy of the MD with one change. The worker retries and a
  checker on another model grades it against the answer key. At most 3
  rounds; it stops after 2 rounds with no improvement.
- You see the old and new file side by side and approve or reject. An
  approved change to bSmart-System becomes one pull request; pushing always
  needs your OK.

Files:

- `improve.md`: the loop, the card, the rules, the outcomes.
- `coach.md`, `checker.md`: the two role briefs.
- `bimprove.py`: the mechanical parts (fresh run folders, the agent CLI call,
  grading, the hash guard, the side-by-side diff, the leak check, the card,
  the PR text). Standard library only; Windows, macOS, Linux.
- `templates/`: settings, denylist, card, and PR text.
- `templates/case/`: a blank case. Any bSmart MD can be a target; a new case
  is just a folder ("Add a new case" in `improve.md`). Real cases, answer
  keys, and score history live in your own project, not here.

Every case doubles as a regression test: `bimprove.py regress` reruns it with
no coach and compares with its last score; scores are kept in the instance's
history file (`State/bimprove-history.jsonl` unless the settings name another).

Instance data (settings, denylist, cases, results) lives in the instance,
never here. Models are set in the instance; this folder names none.
