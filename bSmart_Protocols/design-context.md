# bSmart Protocol: design context

```yaml
bsmart-protocol-summary:
  id: design-context
  title: Strategic note, ADR consult, project glossary, change risk, coding standards, and black-box tests
  purpose: Give the architect and critic the project's past decisions, words, and coding standards before design, keep the coder's context small, review code on two axes, keep tests few and at public interfaces, and raise review effort for changes that are hard to undo.
  load_when:
    - designing, planning, or reviewing architecture or code work in a project
    - bArchitect, bCritic, bSwarm, bAsk, or bMap work
    - writing or updating an ADR or a glossary term
    - classifying change risk (one-way or two-way door, blast radius)
    - reviewing code against the spec and the coding standards
    - planning, writing, reviewing, or pruning tests; an architecture review
```

This is the one home of these rules. bArchitect, bCoder, bCritic, bAsk, and
bSwarm point here. Everything below is optional per project: a project
without ADRs, a `glossary/` folder, or a `CODING_STANDARDS.md` works exactly
as before.

## Who reads what

| Role | Strategic note | ADRs | Glossary | Change risk | Coding standards | Tests |
|---|---|---|---|---|---|---|
| Architect | writes it | keyword search, reads matches | reads the index | classifies | copies the relevant rules | writes the test plan |
| Coder | - | none; only rules copied into the ticket | none; only terms copied into the ticket | may only raise | none; only rules copied into the ticket | follows the test plan |
| Critic | checks it | checks independently, flags misses | checks independently, flags drift | confirms or raises | standards axis of the review | flags redundant, brittle, or internal tests |
| bAsk | - | offers a new ADR (three gates) | writes confirmed terms | - | - | - |

The coder's context stays small on purpose. If an ADR, a term, or a coding
standard matters for the code, the architect copies that single rule or term
into the plan.

## 1. Strategic note

Before designing, the architect writes 2-3 lines in the plan
(`strategic_note`): is this work part of a bigger plan (a map, a roadmap, a
series of tasks), and what must it keep open or avoid because of that? If it
is a one-off, say so in one line. The critic flags a plan whose design closes
a door the note says must stay open.

## 2. ADR consult

An ADR (Architecture Decision Record) is a short file that records one
important decision and why it was made, so later agents do not undo it by
accident.

**Where.** The project's ADR folder: the `adr_path` field in `project.md`, or
`docs/adr/` when the field is missing. The folder's `README.md` is the ADR
index. No folder or no index means no ADRs: skip this step, give no note, and
never fail.

**Architect.**

1. Write a rough keyword sketch of the job: 3-8 words for the areas, modules,
   data, and interfaces it touches.
2. Search the ADR index with those keywords (a text search is enough; no
   subagent needed).
3. Read only the ADRs that match. Do not load the whole folder.
4. Use them as design research. If the plan contradicts an `Accepted` ADR,
   stop and put it to the operator as a `decision`; changing the decision
   means a new ADR that supersedes the old one.
5. List what you read in `adrs_consulted` (ADR id and one line on how it
   applies), or `none matched`.
6. Copy each ADR rule the coder must follow into `must_implement` or
   `do_not_implement` as one line, for example
   `Do not write to the cache from the UI layer (ADR-0007).`

**Critic.** Search the ADR index independently, from the plan or diff, not
from the architect's list. Flag an ADR that applies but is missing from
`adrs_consulted`, or a plan or diff that breaks one. This is a backstop for a
weak search.

**When to write a new ADR.** Only when all three gates are true:

1. Hard to reverse: changing your mind later is costly.
2. Surprising without context: a future reader will wonder why.
3. A real trade-off: there were genuine alternatives.

Most work writes no ADR, and that is fine. Prefer the short template
(`bSmart-Extensions/bADR/templates/template-short.md`, 1-3 sentences); use
the full one when the alternatives really matter. Add the new record to the
index with its keywords in the same step. A new or changed ADR follows the
project's normal decision rules; the operator agrees before it is `Accepted`.

## 3. Project glossary

A project glossary is the project's shared language: one agreed word per
domain idea, with the words to avoid. It is not the Library `glossary/`
topic, which logs user corrections across the instance
(`bSmart_Protocols/knowledge.md`, habit 6).

**Layout.** A `glossary/` folder next to the project's `knowledge/`, never
inside it. Created only when the first term is confirmed; nothing is
pre-created.

```text
<project>/glossary/
├── index.md      # every term in this folder, one line each
├── RELATED.md    # optional: links to other glossary folders, with a label
├── A.md ... Z.md # optional detail, one file per first letter, created when needed
└── 0.md          # optional detail for terms that start with a digit or symbol
```

