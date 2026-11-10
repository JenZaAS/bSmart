# bSwarm chat protocol v1

Use this protocol when the operator asks to run a bSwarm before a dedicated command handler exists.

## 1. Draft concise run spec

Show this quick-glance summary before launching agents. Prefer the compact
workflow keyword interface unless the operator asks for internal branch/stage detail:

```text
ordinary
bSelective
architect
bSelective architect
cascade
cascade critic
cascade critic audit
```

Keyword meanings:

| Keyword | Meaning |
|---|---|
| `ordinary` | Direct ordinary coder; no bSelective context tooling. |
| `bSelective` | Direct bSelective-enabled coder. |
| `architect` | Ordinary architect → ordinary coder, using one compact handoff. |
| `bSelective architect` | bSelective architect → bSelective coder, using one compact handoff. |
| `cascade` | bSelective architect-led stepwise workflow: decompose, dispatch one coder task, evaluate, re-plan, continue. |
| `cascade critic` | bSelective cascade with same-model architect/programmer critics and bounded score-based repair loops. |
| `cascade critic audit` | `cascade critic` plus external design/code audits using the ordered instance-local audit model list. |

Normalization rules:

- `ordinary` is the default direct mode and may be omitted internally.
- `architect` implies an architect followed by a coder.
- `cascade` implies a bSelective architect-led stepwise execution; it is not a direct-coder mode.
- `bSelective` applies to all relevant stages by default.
- `bSelective architect` means bSelective architect and bSelective coder.
- `cascade` means bSelective architect, bSelective coders, and architect evaluation/replanning between tasks.
- `cascade critic` means `cascade` with maximum depth 3, one completed task at a time, and architect/programmer critics.
- `cascade critic audit` means `cascade critic` plus external design and code audits.
- `bSelective cascade` remains a synonym for `cascade`.
- bSelective is on for every cascade phrase. Opt out only when the operator explicitly requests ordinary (non-bSelective) context tools.
- Do not expose mixed bSelective architect → ordinary coder combinations as normal user-facing modes; keep them only for controlled experiments.

Internal normalization:

```yaml
ordinary:
  context_mode: ordinary
  workflow: direct
bSelective:
  context_mode: bselective
  workflow: direct
architect:
  context_mode: ordinary
  workflow: architect_handoff
  coder_context_mode: ordinary
bSelective architect:
  context_mode: bselective
  workflow: architect_handoff
  coder_context_mode: bselective
cascade:
  context_mode: bselective
  workflow: architect_taskflow
  coder_context_mode: bselective
cascade critic:
  context_mode: bselective
  workflow: critcascade
  coder_context_mode: bselective
cascade critic audit:
  context_mode: bselective
  workflow: critcascade_audit
  coder_context_mode: bselective
```

Then show the normalized run summary:

```yaml
bswarm_run:
  goal: <one-line goal>
  scope: <path/reference or none>
  workflow_keyword: ordinary | bSelective | architect | bSelective architect | cascade | cascade critic | cascade critic audit
  workflow: direct | architect_handoff | architect_taskflow | critcascade | critcascade_audit
  mode: unsupervised | supervised
  intent: review | design | compare | implement | other
  ab_testing: off | report | self_improving
  bselective: all_off | all_on | mixed_ab
  statistics: on
  max_depth: 1 | 2
  max_total_child_agents: 3
  max_iterations: 5
  max_worker_attempts_per_supervisor: 5
  safety: read_only | propose_patches | approved_writes
  branches:
    ordinary:
      pattern: direct_worker
      context_mode: ordinary
      stages: [coder]
    bselective:
      pattern: direct_worker
      context_mode: bselective
      stages: [coder]
    architect:
      pattern: architect_coder
      architect_context_mode: ordinary
      coder_context_mode: ordinary
      stages: [architect, coder]
    bselective_architect:
      pattern: architect_coder
      architect_context_mode: bselective
      coder_context_mode: bselective
      stages: [architect, coder]
    cascade:
      pattern: architect_taskflow
      architect_context_mode: bselective
      coder_context_mode: bselective
      stages: [architect, coder, architect_evaluation]
    bselective_cascade:
      pattern: architect_taskflow
      architect_context_mode: bselective
      coder_context_mode: bselective
      stages: [architect, coder, architect_evaluation]
    critcascade:
      pattern: critcascade
      architect_context_mode: bselective
      coder_context_mode: bselective
      max_depth: 3
      stages: [architect, architect_critic, coder, programmer_critic, architect_revision, coder_fix]
```

