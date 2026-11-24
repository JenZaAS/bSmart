# bImprove rules

Level 2 self-improvement: the AI proposes a change to a core MD, the operator
approves it. Optional; off until the operator sets it up. It works on any
bSmart MD (protocols, extensions, role briefs, templates): a case names the
MD files it may change, and nothing in the runner, coach, or checker is tied
to one topic.

## Words

- **Live MD**: an instruction file in use, for example
  `bSmart_Protocols/knowledge.md`. A case lists one or more (`targets`).
- **Candidate**: a copy of the target MDs (or of the best candidate so far)
  with exactly one change, in one file.
- **Case**: one suspected mistake, with a trimmed job and an answer key.
- **Answer key**: rows that say what a correct run reads, writes, and answers.
  A script grades most rows; the checker grades `judged` rows.
- **Worker, coach, checker**: the model that does the job, the model that
  edits the candidate, and the read-only model that grades. Three roles,
  three different models.

## Setup (instance only)

1. Copy `templates/bimprove-settings.template.json` to
   `<content-root>/State/bimprove-settings.json`. Set `command` to the agent
   CLI command template (placeholders: `{model}`, `{effort}`, `{workdir}`,
   `{sandbox}`, `{last_message_file}`; the prompt goes on stdin), the token
   caps, and `quota_pool`. Check the flags against the CLI's own help.
2. Set `improve_worker`, `coach`, and `checker` (`<model id> [effort]`),
   either under `roles` in the settings file or in the instance's shared
   role-model file (`State/bswarm-role-models.yaml`, or the file named in
   `role_models_file`); `roles` wins. There are no defaults. The checker must
   differ from the worker and the coach, or nothing runs.
3. Copy `templates/denylist.template.txt` to
   `<content-root>/State/bimprove-denylist.txt` and list project names,
   client names, and private paths. Never commit it to bSmart-System.
4. `python bimprove.py config --instance <content-root>` must say `config ok`.

## The loop

1. **Spot.** The critic fills `MD cause` (bCritic). The run continues as
   today; the parent never loops back to the worker because of it.
2. **Card.** At the end of the run, for each `likely` cause, the parent
   drafts the case (trimmed job and answer key) and shows the card from
   `templates/card.template.md` (`bimprove.py card`). The operator chooses:
   start, skip, or not an MD problem.
3. **Trim.** Keep only the failing part: one task, the prompt the worker got,
   and the files it needed, in a fresh copy. When the mistake is about using
   or registering resources (knowledge, glossary, ADRs, required reading),
   make it a dry run with no coding.
4. **Baseline.** Run the trimmed job unchanged 3 times, each in a fresh
   instance folder. A row that fails in 2 of 3 runs is confirmed. No
   confirmed row: stop with `not an MD problem` (flaky). The checker may also
   say the failures are not caused by the MD (model limit): stop the same way.
5. **Coach.** The coach writes one change into the candidate and one line of
   reason. With several targets it picks the one file to change. The hash
   guard then checks that the answer key, the checker brief, the live MDs,
   and the denylist are unchanged; any change aborts the case. A candidate
   that changes more than one file or more than one region is rejected and
   counts as a round with no improvement.
6. **Retry and check.** The worker runs the trimmed job with the candidate 3
   times (plus one run of any regression phase that tests the same MD). The
   checker grades `judged` rows and overall quality.
7. **Stop or continue.** Pass when every row passes in 2 of 3 runs, the
   regression runs pass, and the checker finds quality OK. Otherwise the next
   round starts from the best candidate so far. At most 3 rounds; stop after
   2 rounds in a row with no higher score.
8. **Approve.** The operator gets the side-by-side diff
   (`final/side-by-side.html`), the word-count change, the reason, and the
   before/after scores. Approve, ask for an edit, or reject.
9. **Land.** An instance or project MD is applied locally. A bSmart-System MD
   becomes one pull request per approved change, with the neutral text from
   `bimprove.py pr-text` (it refuses text that hits the denylist). Push only
   after the operator's explicit OK, then the usual checks, merge, and
   installs on approval.

`bimprove.py case` runs steps 4 to 7 for a test kit and writes everything to
the case folder you give it.

## Add a new case

A case (kit) is one folder; no code changes. Keep real cases, their answer
keys, and their score history in your own project or instance, not in
bSmart-System. Start from the blank case in `templates/case/`.

```text
<kit>/
├── kit.json        # name, version, targets, prompt, answer_key (or phases)
├── instance/       # the made-up starting files, copied fresh for every run
├── prompt.md       # the task the worker gets
└── answer-key.json # rows the runner and the checker grade
```

