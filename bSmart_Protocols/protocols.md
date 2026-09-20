# bSmart protocol index

```yaml
protocol_index:
  purpose: Route an agent to the smallest relevant reusable protocol.
  loading: Read this index during startup; load one or more detailed protocols only when the task requires them.
  rule: This file contains summaries and ownership only, not duplicated procedures.
```

| Protocol | Scope | Load when |
|---|---|---|
| `bootstrap.md` | Session startup order, fresh-agent bootstrap, and verification | Starting, installing, or repairing bSmart |
| `startup-hooks.md` | AGENTS.md/HERMES.md hook content and hook helper behavior | Creating or troubleshooting startup hooks |
| `operations.md` | Safe action cadence, approvals, secrets, and traceability | Any action with safety or approval implications |
| `state.md` | Legacy `bSmart_State.md` migration rules | Migrating an older instance to role-owned state |
| `projects.md` | Project structure, project focus, and project-context boundaries | Creating, listing, selecting, or opening projects |
- `project-commands.md` | Hermes `/project` command behavior and lifecycle actions | Using or testing `/project` commands |
| `project-storage.md` | Project and sandbox roots, mounts, setup prompts, and storage checks | Configuring or troubleshooting project storage |
| `workdocs.md` | Structured workdocs and larger multi-session work | Creating or maintaining a workdoc |
| `knowledge.md` | Reusable knowledge storage and retrieval boundaries | Creating or searching bKnowledge |
| `history.md` | Concise completed-work diary rules | Recording or reviewing completed work |
| `dreaming.md` | Scheduled instance-content maintenance and Dreaming safety | Configuring, running, or reviewing Dreaming |
| `instance-git-onboarding.md` | Optional Git for instance content and projects | Configuring instance/content Git |
| `roles-and-concurrency.md` | Role selection, role-owned state, shared projects, and `.bLock` file concurrency | Selecting roles or handling concurrent writes |
| `secret-provider-onboarding.md` | Credential-provider choices and secret boundaries | Configuring a feature that needs credentials |
| `github-ai-access.md` | Generic GitHub access and AI-account patterns | Configuring or troubleshooting GitHub access |
| `local-agent-onboarding.md` | Explicit local-agent onboarding for host/Docker agents | Starting local-agent onboarding |
| `admin-container-design.md` | Design boundaries for admin/container instances | Designing an admin AI container |
| `security-watch.md` | Read-only security drift monitoring and ownership | Configuring or running Security Watch |
| `bAccountant-onboarding.md` | Optional bAccountant setup and boundaries | Enabling or configuring bAccountant |

## Ownership rules

- `bSmart_Setup.md` owns the interactive setup sequence, questions, defaults, and links to protocols.
- Individual protocol files own detailed behavior, constraints, commands, and verification for one domain.
- `bSmart.md` owns startup routing and the order in which compact metadata is loaded.
- `bSmart_Invariants.md` owns absolute cross-runtime rules and overrides conflicting lower-level guidance.
- Instance and project files own local facts and preferences; they must not duplicate generic procedures.
