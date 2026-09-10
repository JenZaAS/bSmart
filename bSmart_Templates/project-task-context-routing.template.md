# <project-name> task context routing

Purpose: keep agent context small by mapping work to the smallest useful set of project knowledge files.

## Default

Always load:

- `project.md`
- `knowledge/README.md`
- this file

Then select one or more task bundles below. Load only the task-specific knowledge bundle(s) required for the current task; do not load unrelated bundles by default.

## Task bundles

Add project-specific task bundles here. Each bundle should list only the knowledge, workstream, source-navigation, or decision files needed for that kind of task. Examples include coding/debugging/testing, UI/UX, architecture/design, documentation, and domain-specific workflows.

### General project orientation

- `knowledge/general/` only when the task needs broad project or domain orientation
- the relevant code-knowledge file only when source navigation is required

## Routing rules

- Add a bundle only when the task requires it or the first investigation shows that the initial bundle is insufficient.
- Prefer current application callers and active implementation paths over inherited helpers or stale flows.
- Register non-authoritative or legacy flows explicitly and consult their warning note before relying on them. Verify the active caller chain before using inherited or stale code paths.
- Promote stable, reusable routing conclusions into this file; keep temporary task details in the relevant workstream or workdoc.