Offer: start, edit keyword, edit A/B/C branches, edit statistics, edit budgets, edit safety, cancel.

## 2. Preflight QC before launch

Before launching any run, do a short preflight QC and show blocking warnings
instead of starting a run that is likely to fail. For `architect`,
`bSelective architect`, `cascade`, `cascade critic`, and especially
`cascade critic audit`, this is
mandatory if the run expects the architect subagent itself to dispatch coder
subagents. Earlier staged handoff runs can work with lower spawn depth because
the parent/supervisor runs architect first, then manually hands the plan to a
coder; that is `supervisor_mediated_architect_handoff`, not nested architect
dispatch.

Record the detected CLI/runtime adapter. bSwarm is portable, but nested
delegation checks are adapter-specific:

- `hermes` adapter: check live Hermes config and the current tool schema.
- `opencode`, `codex`, `claude`, or unknown adapter: do not assume Hermes
  nested delegation exists; require an adapter-specific nested-worker mechanism
  or downgrade to a supervisor-mediated cascade after telling the user.

Hermes cascade preflight checks:

```yaml
preflight_qc:
  adapter: hermes | opencode | codex | claude | unknown
  required_for_nested_architect_dispatch:
    delegation.orchestrator_enabled: true
    delegation.max_spawn_depth: ">= 2"
    delegation.child_timeout_seconds: ">= planned_timeout_seconds"
  recommended_for_cascade:
    delegation.child_timeout_seconds: 1200
  required_for_cascade_critic:
    delegation.max_spawn_depth: ">= 3"
```

If a required check fails, stop and report a concise settings warning with the
exact observed value and the suggested command when known, for example:

```text
bSwarm preflight blocked: nested architect dispatch needs Hermes delegation.max_spawn_depth >= 2.
Observed: delegation.max_spawn_depth = 1.
Suggested fix: hermes config set delegation.max_spawn_depth 2, then start /new or /restart before rerunning.
```

Do not silently continue as a true nested architect/cascade run when the adapter
cannot verify nested child dispatch. Either ask the user to fix settings, or
explicitly switch the run spec to `supervisor_mediated_architect_handoff` or
`supervisor_mediated_cascade` and record that it is not true nested
architect-dispatch.

## 3. Cascade audit rules

These rules apply only to `cascade critic audit`. Internal critics remain
same-model; external auditors use other models from the ordered instance-local
list.

### Finding classes

Auditors review like a bCritic critic (`../bCritic/critic.md`): the same
checks, issue classes (`automatic`, `decision`, `optional`), and file format,
with the auditor file name from `../bCritic/critique-notes.md`.

### Instance audit model list

Each instance owns one ordered list for both design and code audits. The system
ships only the placeholder template
`templates/audit-models.template.yaml`; the real file belongs in instance
content at `./bSmart/State/bswarm-audit-models.yaml`. Keep it free of secrets.
The list is intentionally empty by default: an empty list means the audit is
**blocked until configured**.

Preflight must fail closed when the list is empty or every entry is the same
model as the implementing/critic model. Show the configured list in order and
ask the operator to change it; never silently audit with the same model.
Prefer auditors from other vendors/providers than the working team
(architect, coder, critics, parent agent); when every entry shares the
team's vendor, say so at preflight and offer any other-vendor model the tool
can use. Put a strong reviewer first: later auditors run only on `automatic`
or `decision` findings, so the first entry is the one that always runs. If the
adapter cannot name or select models, retain the intended order and record that
the auditor could not be launched.

