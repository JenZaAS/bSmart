# bSmart Protocol: knowledge

```yaml
bsmart-protocol-summary:
  id: knowledge
  title: Knowledge handling, layout, and bKnowledge
  purpose: Find knowledge before guessing, save useful findings without being asked, and keep the Library and project knowledge sorted into indexed topic folders.
  load_when:
    - an unfamiliar name, term, tool, or reference
    - saving a finding, reference, or decision
    - the user corrects a term or reference
    - bKnowledge
    - create bKnowledge
    - project knowledge
    - code knowledge
    - source navigation
    - after modifying, fixing, or refactoring code
    - bStart prints a Knowledge line
    - bKnowledgeCheck
    - before a handoff
```

## Habits

These run on their own. Do not ask the user to approve them or to organise knowledge.

1. **Look before guessing.** Before you ask about or guess an unfamiliar name, term, tool, or reference, search in this order: the active project's `knowledge/index.md`, the Library `index.md` (including `glossary/`), then the notes themselves (search both knowledge roots for the name), then your own memory. Use what you find. If nothing matches, say "not found in knowledge" and then ask or research.
2. **Save before replying.** When you learn something worth reusing, even while answering a question, create or update a short, factual note on disk before sending your final reply. If you learn both general and project-specific facts, save the reusable general facts in the Library and the project-specific facts in project knowledge. Keep Library notes free of project and client names and local decisions. Each note has a `Source:` line (URL, file, or "user, in chat") and a `Date:` line. No secrets or personal data.
3. **Pick the place.** Project-specific: the project's `knowledge/`. Useful beyond the project: the instance Library. Apply the project fallback only to individual facts whose reuse is unclear, and move them to the Library when a second project needs them. When a finding contains both reusable and project-specific facts, create or update both notes. The Library note is required even if the project note includes the same reusable facts.
4. **Topic folders only.** Put each note in a topic folder (see "Layout"). Never put a note directly in a knowledge root, or directly in `tools/` or `general/`. Create a new topic when nothing fits.
5. **Index in the same step.** A new note gets its line in its topic's `index.md`, and a new topic gets its line in the parent index, in the same step that creates it.
6. **Corrections become knowledge.** When the user corrects a term, name, or reference, save the correction in the Library `glossary/` topic (create it the first time): one note per term with the right meaning, the wrong reading to avoid, the source ("user correction"), and the date. Then every agent finds it with habit 1. A correction of a word in a project's own glossary goes to that project's `glossary/` folder instead (`bSmart_Protocols/design-context.md`); do not write the same definition in both.
7. **Keep it tidy.** Run `bKnowledgeCheck` (below) when startup reports a Knowledge line and before a handoff. Fix the findings yourself and log what you change.

## Layout

There are two kinds of knowledge root:

- the instance Library, `<content-root>/Library/` (one per instance; reusable across projects);
- each project's `knowledge/` folder (`/projects/<project>/knowledge/`).

Both use the same layout. Every folder below a root is a topic. Topics nest to any depth.

```text
<knowledge root>/
├── index.md                 # topics only, one line each
├── CHANGELOG.md             # change log for this root (bKnowledgeCheck and agents)
├── README.md                # optional catalogue or guidance
├── task-context-routing.md  # projects only: task-to-knowledge bundles
├── code/                    # default: code knowledge
│   ├── index.md
│   ├── <note>.md            # language-agnostic notes may sit directly in code/
│   └── matlab/              # one subfolder per language
│       ├── index.md
│       └── <note>.md
├── tools/                   # default: apps, services, external references
│   ├── index.md
│   └── <some-app>/
│       ├── index.md
│       └── <note>.md
├── general/                 # default: last resort only
│   └── index.md
└── <domain-topic>/          # any other topic an agent creates, e.g. a subject area
    ├── index.md
    └── <note>.md
```

