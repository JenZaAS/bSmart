# bSmart Protocol: test tiers

```yaml
bsmart-protocol-summary:
  id: test-tiers
  title: Tagged tests, pass/fail history, and two run tiers with automatic moves
  purpose: Run the tests that matter on every change and the rare, low-severity, or slow ones on a slower schedule, with tags in the project, history in the instance, and tier moves made by rule instead of by hand.
  load_when:
    - adding, tagging, or reviewing tests in a project that uses test tiers
    - wiring CI or an agent routine for the special tier
    - a special-tier test failed, or a tier review is due
    - classifying an existing test suite once
  owner_files:
    - bSmart_Protocols/test-tiers.md
    - scripts/bTestTiers
    - bSmart_Templates/test-tiers.template.txt
    - bSmart_Templates/test-tiers-settings.template.json
    - bSmart_Templates/test-tiers-log.template.md
```

Optional per project. A project without a tag manifest runs its tests as
before. This protocol adds to `design-context.md` section 6 (which tests earn
their place); it does not replace it.

**Scope: code developed in a git repo with a main branch** (for example on
GitHub), because the special tier is tied to main. One-off agent scripts and
their throwaway tests are out of scope: they are not tagged, logged, or
tiered.

## Tags

Every test gets two tags, and one more when it guards a bug:

| Tag | Values | Meaning |
|---|---|---|
| likelihood | `main`, `edge` | `main`: a path real use takes often. `edge`: a rare input, state, or platform. |
| severity | `high`, `med`, `low` | What breaks if this behaviour breaks: `high` data loss, security, wrong results, or a blocked user; `med` a visible fault with a workaround; `low` cosmetic or a message. |
| fix | `#<number>` | Optional. The issue or pull request of the bug this test guards. |

**Where tags live: a manifest in the code repo**, so they work with any
language and runner. Default `test-tiers.txt` at the repo root, or the path in
`test_tiers_manifest` in `project.md`. Blank template:
`bSmart_Templates/test-tiers.template.txt`. One line per test, or per file with
a glob:

```text
<tier>   <likelihood>/<severity> <fix or -> <test id>
normal   main/high  #37      tests/test_export.py::refuses a missing file
special  edge/low   -        tests/test_format.py::*
```

- The test id is `<file>::<test name>` as the runner's JUnit report gives it
  (pytest, vitest, jest, MATLAB, go and most others can write JUnit XML).
- Exact ids win over globs; the first matching glob wins.
- `?/?` marks a test that is not tagged yet. `bTestTiers check` fails on it.
- A test name may also carry an inline tag at its end, for example
  `refuses a missing file [main/high fix #37]`. `bTestTiers init` copies it
  into the manifest and strips it from the id, so changing a tag never resets
  the test's history. The manifest is the source of truth.
- Each project wires its runner to the manifest once (for example a pytest
  selection or marker hook, a vitest project or file list, a MATLAB test
  suite built from ids). That wiring is project code, not part of bSmart.

## Two tiers

| Tier | Runs | Holds |
|---|---|---|
| normal | every change (local runs and every pull request) | everything not in special; always every `high` and every `fix` test |
| special | every 14 days, only on the main branch, only if main changed since the last special run | `edge` or `low` tests, and slow tests (over `slow_seconds`), unless `high` or `fix` |

Both tiers run in full before every release and before every merge to main,
but **only normal-tier failures block**. `bTestTiers gate --manifest M
--report R` exits 1 only for a failing normal-tier test (an untagged or
unlisted test counts as normal) and lists special-tier failures as not
blocking.

**A special-tier failure never blocks a release.** Special runs are on main,
which may already be released, so the failure goes to the next version:

1. `record` moves the failing test back to normal (see Automatic moves).
2. The agent that ran the special tier opens an issue in the repo, or adds
   it to the project's issue list when the repo has none. `bTestTiers issue
   --project P --repo N --manifest M` prints a ready-made issue body.
3. It links the issue in the run log: `bTestTiers note --project P --repo N
   --tier special --text "issue: <link>"`.
4. The fix (and its `fix #NN` regression test) goes into the next version
   through the normal flow.

Accepted risk: a rare bug can slip through between two special runs. A third,
monthly tier is a future option, not part of this rule.

**When the special tier runs.** `bTestTiers due --project P --repo N --sha S
--branch B [--commit-date D]` exits 0 when a run is due (on main, main's sha
differs from the last special run, and `special_every_days` have passed).

- **Default: an agent routine** that runs `due` on main and, when due, runs
  the special tier, records it, and handles failures as above. Hosted CI
  minutes can run out, so the default does not depend on them.
- **Optional alternative: a CI schedule** (for example weekly) that does the
  same check. Set `test_tiers_trigger: ci` in `project.md` to use it.