Walk the list in order for both design and code audits. Continue only when the
current auditor produced an `automatic` or `decision` finding; optional-only
stops the list. Record the actual model id used per auditor, or explicitly
record that it could not be launched.

Operator commands (aliases may be supported):

```text
list audit models
change audit models
```

`list audit models` prints the ordered instance list and its file path, or says
that it is unset and `cascade critic audit` is blocked until set. `change audit
models` replaces the ordered list, or applies an explicit add/remove/move
request when supported, then confirms the resulting order. Do not put secrets
in the file. Different instances may have different lists without forking the
system repository.

- Run a **design audit** after the first architect plan, before substantial code.
- Run a **code audit** after the architect task list is empty by default.
- The architect may set `audit_after_task` on a high-risk task to request an
  earlier code audit for that slice.
- The next auditor runs only when the current auditor produced an `automatic`
  or `decision` item. An `optional`-only result stops the auditor list.
- A finding that the behavior is a feature is locked and commented (or
  recorded in an ADR), not silently changed.
- For a design audit, `automatic` makes the architect revise the plan;
  `decision` pauses for the operator and then updates the plan.

The job package is the durable record (section 13 says where it lives). Use
`templates/jobs/` to create `jobs/README.md`, one dated job folder, and its
`report.md` and `plan.md`. The report records each external auditor as design or code with its
class, status, and stop reason; it records optional findings as a count only.

```yaml
audit:
  enabled: true
  models_file: ./bSmart/State/bswarm-audit-models.yaml
  model_list: []
  design: after_architect_plan
  code: after_task_list_empty
  audit_after_task: false
  auditor_continue_on: [automatic, decision]
  optional_only: stop
  external_model_required: true
```

## 4. Defaults

Use these unless the operator changes them:

- simple spec/review work: `mode: unsupervised`, `max_depth: 1`, `max_total_child_agents: 3`;
- high-assurance work: `mode: supervised`, `max_depth: 2`, `max_total_child_agents: 4`;
- `max_iterations: 5`;
- `max_worker_attempts_per_supervisor: 5`;
- `statistics: on`;
- `safety: read_only`.

### Per-role models

bSwarm can run each role on its own model. The shared system only provides
this capability; it assigns no models. Which models are used is instance
configuration.

- Instance file: `./bSmart/State/bswarm-role-models.yaml`, copied from
  `templates/role-models.template.yaml`. It sets `architect`, `coder`, and
  `critic` to `session`, `same_as_reviewed` (critic only), or a
  `<provider-model-id>`. Read it at run start; a missing file means every role
  uses the session model. Auditors stay in `bswarm-audit-models.yaml`.
- Precedence per role: `role_defaults.<role>.model` in the run spec, when set
  to something other than `session` > instance file > session model.
- `same_as_reviewed` means the critic uses the model of the role it reviews:
  `architect_critic` uses the architect model, `programmer_critic` the coder
  model. This keeps section 3: internal critics stay same-model.
- Agent tools name models differently. Map the configured id to the name the
  tool accepts and record both.
- Fallback rule. The configured models (architect, coder, critic, audit) are
  the instance's intended defaults, but not every agent tool (Cursor, Codex,
  Claude Code, and others) can switch models. When the tool cannot use the
  configured model for a role:
  - if the current session model is the only one available, use it, do the
    best job possible, and log the fallback;
  - if other models are available, propose them to the user and let the user
    choose; never silently settle on a weaker substitute.
  Never fail a run only because a role model cannot be chosen. Auditors are
  the exception: they must still differ from the implementing and critic
  models, so a one-model tool records the audit as `not launched` (section 3).
- The run record logs, per role, the configured model, the model actually
  used, and whether a fallback happened.

### Choosing role models

The system names no models; these principles guide the operator and parent
agent when filling in or reviewing the instance files.