- `code/`, `tools/`, and `general/` are the defaults. Do not add more defaults; create topics as you go.
- `code/` holds source-specific or codebase-navigation knowledge. Language-agnostic notes may sit directly in `code/`; language notes go in `code/<language>/`.
- `tools/` holds one subfolder per app, service, or external reference, such as `tools/<some-app>/`.
- `general/` is the last resort. Use it only when no topic fits and none is worth creating yet. The check lists notes there so they can move when a better topic appears.
- Domain topics (a subject area) can sit at the root next to the defaults.
- Allowed directly in a root, as housekeeping rather than notes: `README.md`, `index.md`, `CHANGELOG.md`, `CATEGORIES.md`, and `task-context-routing.md`. Any other file there is a loose note.
- A root has no `knowledge/` subfolder; the Library root is itself the knowledge root.
- A folder holding only attachments (images, PDFs) is not a topic and needs no index.

`workdocs/` remains for active working notes, investigations, handoffs, and detailed reasoning. Do not use a workdoc as the final home for a concise reusable knowledge item.

Knowledge does not have to be tied to a file. A domain concept, cross-component relationship, decision, invariant, workflow, or open question goes in the topic it is about. Code knowledge may also be cross-cutting; use `code/` when its main purpose is helping an agent navigate or extend a codebase, even if it references several files.

## Indexes

Two levels, so an agent reads two short files instead of many:

- The root `index.md` lists topics only, one line each: `- [tools/](tools/index.md) - apps, services, and external references`.
- Each topic's `index.md` lists its notes and subtopics, one line each: `- [some-note](some-note.md) - what this note answers`.

An existing `README.md` in a topic, or a catalogue `README.md` at the root, also counts as that folder's index. Keep it; `bKnowledgeCheck` adds an `index.md` that points to it when entries are missing. Templates: `bSmart_Templates/knowledge-index.template.md` and `bSmart_Templates/knowledge-topic-index.template.md`.

Project task bundles in `knowledge/task-context-routing.md` point into these topics. The indexes find a note; the routing file says which notes a task needs.

## Check and fix: bKnowledgeCheck

```text
python <system>/scripts/bKnowledgeCheck            # report; exit 0 clean, 1 findings
python <system>/scripts/bKnowledgeCheck --fix      # safe fixes, logged
python <system>/scripts/bKnowledgeCheck --project <name>
```

It checks the Library and every project's `knowledge/` and reports: notes directly in a root (`root_file`) or directly in `tools/` or `general/` (`default_root_file`), a `knowledge/` folder inside a root (`nested_root`), topics without an index (`missing_index`), notes or subtopics missing from their index (`unindexed`), index links to missing files (`broken_link`), placeholder descriptions (`placeholder`), and, as advisory only, notes under `general/` (`general_note`).

`--fix` does only the mechanical part: it creates a missing `index.md`, adds missing index lines with the placeholder `TODO: one-line description`, and removes broken links (an `index.md` list line is removed; in a `README.md` the link text stays). It never moves a note and never picks a topic.

The rest is yours, without asking the user: move loose notes into topics (create the topic if needed), replace placeholders with a real line, and move notes out of `general/` when a better topic fits. Run the check again until it is clean.

**Change log.** Every change goes to `<knowledge root>/CHANGELOG.md`: `bKnowledgeCheck --fix` and the migration write it themselves; you add a line for each move or rename you make, in the same form (`- <date> <who>: moved <old> to <new>`).

**When it runs.** `bStart.py` runs `bKnowledgeCheck --summary` at startup. It prints one `Knowledge:` line only when there is something to do, stops walking after about one second, and never blocks startup. When you see that line, fix the findings during the session. Before writing a handoff, run the check for the project (and the Library if you touched it) and fix what it finds.

