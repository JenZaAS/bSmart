# bQAbuild

`bQAbuild` is a standard bSmart question-and-answer scoping feature.

It turns an unclear feature, change, or refactor into a recorded set of decisions and a concise implementation brief. It is the bSmart adaptation of the reviewed `ask-then-build` idea from `davidondrej/skills`. The upstream skill remains a reference; bQAbuild is the bSmart-native implementation.

## Boundary

`bQAbuild` helps an agent:

1. identify the important open decisions;
2. ask one question at a time;
3. record the answers and superseded decisions;
4. produce a build brief after the scope is sufficiently clear.

It does **not**:

- edit project source code;
- commit, push, deploy, or publish;
- store secrets;
- force every task through a fixed number of questions;
- replace project-specific requirements, ADRs, or approval rules.

## Storage

Packaged source:

```text
/workspace/bSmart-System/bSmart-Extensions/bQAbuild
```

Instance-local session state:

```text
/workspace/bSmart/QABuild
```

The instance-local folder contains JSON session records and generated Markdown briefs. It must not be committed to the public bSmart-System repository.

## Commands

```text
python3 bqabuild_handler.py start "Add export support" --session-id export-support
python3 bqabuild_handler.py set-questions export-support questions.json
python3 bqabuild_handler.py status export-support
python3 bqabuild_handler.py answer export-support "Use a project-local command"
python3 bqabuild_handler.py revise export-support storage "Use instance-local state"
python3 bqabuild_handler.py build export-support \
  --read-first project.md \
  --step "Add the command handler" \
  --validate "Run the unit tests" \
  --rule "Do not commit or deploy"
```

Use `--root PATH` for tests or a different instance-local state root.

## Question file

`set-questions` accepts a JSON list. Each question has:

```json
{
  "id": "storage",
  "title": "Where should the feature store its state?",
  "context": "State must survive a session restart.",
  "options": [
    "Project-local files",
    "Instance-local extension state"
  ],
  "recommendation": "Instance-local extension state"
}
```

Each question must have 2–4 options and a recommendation. Questions are presented in order, one at a time. Each returned question includes its position, total question count, and remaining count so the operator can see the progress, for example: `Question 2 of 5 — 4 remaining`.

## Status

Initial v1 runtime implemented and tested. bQAbuild is part of the normal bSmart feature set; the chat/UI adapter remains responsible for presenting the returned question and collecting the operator's answer.