- **Review every run.** Before a `cascade critic` or `cascade critic audit`
  run, check which models the agent tool can use now and compare them with the
  instance files. New models appear often; a list can go stale.
- **Balance per role.** Weigh price, speed, and strength for each role
  separately. The architect needs a strong model, because plans are product
  and design reasoning and a weak architect tends to invent rules (a cheaper
  model may do purely mechanical task splits). The coder gets the cheapest
  model that does the work reliably, since it produces most tokens. Critics
  follow `same_as_reviewed`; auditors follow section 3.
- **Propose, then start.** Before launch, show the operator the proposed setup
  (role, model, one-line reason) and let them accept or change it. This
  applies on every run, not only in the fallback case. Record the accepted
  setup in the run record; update the instance files only when the operator
  asks to keep the change.

## 4. Top-level modes

### unsupervised

Coordinator launches workers or branch stages directly.

Use for breadth, speed, independent perspectives, and most A/B/C comparison runs.

### supervised

Coordinator acts as supervisor mode or launches supervisors/evaluators. Each supervisor launches or evaluates worker attempts.

Use when correctness/evidence matters enough to justify extra cost.

Supervisor retry rules:

- retry only for a diagnosed gap;
- retry only within `max_worker_attempts_per_supervisor`;
- return `partial`, `not_reached`, or `inconclusive` instead of looping;
- never launch another bSwarm.

## 5. Explicit subagent modes

These are stage semantics for bSwarm runs. Name them explicitly in prompts and
run records. The architect follows bArchitect, the coder follows bCoder, and
the critics follow bCritic; this section adds only what is bSwarm-specific.

### Supervisor mode

Purpose: orchestration and statistics only.

Rules:

- creates/validates the run folder;
- creates duplicate branch files when the test permits file edits;
- dispatches branch workers/stages;
- does not directly edit target implementation files unless explicitly asked;
- shields prior generated-code artifacts: do not include previous generated-run paths in worker prompts;
- collects per-branch and per-stage stats;
- writes run artifacts:
  - `run-spec.yaml`;
  - branch output files;
  - `architect-plan.md` files, if applicable;
  - `run-record.md`;
  - `tool-read-stats.md`;
  - `comparison.md`;
  - cross-run stats index updates in `ab-testing/stats-index.md` (section 13).

Supervisor verification must not trust child self-reports until directly checked:

- branch file exists;
- diff stats are available;
- no conflict markers;
- exactly one `classdef` for MATLAB class duplicates;
- original source unchanged;
- runtime/test status recorded if available.

### Architect mode

The architect follows bArchitect (`../bArchitect/architect.md`). Its compact
handoff is the default; run prompts need not restate it unless they override
the budget. In bSwarm:

- `target_file_path` in the plan is the allowed duplicate file;
- for bSelective architect branches, use bSelective first where possible:
  - `list FILE all --compact`;
  - `list FILE functions --format text`;
  - targeted `get FILE function NAME`;
  - avoid whole-file fallback unless necessary and record it if used;
- for ordinary architect branches, use ordinary file/search tools only; no bSelective and no code-knowledge file unless the run explicitly permits it;
- in a cascade, the architect is the parent that does bArchitect's final knowledge check (section 12).

### Coder mode

The coder follows bCoder (`../bCoder/coder.md`). In bSwarm it:

- edits only the branch duplicate file;
- receives the design brief and architect plan;
- must not inspect previous generated-run archives unless explicitly permitted;
- on duplicate branch files, lists the needed knowledge changes instead of editing knowledge;
- returns the role output contract (section 10).

bSwarm adds these checks to bCoder's:

- branch file exists;
- exactly one `classdef` for MATLAB class duplicates;
- expected UI scaffolding strings present;
- original source unchanged.

## 6. A/B/C testing

A/B model:

```text
same goal + same rubric + different variant settings -> compare outcome/evidence/cost
```

Styles:

- `report`: compare and report; default for research/comparison.
- `self_improving`: bounded iterative improvement; requires `max_iterations`.

Common templates:

- mode comparison: `unsupervised` vs `supervised`;
- bSelective comparison: ordinary context vs bSelective-guided context;
- workflow comparison: workflow A vs workflow B;
- prompt/rubric comparison: prompt A vs prompt B;
- staged-context comparison: direct ordinary worker vs bSelective architect/coder vs ordinary architect/coder.

For A/B/C comparison runs, use the keyword normalization unless deliberately
testing an internal override. The normal compact branch names are:

```yaml
branches:
  ordinary:
    pattern: direct_worker
    context_mode: ordinary
    stages: [coder]
  bselective:
    pattern: direct_worker
    context_mode: bselective
    stages: [coder]
  architect:
    pattern: architect_coder
    architect_context_mode: ordinary
    coder_context_mode: ordinary
    stages: [architect, coder]
  bselective_architect:
    pattern: architect_coder
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages: [architect, coder]
  cascade:
    pattern: architect_taskflow
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages: [architect, coder, architect_evaluation]
  bselective_cascade:
    pattern: architect_taskflow
    architect_context_mode: bselective
    coder_context_mode: bselective
    stages: [architect, coder, architect_evaluation]
```

Mixed combinations such as bSelective architect → ordinary coder may be used as
internal experimental overrides, but should not be offered as normal user-facing
keywords.

Cascade safeguards:

```yaml
cascade_defaults:
  max_tasks: 4
  max_coder_attempts_per_task: 1
  max_patch_calls_per_coder: 3
  stop_after_acceptance: true
  re_evaluate_after_each_task: true
```

## 7. critcascade

`critcascade` is the high-assurance bSelective cascade. It uses one task at a time:
the architect works task by task as bArchitect says ("Between tasks").

```text
architect → architect_critic → programmer → programmer_critic
          → architect_revision → programmer_fix
```

Both critics follow bCritic (`../bCritic/critic.md`): what to check, score
and rounds, issue tags, the review file, the summary, and the backlog. The
architect critic reviews the plan; the programmer critic reviews the code.
bSwarm adds:

- Review files go to the run's `critiques/` folder (section 13).
- The parent usually just routes (architect -> parent -> critic -> parent ->
  architect): it forwards the summary and the file path.
- When a task or run ends, the parent adds the backlog entries; a run-spec may
  set `deferred_issues_scope` for one run.
- Maximum delegation depth is 3.

## 8. bSelective

Modes:

- `all_off`: no bSelective.
- `all_on`: bSelective for all relevant subagents.
- `mixed_ab`: bSelective on/off variants; usually `ab_testing: report`.

When active, record adapter, slices, whole-file fallbacks, and missing context.

For bSelective-heavy architect/coder runs, the architect should own most context discovery. The coder should receive the exact target file, exact functions/line regions, required changes, forbidden changes, and concise relevant context. This reduces repeated broad reading and makes bSelective more useful.

## 8. Safety / contamination rules

For generated-code evaluation runs:

- never edit the real/original target source unless explicitly approved;
- duplicate source into branch files under the new run folder;
- do not include previous generated-run paths in worker prompts;
- do not allow workers to inspect `previous-generated-runs/` unless the test explicitly compares against old generated code;
- do not compare to prior generated code until after all workers finish;
- direct workers and coders edit only their allowed duplicate file.

## 9. Recommended run shapes

Choose the smallest role chain that fits the task:

- 1 agent: `coder` — simple direct implementation.
- 2 agents: `architect -> coder` — large files or unclear context.
- 2 agents: `coder -> supervisor` — simple work needing review.
- 3 agents: `architect -> coder -> supervisor` — important or risky work.

## 10. Role output contract

All child outputs should be concise and structured:

```yaml
role_output:
  role: architect | coder | supervisor | worker
  branch_id: <id>
  stage: architect | coder | supervisor | direct_worker
  parent_branch_id: <id or none>
  outcome: reached | not_reached | partial | inconclusive | blocked | unsafe
  confidence: low | medium | high
  summary: <1-3 bullets or short paragraph>
  changed_files: [<paths or none>]
  knowledge_changes: [<path: one-line change> or "no knowledge changes needed"]
  artifacts: [<architect-plan.md/branch-output.md/etc.>]
  evidence: [top 3-5]
  verification: [compact list]
  risks: [top 3]
  missing_context: [top 3]
  recommended_next_step: <one action or none>
  statistics_delta:
    duration_seconds: unknown
    api_calls: unknown
    tool_calls: unknown
    tool_calls_by_type: {}
    bselective_calls: 0
    bselective_used: true | false
    selective_slice_count: 0
    whole_file_reads: unknown
    input_tokens: unknown
    output_tokens: unknown
    reasoning_tokens: unknown
    cache_read_tokens: unknown
    fresh_total_tokens: unknown
    total_with_cache_read_tokens: unknown
    total_tool_output_chars: unknown
    target_related_tool_output_chars: unknown
    diff_added_lines: unknown
    diff_removed_lines: unknown
    matlab_runtime_verification: not_run | passed | failed | partial
```

Supervisor judgement adds:

```yaml
supervisor_judgement:
  worker_branch_id: <id>
  goal_reached: true | false | partial | inconclusive
  acceptance_rationale: <compact>
  identified_gaps: [top gaps]
  retry_requested: true | false
  retry_reason: <compact or none>
  final_branch_recommendation: accept | reject | revise | inconclusive
```

## 11. Statistics

Stats are part of v1. Record what is available cheaply; use `unknown` rather than spending extra tokens to measure.

Collect both per-stage and combined per-branch stats:

- duration seconds;
- API calls;
- tool calls;
- tool calls by type;
- bSelective calls;
- whole-file reads/fallbacks;
- input tokens;
- output tokens;
- reasoning tokens;
- cache-read tokens;
- fresh total tokens = input + output + reasoning;
- total with cache-read tokens;
- total tool-output chars;
- target-related tool-output chars;
- diff added/removed lines;
- whether MATLAB/runtime verification ran.

Architect/coder runs should make it possible to answer:

- did bSelective reduce architect discovery context?
- did the coder avoid repeating discovery?
- did architect/coder split improve quality vs direct ordinary?
- did the split reduce or increase total tokens/tool calls?

## 12. Final report

The final report to the operator follows the core plain-language rule in
`bSmart.md` (`response_style.plain_language`): lead with the answer or
decision, short plain sentences, only the issues that matter, jargon
explained, next steps last. This applies to the report, not to critique
files.

Before reporting, the parent (the architect, in a cascade) does bArchitect's
final knowledge check across the whole change.

Keep the report quick-glance:

- recommendation;
- outcome;
- key evidence;
- unresolved disagreements;
- open `decision` issues by ID, and the count of new backlog entries;
- knowledge changes, or "no knowledge changes needed";
- stage and branch statistics summary;
- budget/limit status;
- one next action.

Save a run record with `templates/run-record.md` when useful or requested.

## 13. Project tracking

A run belongs to the session's active project or workstream
(`bSmart_Protocols/projects.md`). In Free mode, ask which project it belongs
to before writing run files.

- The owner folder is the project folder, or the workstream folder when
  `deferred_issues: workstream` is set in `project.md` (bCritic).
- Run files live in the owner folder: `bswarm-runs/<run>/` (critiques
  included), `jobs/`, `ab-testing/stats-index.md`, and `deferred-issues.md`.
- Knowledge is the project's `knowledge/`; the roles use it as bCoder,
  bArchitect, and bCritic say.
- Operator decisions from the run go to the project's `decisions.md`, or to an
  ADR when the project uses bADR.
- At the end, the parent updates the owner's `handoff.md` with the outcome and
  the one next action.