**Project and module glossaries.** The check also looks at each project's `glossary/` folder (a sibling of `knowledge/`) and at module glossaries in the project folder and in the repos listed in `module_repos` (discovery and rules in `bSmart_Protocols/design-context.md`), and reports `glossary_missing_index`, `glossary_stray_file`, `glossary_unindexed` (a letter file the index never points to), `glossary_broken_link` (in `index.md` or `RELATED.md`), `glossary_empty_file`, `glossary_conflict` (a term also in a linked `parent` glossary), and, as advisory only, `glossary_long_line` (an index line over 25 words). It also reports a `coding_standards` path in `project.md` that does not exist (`standards_missing_file`). It only reports: `--fix` never writes a glossary or standards file, because only the architect or bAsk writes terms and standards change only when accepted. Use the same moments (a Knowledge startup line, before a handoff) for a short slimming pass over the glossary index.

## One-time migration (0.1.56)

The first time an instance runs this version, its knowledge is brought into this layout once:

1. `bsmart-update` (through `bsmart-instance-upgrade`) runs `bKnowledgeCheck --migrate`. It moves any `<root>/knowledge/*` content up into the root (never overwriting; a clash is listed), creates `code/`, `tools/`, and `general/` with an `index.md`, creates or extends indexes, removes broken links, logs every change in each root's `CHANGELOG.md`, and lists the loose notes.
2. You sort each listed note into a topic folder, add its index line, log the move in `CHANGELOG.md`, then run `bKnowledgeCheck --migrate` again.
3. When nothing is left to sort, it writes `status: done` to `<content-root>/State/knowledge-migration.yaml` and never runs again (`--force` reruns it).

Until the marker says done, startup prints a `Knowledge: one-time layout migration pending` line. If the instance was updated without `bsmart-update`, run step 1 yourself when you see it. No user approval is needed; READMEs are never deleted.

### Only if there's an issue

- The startup line says the check stopped at the time limit: the disk is slow. Run `bKnowledgeCheck` without `--summary` when convenient. `BSMART_KNOWLEDGE_CHECK=0` turns the startup check off.
- The migration lists a clash (`conflict, not moved`): the same path exists in the root and in `knowledge/`. Compare them, merge by hand, delete the copy you merged, log it, and run `--migrate` again.
- A topic keeps its notes in `README.md` and the check still reports `unindexed`: the README does not name the file. Add the line to the topic's `index.md`, or run `--fix`.
- `State/knowledge-migration.yaml` cannot be written: the content root is read-only. The check still works; the pending line stays until the marker can be written.

## Natural-language intent

Treat the following as a bSmart intent, not as a request for a long prompt:

```text
create bKnowledge <source>
```

`<source>` may be either a project filename or a URL.

Examples:

```text
create bKnowledge calibrate_sensor
create bKnowledge calibrate_sensor.m
create bKnowledge DTM_ModelTemplates
create bKnowledge https://example.com/design-document
create bKnowledge https://github.com/org/repo/blob/main/src/calibrate_sensor.m
```

The intent creates or refreshes one concise knowledge/navigation Markdown item. It does not modify a project source file or remote source.

## Filename resolution

1. Resolve the active project using the State and Projects protocols before searching for the source.
2. Search the active project/codebase recursively for a source file matching `{filename}` exactly, including the supplied extension.
3. If the extension is omitted, accept a unique basename match and prefer source files over generated/build/cache artifacts.
4. If more than one plausible match remains, stop and ask the operator to choose; do not guess.
5. If no match exists, report that clearly and ask for the source path. Do not create an ungrounded code-knowledge file.
6. Preserve the exact resolved source path in the generated knowledge item.

## URL sources

When `<source>` is an HTTP(S) URL:

1. Fetch and inspect it read-only, using the available web extraction/browser tools.
2. Classify the source as documentation, article, specification, repository information, or source code.
3. Store documentation and references about an app, service, or external project under `tools/<some-app>/`, domain concepts under their topic, and use `general/` only as the last resort.
4. Store source-code and codebase-navigation summaries under `code/` (`code/<language>/` for language-specific ones).
5. Preserve the exact source URL, page title when available, and repository/branch/commit information when the source provides it.
6. Prefer stable raw-file, release, or commit-pinned URLs for source-code knowledge when available. Do not silently treat a mutable branch URL as immutable evidence.
7. If the page is blocked, requires login, or cannot be retrieved reliably, report that and ask for an accessible URL, pasted content, or local path. Do not invent knowledge.