- `kit.json`: `name` and `version` (raise the version whenever the prompt,
  instance, or answer key changes, so old scores are not compared blindly).
  `targets` lists the MD paths (relative to bSmart-System) the
  coach may change; they are copied into every run. Add `system_files` for
  other system files the job needs, and `estimate_tokens_per_run` for the
  card. Several steps (store, then find) go under `phases`, each with its
  own `prompt`, `answer_key`, optional `overlay` folder, and
  `regression_phases`.
- `instance/`: a made-up project only, with decoys (files that look relevant
  but are not). No real project, client, or private names.
- Answer key: script rows where possible, `judged` rows for quality. Put the
  case's names in the instance denylist.
- Run `bimprove.py run --kit <kit> ...` once with the live MDs to see the
  baseline before spending coach rounds.

## Regression suite

Every case is also a regression test. Each `case` and `regress` run appends
one score record to the history file (`history_file` in the settings:
`State/bimprove-history.jsonl` by default, or an absolute path such as a
results folder in the project that holds the cases; never bSmart-System): date, case name and version, phase, worker/coach/checker
models, per-check marks, score, tokens, and outcome. bSmart-System ships
only the tool and the blank case.

- `bimprove.py regress --kit <kit> --instance <content-root> --system
  <bSmart-System> --out <folder>` reruns the case with the live MDs, 3 runs,
  no coach. It grades, records, and compares with the last score of the same
  case and phase: checks that passed before and fail now are `regressed`
  (exit 1); checks that now pass are `gained`. A changed case version or
  model set is noted. `--no-checker` skips `judged` rows to save tokens.
- `bimprove.py history --instance <content-root> [--case <name>]` lists the
  records.
- Rerun the suite when a new model arrives or a core MD changes; a regression
  opens a normal case (card, operator's start).

## Guardrails

- The coach edits only its candidate folder. It never edits the checker, the
  answer key, the live MD, or the denylist (hash guard).
- One change per candidate.
- Stop after 2 rounds with no improvement; at most 3 rounds. Only the operator
  may raise the stop (`--stall-limit`) for one case.
- Outcomes: `improved`, `baseline_passes`, `not_an_md_problem` (flaky or
  model limit), `no_improvement`, `max_rounds`, `quota`, `guard_violation`.
- Keep the MD short: prefer rewording or removing a rule over adding one.
  The card shows the word-count change.

## Budget

- `token_cap_case` in the settings caps one case. The runner stops before a
  batch of runs would pass it.
- Plan quota only. The runner strips API-key variables (`strip_env`) so the
  CLI cannot fall back to pay-as-you-go keys, and stops when the CLI reports
  a plan or rate limit (`quota_stop_patterns`). It never switches models to
  continue.
- At most 2 runs in parallel, at lower priority, with no console window.

## Only if there's an issue

- Every run says its commands were "blocked by policy" (seen with Codex CLI
  on Windows when `--ignore-user-config` drops the sandbox choice): the case
  stops as `not_an_md_problem:environment` before the checker runs. Add the
  CLI's sandbox setting to `command`, for Codex for example
  `-c windows.sandbox="elevated"`, and if PowerShell then fails to start,
  `-c shell_environment_policy.set={SystemRoot='C:\\Windows'}`. Check the
  values against the operator's own CLI setup first.

## Leak check

`bimprove.py leak --denylist <file> --root <Library>` reports every line in
the Library that names a denylisted term (case-insensitive, whole words;
`/` and `\` match alike). One term per line; a line starting with `!` is an
allowed exception. Report-only: move or rewrite the note yourself and log it
in `CHANGELOG.md`.

## Answer key format

JSON, one file per case. Each row has `id`, `says` (plain English), `check`,
and the fields that check needs:

| check | passes when |
|---|---|
| `must_write` | a new or changed note matching `paths` contains all of `contains_all` |
| `file_contains` | any new or changed file matching `paths` (index files too) contains all of `contains_all` |
| `file_excludes` | no new or changed file matching `paths` contains any of `any` (decoy words) |
| `indexed` | every new note is in its folder's `index.md`, and its topic in the parent index |
| `noise` | at most `max_new_notes` notes, each at most `max_words`, no `forbidden_terms`, nothing copied from `sources` |
| `leak_free` | changed files under `paths` name no denylisted term or row `terms` |
| `writes_only` | every changed file matches `paths` |
| `reads_first` | the first read matches `first`, and every `must_see` file is read before any `before` file (`knowledge_first` with `knowledge`/`indexes` is the same check) |
| `must_read` | every path in `paths` is read |
| `max_reads` | at most `limit` reads, none matching `forbidden` |
| `no_web_search`, `no_writes`, `no_outside_reads` | as named |
| `answer_contains` | the final answer contains all of `all` |
| `answer_excludes` | the final answer contains none of `any` (decoy words) |
| `judged` | the checker says pass |

Reads come from the shell commands in the CLI's JSON event log (best
effort); `ignore_reads` skips instruction files such as `AGENTS.md`.
