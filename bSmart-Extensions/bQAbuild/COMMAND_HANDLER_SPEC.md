# bQAbuild command handler specification

```yaml
name: bQAbuild command handler
status: v1_implemented
scope: question-driven scoping, decision capture, and implementation-brief generation
packaged_root: /workspace/bSmart-System/bSmart-Extensions/bQAbuild
instance_root: /workspace/bSmart/QABuild
```

## Principles

- Question design belongs to the agent using the extension; the runtime stores and presents the explicit question contract.
- Ask one question at a time.
- Show progress with each question: current position, total questions, and remaining questions.
- Record every answer immediately.
- Preserve the original answer text.
- Never silently replace a prior answer. A later answer is recorded as a superseding decision.
- Do not generate a build brief until every configured question has an answer.
- The runtime is file-backed and uses only the Python standard library.
- Generated briefs are plans/prompts, not authorization to edit, commit, deploy, or publish.

## CLI

```text
bqabuild_handler.py [--root PATH] start TITLE [--session-id ID]
bqabuild_handler.py [--root PATH] set-questions SESSION QUESTIONS_JSON
bqabuild_handler.py [--root PATH] next SESSION
bqabuild_handler.py [--root PATH] answer SESSION ANSWER
bqabuild_handler.py [--root PATH] revise SESSION QUESTION_ID ANSWER
bqabuild_handler.py [--root PATH] status SESSION
bqabuild_handler.py [--root PATH] build SESSION [--read-first FILE]... [--step TEXT]... [--validate TEXT]... [--rule TEXT]...
```

## State

Each session is stored at `<root>/sessions/<session-id>.json` with:

- title and creation time;
- ordered question definitions;
- answer records with timestamps;
- current question index;
- status: `draft`, `questioning`, `ready`, or `built`;
- generated brief path when available.

The default root is `/workspace/bSmart/QABuild`.

## Build brief

The generated `<root>/briefs/<session-id>.md` contains:

1. read-first files;
2. the requested change;
3. recorded decisions;
4. implementation steps;
5. validation steps;
6. explicit rules and boundaries.

The brief must say that the implementing agent should not commit or publish unless separately instructed.