- `index.md` is a flat alphabetical list, one line per term, one sentence of
  at most 25 words, then optional `_Avoid:_` synonyms and a pointer to the
  letter file. Template: `bSmart_Templates/glossary-index.template.md`.
- A letter file holds the longer entry: what the term is (not how it is
  built), and the words to avoid. Usually the index is enough. Template:
  `bSmart_Templates/glossary-letter.template.md`.
- File a term under the first letter of its written name, ignoring case.
- `RELATED.md` lists other glossary folders by relative path with a context
  label, such as `parent` or `shared data model`. Links, not imports: never
  copy another glossary's entries into this folder. Template:
  `bSmart_Templates/glossary-related.template.md`.
- Vocabulary only: no implementation detail, specs, or how-to. Those belong
  in `knowledge/`.

**Module glossaries.** A module with its own language keeps its glossary
with its code: a `glossary/` folder in the module's code repo, next to the
module's code (for example `<repo>/glossary/` or
`<repo>/src/<module>/glossary/`). Its `RELATED.md` links to the parent or
system glossary with the label `parent`. The project-level `glossary/` (or
the folder in `glossary_path`) is the parent for the project's modules.

```text
<project>/glossary/              # parent: shared terms
<repo>/src/<module>/glossary/    # module: its own terms only
  index.md
  RELATED.md                     # - [parent](<relative path>/glossary/index.md) - <project> core: parent
```

Use a relative link that resolves on every machine that has both checkouts;
a link that does not resolve is reported as `glossary_broken_link`.

**Discovery.** `bKnowledgeCheck` finds glossaries without a list:
`glossary_path` (or `<project>/glossary/`), every `glossary/` folder under
the project folder, and every `glossary/` folder in the repos listed in
`project.md` as `module_repos` (for repos kept outside the project folder).
It skips hidden folders (such as `.git`), `knowledge/`, dependency folders
(`node_modules`, `vendor`, virtual environments), build output, `data/`, and
`sandbox/`, and stops 6 folders deep. At startup it uses only the time left
after the knowledge check; when that runs out, the remaining glossaries wait
for the next full run.

**Lookup.** Missing folder or index: skip, give no note, never fail.

1. Read the local `index.md`. If the term is there, open only its letter file,
   and only when the line is not enough.
2. Not there: read `RELATED.md` and the indexes of the linked folders. One hop
   only; do not follow their `RELATED.md`.
   In a module, that is usually the parent.
3. Still not there: it is not in the glossary. Do not invent an official
   word; say so or research.

