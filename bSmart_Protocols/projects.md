# bSmart Protocol: projects

Shared executable commands: [project-commands.md](project-commands.md) defines `/project`, confirmation and the new verified full-project retirement policy.

```yaml
protocol:
  id: projects
  title: Projects
  purpose: Create, select, and manage local bSmart projects.
```

```yaml
paths:
  project_root_selection:
    - BSMART_PROJECT_ROOT when set to a readable/writable directory
    - /projects when readable/writable
    - ./projects when readable/writable from the current bSmart/workspace folder
  index: <project-root>/INDEX.md
  handoff: <project-root>/<project>/handoff.md
  workstream_handoff: <project-root>/<project>/workstreams/<workstream>/handoff.md
  legacy_state_file: /workspace/bSmart/bSmart_State.md
  legacy_roles: /workspace/bSmart/Roles
```

```yaml
session:
  scope: this conversation only
  shared_selector: false
  empty: Free mode
  guess: never
  select: /project <name> or a plain request in the conversation
  switch: write the old project's handoff first, then print a compact startup block for the new project
```

```yaml
state_management:
  protocol: /workspace/bSmart-System/bSmart_Protocols/projects.md
  legacy_protocol: /workspace/bSmart-System/bSmart_Protocols/state.md
  rule: The session holds the active project and workstream. The project holds the handoff. Roles/ and bSmart_State.md are not selectors.
```

```yaml
path_resolution:
  rule:
    - resolve ./projects relative to the folder containing the startup hook, e.g. AGENTS.md
    - if /workspace/bSmart paths do not exist, use ./bSmart equivalents
    - report project storage setup_required when no supported project root is usable
```

```yaml
default_search_scope:
  rule: In Project mode, read, search, and list files under the active project only.
  canonical_path: /projects/<active-project>
  cross_project_access: Only when the operator explicitly requests it or the task clearly requires comparison across projects.
  project_listing_exception: Listing immediate project names is allowed; do not recursively scan sibling projects.
  shared_files_exception: Load bSmart-System, instance state, and relevant shared protocols when required by the startup or task.
```

```yaml
list_projects:
  procedure:
    - select project root using project_root_selection
    - list immediate child directories in the selected root
    - treat a child as a bSmart project when it contains project.md or README.md
    - also show plain child directories separately when they may be source/project folders without bSmart metadata
    - include the selected project root in the response so the operator can spot path mistakes
  output_style:
    - concise bullets
    - group archived folders such as _archive separately when present
```

```yaml
project_structure:
  required:
    - README.md
    - project.md
    - data/README.md
    - sandbox/README.md
    - knowledge/README.md
    - knowledge/task-context-routing.md
    - knowledge/general/
    - knowledge/code/
    - decisions.md
    - workdocs/README.md
  meaning:
    data: Raw/supporting project material such as inputs, exports, screenshots, source artifacts, and temporary research notes.
    knowledge: Curated reusable knowledge specific to this project. `knowledge/task-context-routing.md` maps task types to the smallest useful knowledge bundles and should be consulted before substantial work. Load only the relevant bundle rather than the complete knowledge tree. `knowledge/general/` holds file-independent project/domain knowledge; `knowledge/code/` holds source-specific or codebase-navigation knowledge. Use the global Library only when the material is broadly reusable across projects or the bSmart instance. `knowledge/` is preferred over `library/` inside projects to avoid confusion with software libraries.
    decisions: A single project decision file for choices, approvals, rejected options, and migration/design decisions specific to this project.
    workdocs: Project-local working documents for larger or multi-session work within this project.
    sandbox: Disposable or derived execution/build/test workspace notes; not the source of truth.
  onboarding_rule: Create these defaults for new projects to reduce friction. If a folder stays empty, keep its README as guidance rather than asking the operator to decide up front.
  existing_project_rule: Existing projects do not need a forced migration. If an existing project lacks `knowledge/`, `knowledge/general/`, `knowledge/code/`, `decisions.md`, or `workdocs/` and the operator asks to add one, create the missing standard file/folder from the corresponding template or the knowledge protocol.
```

```yaml
templates:
  project: /workspace/bSmart-System/bSmart_Templates/project.template.md
  project_task_context_routing: /workspace/bSmart-System/bSmart_Templates/project-task-context-routing.template.md
  project_knowledge_readme: /workspace/bSmart-System/bSmart_Templates/project-knowledge.README.template.md
  project_decisions: /workspace/bSmart-System/bSmart_Templates/project-decisions.template.md
  project_workdocs_readme: /workspace/bSmart-System/bSmart_Templates/project-workdocs.README.template.md
```

```yaml
project_md_required_fields:
  - project_name
  - status
  - owner
  - objective
  - agent_focus
```

```yaml
create_project:
  default_after_creation: the session that created the project selects it
  rule: `/project add NAME` creates the project, updates INDEX.md, and selects it in this session only. If this session already has a project, write that project's handoff before switching.
```

## Project index

`projects/INDEX.md` has one line per project:

```text
name | label | aliases | description | status
```

`status` is `active` or `archived`. Only `/project` commands update an existing index: add, rename, retire (archive), delete, and label, description, or alias changes. bStart reads the index and prints active projects. Archived projects stay hidden until `/project list --all`.

If the index is missing, bStart or `/project list` creates it from the project folders and `project.md`. If the index exists but folder names disagree, bStart flags the mismatch and offers `/project index repair`. Repair adds lines for folders the index does not name. It does not delete existing lines.

The label is the short tag used in operation tags, for example `DSW`. A new project gets a provisional label from its name. Change it with `/project label`.

## Project awareness

In Free mode, casual chat stays casual. When real work, a decision, or knowledge appears, suggest placing it in a matching project or creating one. Match on the index name, label, and aliases.

If the conversation drifts to a different project's topic, ask once whether to switch or only note it. Never switch silently. If the operator says to stay, do not ask again in that session.

## Handoff

Selecting a project loads its handoff. Selecting a workstream loads that workstream's handoff. Parallel sessions on the same project use different workstreams so their handoffs stay separate.

On a project change, write a short wrap-up into the old handoff first. Do not replace existing handoff text; append the new note. Then print the new project's compact startup block. Shared writes to the index and to a handoff use `.bLock`.
```