**Pause for inactive repos.** When main has not changed for
`pause_after_days` (default 60), the special tier pauses on its own. `due`
answers `paused (inactive): main unchanged since <date>`, and the pause is
written once to the special run log, so it never stops silently. Pass
`--commit-date` (the main commit's date) for an exact answer; without it,
the date main was first recorded at that sha is used.

**Setup and re-activation on the next run.** Every `record` (normally the
normal-tier run after a change) also checks that tiering is set up and
active for the repo. A repo without history gets it started, a missing
manifest is created from the report (tests untagged, to tag next), and a
paused repo is re-activated when a new commit is recorded. Each of these is
written as a `note:` line in the run log.

## History, in the instance

After every run (normal, special, or both), record each test's result:

```text
bTestTiers record --project P --repo N --report <junit.xml> --tier normal|special|all --sha S --branch B --manifest M
```

With `--manifest`, the same step applies the automatic moves below.

History never goes into the shared system or the code repo. It lives in the
instance:

- `<content-root>/State/test-tiers/<project>/<repo>/history.json`: per test,
  runs, fails, the current pass streak and when it began, the special-tier
  pass streak, the last result, and the slowest time.
- `<content-root>/State/test-tiers/<project>/<repo>/runs.jsonl`: one line per
  run (date, sha, branch, tier, counts, failing ids), kept for `keep_months`.
- `<content-root>/State/test-tiers/<project>/<repo>/log-normal.md` and
  `log-special.md`: the run log, one file per tier (a full `all` run goes in
  the special log, marked `(all)`). See "Run log" below.
- `<content-root>/State/test-tiers/settings.json`: the thresholds below, with
  optional per-project overrides. Template:
  `bSmart_Templates/test-tiers-settings.template.json`. Missing file means
  the defaults.

| Setting | Default |
|---|---|
| `demote_after_runs` / `demote_after_weeks` | 100 passes in a row over at least 4 weeks |
| `special_every_days` | 14 |
| `pause_after_days` | 60 (main unchanged this long pauses the special tier) |
| `slow_seconds` | 2 |
| `retire_after_special_runs` / `retire_after_weeks` | 100 special passes in a row over at least 26 weeks |
| `main_branch` | `main` |
| `keep_months` | 12 |

## Run log

Every `record` appends one compact entry to its tier's log, so the value of
the tiers can be judged over time and the settings tuned. Template:
`bSmart_Templates/test-tiers-log.template.md`.

```text
- 2026-03-02 1a2b3c4d5e main | 598 pass, 2 fail, 1 skip | 41.7s
  new failures: tests/test_export.py::refuses a missing file
  to normal: 0 (none); to special: 3 (tests/a.py::x, tests/b.py::y, tests/c.py::z)
  slowest: tests/test_render.py::full page 6.2s, tests/test_io.py::large file 3.1s, ...
```

- Entry: date, commit, branch, pass/fail/skip totals, total test time, new
  failures (tests that passed, or had not run, last time), the tier moves
  applied in this step, the three slowest tests, and `note:` lines (set up,
  re-activated, the issue link for a special failure). A pause is its own
  `paused (inactive)` entry in the special log.
- Two files per repo at most; entries older than `keep_months` are dropped
  when a new one is written.
- Read it when tuning: how often special runs find a new failure, how many
  tests move each way, and where the time goes.

## Automatic moves

`bTestTiers record ... --manifest M` applies the moves after each run and
logs them. `bTestTiers review --project P --repo N --manifest M [--apply]`
shows the same moves plus suggestions as a short report. No test is reviewed
by hand.

- **Normal to special:** a normal test that is not `high` and has no `fix`,
  after `demote_after_runs` passes in a row over at least
  `demote_after_weeks`.
- **Special to normal:** any special-tier failure moves the test back to
  normal. Its streak starts again from zero, so it needs the full
  `demote_after_runs` passes over `demote_after_weeks` again to move down.
  Tests move both ways, by their history alone.
- **Never down:** `high` and `fix` tests stay in normal for good.
- **Removal is only a suggestion:** a `low` or `edge/med` special test without
  `fix`, after `retire_after_special_runs` special passes over at least
  `retire_after_weeks`, is listed. Nothing is deleted; removing a test goes
  through the normal suite prune (`design-context.md` section 6).

Run `review` before a release or when tuning. A manifest change goes in as
an ordinary change through the normal review.

## Roles

- **Architect:** each `test_plan` entry for a new test names its tag, for
  example `refuses a missing file [main/high]`, and `fix #NN` for a
  regression test.
- **Coder:** add the new tests to the manifest with their tags, in the normal
  tier (`place` decides special only for the first classification).
- **Critic:** check the tags: present and valid, the severity fits the
  behaviour, a regression test has its `fix`, and no `high` or `fix` test sits
  in special. Run `bTestTiers check` when the project has a manifest. A wrong
  tag is a normal issue.
- **bSwarm programmer critic:** the same check, as part of the tests line.
  Before a merge to main, bSwarm uses `bTestTiers gate`: only normal-tier
  failures block.
- **Agent running the special tier:** records the run, opens the issue for
  any special failure, and links it in the log (see Two tiers).

## One-time classification of an existing suite

An agent does this once per repo, as one reviewed change:

1. Run the full suite with a JUnit report, then `bTestTiers init --manifest M
   --report R`. Every test gets a line, tagged `?/?` unless its name carries an
   inline tag.
2. Tag each test (likelihood, severity, and `fix` where the history shows a
   bug). Suggest cuts for tests that do not earn their place (section 6), but
   do not delete them in this step.
3. `bTestTiers place --manifest M --report R` sets the first tiers from the
   tags and times; `bTestTiers check --manifest M --report R` must be clean.
4. Wire the runner and the special-tier trigger, record the first full run
   with `--tier all`, and send it through the normal review.

## Trying it in a project

Try it in one project first, after its open test changes merge: classify once,
run for a few weeks, then read the review report and the history before
changing the defaults.