**AI coding vocabulary.** For general AI-coding terms (agent, context
window, prompt, and so on), the default external reference is
[The AI Coding Dictionary](https://www.aicodingdictionary.com/), a
plain-English glossary. Open it only when such a term is unclear; never load
it by default, and never copy its entries into a project glossary. A project
may list it in `RELATED.md` with the label `AI coding vocabulary`; an
external link is not part of the one-hop lookup.

**Parent and module.**

- Shared terms live only in the parent; module terms only in the module.
- A module must not redefine a parent term. The same term in both is an error:
  same meaning, remove it from the module; different meaning, flag it as a
  `decision`, and the parent wins until the operator decides.
- Siblings need not agree and are not read unless linked in `RELATED.md`.

**Roles.**

- Architect: read the local index (and one hop when a needed term is not
  local). Use those words in the plan. Copy every term that binds the coder
  into `glossary_terms` (term and one sentence).
- Coder: use only the copied terms. Never write the glossary; report a new
  word for the architect or critic.
- Critic: read the indexes independently. Flag missed terms, names that use an
  `_Avoid:_` synonym (naming drift), and parent/module conflicts. The critic
  proposes; it does not write official entries.
- Writers: only the architect, or bAsk during an interview.

**Admission bar.** A term goes in only when all are true:

1. It is a domain or project word, not a general programming word (timeout,
   function, test, and so on).
2. The user or a confirmed design uses it as the canonical word, or synonyms
   or ambiguity have actually appeared.
3. It can be defined in one or two sentences of what it is.
4. The right folder is clear (parent or module). If not, ask.
5. It is not already in the local or a linked index, as a term or an
   `_Avoid:_` synonym.

A changed meaning needs the same confirmation as a new term; typo and
slimming fixes do not. Write the index line and the letter entry in the same
step.

**Upkeep.** Part of `knowledge_upkeep`, not a separate ritual. After a code
change, also search `glossary/index.md` for the touched names. A term that no
longer matches is updated or pruned by the architect (or the critic flags it).
New candidates go into the report as one line each (term, sentence, why it
passes the bar); they are not admitted automatically. "Save on your own" does
not apply to the glossary. Rename code to an admitted term only in files
already being changed; offer a wider rename, never start one. The report says
what glossary changed, or "no glossary changes needed". When a term is
touched, slim it: drop implementation detail and terms that became generic,
duplicated, or unused.

`bKnowledgeCheck` also checks every glossary it discovers (see "Discovery")
and reports only; `--fix` never writes a glossary. Suggested new terms appear
only in task reports, not at startup.

## 4. Change risk: one-way doors and blast radius

A two-way door can be walked back: reverting the change undoes the harm. A
one-way door cannot: data loss, a message sent to many people, a destructive
migration, a removed public interface, an irreversible format change, a
hard-to-reverse product decision. Blast radius is how much is hit if it goes
wrong: `small` (local, easy to contain), `medium` (several modules or a
noticeable user-facing part), `large` (many users, production data,
installers, or external contracts).

```yaml
change_risk:
  door: two-way | one-way
  blast_radius: small | medium | large
  why: <one sentence>
```

- The architect classifies in the plan (and on any high-risk task), from the
  goal as well as the expected diff.
- The coder may only raise the class, with one line why; never lower it.
- The critic confirms or raises it. A downgrade needs a one-line reason in the
  review. Be most suspicious of a self-graded `two-way` / `small`.
- A project may list changes that are always one-way in `project.md`
  (`one_way_examples`). Without a list, use the definitions above.

**What escalates.** Automatic. No new approval gate: the run pauses only for
the existing `decision` and HOLD rules.

| Door | Blast | What the agents do | What the user sees |
|---|---|---|---|
| two-way | small | Normal path. | One line in the report. |
| two-way | medium, large | Normal path. | One risk line in the report. |
| one-way | small | Stricter critic. | Short heads-up. |
| one-way | medium, large | Stricter critic plus an extra audit with the instance's audit model. | Short heads-up, and the same block in the final report. |

- **Stricter critic.** The critic's brief adds "try to break this": the
  rollback path, data safety, side effects, and the ADRs in the area. Use a
  stronger model or higher reasoning effort when the tool allows. If the work
  has no critic step, add one critic review before the work is accepted.
- **Extra audit.** Run a design audit before substantial code and a code audit
  of the risky part, using the first model in the instance's bSwarm audit list
  (`bSmart-Extensions/bSwarm/bswarm-protocol.md`, section 3). Same review
  format as bCritic. If no audit model is configured, or the tool cannot
  select one, record the audit as `not launched` with the reason and continue
  with the stricter critic.
- If a later role raises the class, apply the new row from that point. Do not
  restart the work unless the audit cannot otherwise run.

**Heads-up.** Four short lines, as a `Change risk` block in the report (and
in the handoff and a short chat note when escalated):

- door, blast radius, and why;
- what extra review was started (stricter critic, audit model or
  `not launched`);
- outcome: passed, or the `decision` or HOLD already open;
- no question and no request for approval unless an existing `decision` or
  HOLD needs an answer.

## 5. Coding standards and the two-axis review

**Where.** An optional `CODING_STANDARDS.md` per repo or module, next to its
`glossary/` (repo root or module folder). A project that already has style
files (for example a language style guide or a lint config readme) lists
them in `project.md` as `coding_standards` instead of renaming them. The
standards for a change are the nearest `CODING_STANDARDS.md` above the
changed files, the repo-level one, and the listed files. A nearer (module)
file wins over a repo-level one for that module's code. No file and no list
means no standards: skip the standards axis with no note, never fail.

**Shape.** Template: `bSmart_Templates/coding-standards.template.md`. Start
with a `## Summary` of at most 10 one-line rules, then sections with detail.
Rules are specific and checkable ("No untyped values in public interfaces"),
not general advice ("write clean code"). A rule a tool already enforces names
the tool instead of repeating the rule.

**Architect.** Read the summary (and the sections the ticket touches). Copy
only the few rules that matter for this ticket into `standards_rules`, or
point to the summary section when it is short enough to pass whole. Never
pass the whole file.

**Coder.** Do not open the standards files. Follow `standards_rules` and run
the project's existing linters, type checks, and tests.

**Critic: two axes, always, for every code review.**

1. Spec axis: does the change do what the spec or ticket asked, no more
   (over-scope) and no less (under-scope)?
2. Standards axis: does it follow `CODING_STANDARDS.md` and the project's
   style files? Read the files yourself; do not rely on the architect's copy.

Report both axes in the review file header. A standards miss uses the normal
issue tags; it is `automatic` when a written rule is broken.

**Upkeep: turn misses into rules or checks.** Part of `knowledge_upkeep`, not
a separate ritual.

- A candidate comes from a recurring review miss: the same kind of standards
  issue in two or more reviews, or a user review comment.
- Bar: specific and checkable, not already covered by a rule or a tool, and
  likely to recur. One line. General advice never passes.
- Prefer determinism: when a linter rule, type setting, test, or pre-commit
  hook can catch it, propose that check instead of a new prompt line.
- Candidates are report-only: a `Standards candidates` line in the task
  report (rule or check, the evidence, the review ids). Nothing is written to
  `CODING_STANDARDS.md` or the tool config until the operator, or the
  project's normal decision rules, accepts it. Prune rules a check now
  enforces.

`bKnowledgeCheck` reports a `coding_standards` path in `project.md` that does
not exist (`standards_missing_file`). It does not read or rate the rules.

## 6. Black-box tests and test economy

Tests treat a module as a black box: they call its public interface (a public
function, a public class method, a package or service entry point) and check
what comes out. Then an internal refactor does not break them. Applies in
every language and test runner the project already uses.

**A test earns its place only if it locks one of these:**

1. a public contract or behaviour at a module's public interface;
2. a real bug or regression that happened;
3. a risky edge case at that same interface.

**It does not earn its place if it** pins internals (private helpers, hidden
fields, internal call counts or order), tests a trivial getter or
pass-through, is tautological (the expected value is computed the same way as
the code; use a literal, a worked example, or the spec instead), or
duplicates another test. Prefer a few tests through a narrow entry point over
many tiny tests tied to single lines.

**Architect: test plan on every ticket** (`test_plan`): the public interfaces
to test, the behaviours and edges to cover, and the existing tests that
already cover the rest. Budget: about 3-6 new tests per ticket. More needs a
one-line reason in the plan (for example several public behaviours, or a
cluster of regressions).

**Coder.** Follow the test plan. Do not add tests "for coverage". If a real
bug shows up during the work, add one regression test and say so in the
report. Test through the public interface only; if that is impossible, report
it to the architect instead of testing internals.

**Critic.** Flag tests that pin internals or are brittle, tautological, or
redundant; new tests outside the plan without a reason; a budget overrun
without a reason; and planned behaviours left untested. These are normal
issues (usually `automatic`).

**Upkeep.** A recurring test-quality miss becomes a report-only candidate the
same way as a standards miss (section 5); prefer a check (for example a lint
rule against testing private names) over a prompt line.

**Occasional reviews that only propose.** Two optional passes, run when the
operator asks, or offered before a large change or after a retro when the
shape of the code is the problem. Not every session, and not part of startup.

- **Suite prune:** list tests that no longer earn their place (internal,
  duplicate, tautological, or covered by a newer interface test), each with
  keep, merge, or delete and a one-line reason.
- **Architecture review (deep modules):** a deep module puts much behaviour
  behind a small interface. Look at recently changed hot spots for shallow
  modules and interfaces that are hard to test from outside. For each
  candidate, apply the deletion test (would removing it concentrate
  complexity behind a smaller interface, or just move it?), and give the
  problem, the proposed deepening, how the tests get simpler, and a strength
  (strong, worth exploring, speculative). Read the glossary and the matching
  ADRs first.

Both write a short markdown report in the project's `workdocs/` or the job
folder, then stop and ask which items, if any, to take further. They never
delete a test, never change code, never apply a proposal, and never open a
pull request on their own. A picked item goes through the normal flow (plan,
change risk, review). A rejected candidate with a lasting reason may be
offered as an ADR so the next review does not suggest it again.

### Only if there's an issue

- The ADR index has no keywords, so a search finds nothing: read the titles,
  then add a keywords column or line to the index (template in
  `bSmart-Extensions/bADR/templates/README.template.md`).
- `bKnowledgeCheck` reports a `glossary_conflict`: the same term is in a
  module and its parent. Follow "Parent and module" above.
- A module glossary is not checked: its repo is outside the project folder
  (list it in `module_repos`), it sits under a skipped folder, or it is more
  than 6 folders deep. Move it next to the module's code or run
  `bKnowledgeCheck --project <name>` without the startup time limit.
- An existing project keeps ADRs somewhere other than `docs/adr/`: set
  `adr_path` in `project.md`. Nothing is moved.
