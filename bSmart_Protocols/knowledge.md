# bSmart Protocol: knowledge

```yaml
bsmart-protocol-summary:
  id: knowledge
  title: Project knowledge and bKnowledge
  purpose: Create, classify, retrieve, and maintain concise reusable knowledge without confusing source navigation with general knowledge or active work notes.
  load_when:
    - bKnowledge
    - create bKnowledge
    - project knowledge
    - code knowledge
    - source navigation
```

## Storage and separation

Project-local knowledge is stored under the active project:

```text
/projects/<active-project>/knowledge/
├── general/   # project/domain concepts, decisions, relationships, and reusable facts
└── code/      # source-specific or codebase-navigation knowledge
```

`workdocs/` remains for active working notes, investigations, handoffs, and detailed reasoning. Do not use a workdoc as the final home for a concise reusable knowledge item. Use the global bSmart Library only when the knowledge is reusable across projects or across the bSmart instance.

Knowledge does not have to be tied to a file. File-independent items belong in `knowledge/general/` and may describe a domain concept, cross-component relationship, decision, invariant, workflow, or open question. Code knowledge may also be cross-cutting; use `knowledge/code/` when its primary purpose is helping an agent navigate or extend a codebase, even if it references several files rather than one source file.

## Natural-language intent

Treat the following as a bSmart intent, not as a request for a long prompt:

```text
create bKnowledge <source>
```

`<source>` may be either a project filename or a URL.

Examples:

```text
create bKnowledge DIG_Calibrate
create bKnowledge DIG_Calibrate.m
create bKnowledge DTM_ModelTemplates
create bKnowledge https://example.com/design-document
create bKnowledge https://github.com/org/repo/blob/main/src/DIG_Calibrate.m
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
3. Store documentation, domain concepts, and cross-project facts in `knowledge/general/` unless their primary purpose is code navigation.
4. Store source-code and codebase-navigation summaries in `knowledge/code/`.
5. Preserve the exact source URL, page title when available, and repository/branch/commit information when the source provides it.
6. Prefer stable raw-file, release, or commit-pinned URLs for source-code knowledge when available. Do not silently treat a mutable branch URL as immutable evidence.
7. If the page is blocked, requires login, or cannot be retrieved reliably, report that and ask for an accessible URL, pasted content, or local path. Do not invent knowledge.

URL knowledge items should include source metadata such as:

```md
- Source: `<exact URL>`
- Source type: documentation | article | specification | source code
- Retrieved: <date, when known>
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

Create the file under:

```text
/projects/<active-project>/knowledge/code/<stable-slug>.md
```

Use a lowercase hyphenated slug based on the source basename, retaining a meaningful MATLAB class/function identity. Examples:

```text
DIG_Calibrate.m        -> dig-calibrate.md
DTM_ModelTemplates.m   -> dtm-modeltemplates.md
```

Use this concise structure:

```md
# <Component or file name>

- Source: `<exact source path>`
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

## Verification and refresh

After writing:

1. Read the generated knowledge file back.
2. Verify that the exact source path appears.
3. Verify that recommended bSelective targets appear.
4. Report the generated path and a short summary.
5. Mention when MATLAB runtime validation was unavailable; static bSelective inspection is not runtime validation.

Refreshing an existing item should preserve its stable filename, replace stale facts only when the source supports the change, and retain explicit open questions when they remain unresolved.
