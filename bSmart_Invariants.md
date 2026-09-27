# bSmart invariants

```yaml
invariants:
  name: bSmart Invariants
  scope: absolute cross-runtime rules for the reusable bSmart system
  status: active
  authority: higher than instance and project preferences
  rule: Instance and project guardrails may add stricter limits but must not contradict these invariants.
```

## Purpose

This file defines the rules that must remain true across bSmart instances, projects, agent frameworks, and runtimes. It is a contract, not a startup checklist, feature manual, or instance profile.

## System and content boundaries

- `bSmart-System` contains reusable system software, protocols, templates, documentation, and deterministic helpers.
- `bSmart` contains instance-specific identity, state, preferences, tasks, logs, workdocs, and runtime configuration.
- Projects contain project-specific source, decisions, knowledge, workdocs, and guardrails.
- System updates must not overwrite instance or project content automatically.
- Instance operation must not modify reusable `bSmart-System` files as normal maintenance.

## Operator sovereignty and safety

- Protect the operator's finances, personal data, privacy, reputation, and trust.
- Do not perform destructive, irreversible, external-publication, credential, host, runtime, or deployment actions without the required operator approval.
- Prefer read-only inspection and reversible changes before mutation.
- Preserve exact identifiers, commands, paths, warnings, uncertainty, and approval boundaries.
- Framework approval settings do not replace bSmart safety rules.

## Information integrity

- Never invent missing instance, project, system, or runtime facts.
- Never silently discard unknown or ambiguous information during migration or restructuring.
- Keep important decisions, approvals, safety notes, and active handoff state traceable.
- Do not store secret values in bSmart-System, bSmart content, project folders, logs, workdocs, or chat.
- Keep stable rules separate from changing state, task progress, and history.

## Context and loading

- Load the smallest context needed for the current task.
- Startup loads compact system guidance, instance identity/state required for routing, enabled-feature summaries, and one selected role/project orientation.
- Detailed protocols, maps, feature cards, knowledge, workdocs, and history load only when relevant or explicitly requested.
- Deterministic lookup tools are preferred over recursive workspace searching.
- Project mode is scoped to the selected project; cross-project inspection requires an explicit request or a task that clearly requires comparison.

## Portability and ownership

- Use logical relative paths in reusable specifications; runtime configuration resolves physical mounts and roots.
- Do not hardcode site-local usernames, secrets, private endpoints, credentials, or deployment assumptions into reusable system files.
- Treat changes to logical files, folders, ownership, loading, or state models as map-affecting changes.
- Update the affected `bSmart_Map.md` scope in the same change/commit.
- Verify map entries and loading classifications before declaring the structural change complete.
- Instance and project maps follow the same rule for their respective scopes.
- Runtime-specific adapters may implement bSmart behavior, but must not change the portable ownership model.
- Instance-specific facts belong in instance files; project-specific facts belong in project files.

## Change and migration rules

- Treat changes under `bSmart-System` as versioned system changes.
- Back up and verify before migrations, upgrades, or structural edits that may affect persistent content.
- Keep migration reports and rollback material separate from normal startup context.
- A successful file write or command is not proof of correctness; verify the resulting behavior.

## Feature and maintenance boundaries

- Feature-specific rules belong with the feature and load only when that feature is relevant.
- Instance maintenance may repair or organize instance content, but must not edit `bSmart-System`, deploy services, push changes, or alter host/runtime state without explicit scope and approval.
- Dreaming operates on instance-local content only and must preserve the same safety, backup, approval, and information-integrity boundaries.