URL knowledge items should include source metadata such as:

```md
- Source: `<exact URL>`
- Source type: documentation | article | specification | source code
- Date: <retrieved, when known>
- Confidence: verified from source; hypotheses/open questions are labelled below
```

For a URL pointing to a MATLAB source file, apply the MATLAB procedure below after retrieving or otherwise making the source available to bSelective. Preserve the URL as the external source reference; do not modify or clone the remote source unless explicitly requested.

## MATLAB `.m` procedure

For a resolved MATLAB file, use bSelective progressively and read-only:

1. Run `list FILE all --compact`.
2. Run `list FILE functions --format text`.
3. Retrieve only relevant regions with targeted `get` calls, such as the header/help block, class outline, properties, constructor, callbacks, public entry points, important methods, local functions, and references.
4. Use targeted line/context retrieval when a relationship or constraint cannot be established from a function/method target.
5. Avoid `get FILE all` unless the file is small or the requested knowledge genuinely requires whole-file context; record that escalation in the knowledge item.
6. Never modify the source file as part of this workflow.

The exact command syntax is defined by the bSelective command-handler specification. For future agents, record the useful retrieval targets and their purpose rather than copying tool transcripts.

## Knowledge item structure

Create the file under the language topic, and add its line to that topic's `index.md` in the same step:

```text
/projects/<active-project>/knowledge/code/<language>/<stable-slug>.md   # e.g. code/matlab/
```

Use a lowercase hyphenated slug based on the source basename, retaining a meaningful MATLAB class/function identity. Examples:

```text
calibrate_sensor.m     -> calibrate-sensor.md
DTM_ModelTemplates.m   -> dtm-modeltemplates.md
```

Use this concise structure:

```md
# <Component or file name>

- Source: `<exact source path>`
- Code: `<path>` — `<function>`, `<function>`
- Knowledge type: code navigation
- Confidence: verified implementation facts; hypotheses/open questions are labelled below

## Purpose

## State and data structures

## Entry points and functions

## Relationships

## Extension points

## Pitfalls and constraints

## Recommended bSelective targets

- `list ...`: why it matters
- `get ...`: why it matters

## Open questions / hypotheses

- None, or explicitly labelled items.
```

Include, when present:

- exact source path;
- component/class purpose;
- key state and data structures;
- main entry points, callbacks, and functions;
- important UI/API/backend relationships;
- likely extension points;
- pitfalls and design constraints;
- recommended bSelective retrieval targets for future agents.

Keep it orchestration-oriented and concise. Summarize relationships and targets; do not reproduce the source file or write a broad architecture essay. Distinguish verified facts from hypotheses and open questions.

## Code references and upkeep

Any entry that describes code, in any topic, names that code in one line:

```md
- Code: `src/sensor/calibrate.py` — `calibrate_sensor`, `load_offsets`
```

Use one `Code:` line per file. Searching for a path or function name then finds every entry that depends on it.

After a code change, follow `knowledge_upkeep` in `bSmart.md`: search the knowledge for the touched paths, function names, and feature names, then update or remove what no longer matches. Add a `Code:` line to an entry you touch if it lacks one.

## Verification and refresh

After writing:

1. Read the generated knowledge file back.
2. Verify that the exact source path appears and that the topic's `index.md` lists the file.
3. Verify that recommended bSelective targets appear.
4. Report the generated path and a short summary.
5. Mention when MATLAB runtime validation was unavailable; static bSelective inspection is not runtime validation.

Refreshing an existing item should preserve its stable filename, replace stale facts only when the source supports the change, and retain explicit open questions when they remain unresolved.
