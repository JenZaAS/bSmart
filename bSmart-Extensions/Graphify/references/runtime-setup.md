# Graphify runtime setup for other AI containers

This evaluation kit contains prompts/scripts for a controlled baseline-vs-Graphify comparison. It does **not** vendor Graphify itself.

## Minimum real Graphify requirement

An AI container can run a real Graphify phase only if one of these is available:

1. `graphify` CLI from the `graphifyy` Python package, suitable for local/code-only extraction; or
2. a Graphify build/branch that supports the `codex-cli` backend for full semantic extraction; or
3. another configured Graphify LLM backend via approved API keys.

If none of those exists, the container can only run baseline/protocol dry runs.

## Safe first install: code-only Graphify

Use this for a low-risk first test on a code-heavy repository:

```bash
uv tool install graphifyy
```

Then verify:

```bash
graphify --help
```

Code-only extraction avoids LLM/API backend requirements:

```bash
graphify extract <CORPUS_ROOT> --code-only --no-cluster --out <EVAL_ROOT>/graphify-code-only/out
```

Then generate a report when supported by the installed version:

```bash
graphify cluster-only <EVAL_ROOT>/graphify-code-only/out
```

Expected artifacts are normally under:

```text
<EVAL_ROOT>/graphify-code-only/out/graphify-out/
  graph.json
  GRAPH_REPORT.md
  manifest.json
  cache/stat-index.json
```

## Full semantic extraction with Codex CLI

The SschwAdmin test that processed Markdown/docs used a local Graphify PR build with a `codex-cli` backend and a sanitized child-process environment.

Important: do **not** assume the released `graphifyy` package supports this exact path. Verify first:

```bash
graphify extract --help | grep -E 'codex|backend|llm' || true
```

Required concepts from the successful test:

- scoped Codex CLI install, not global/shared if avoidable;
- dedicated `CODEX_HOME` for the experiment;
- Codex login in that dedicated home;
- sanitized child process environment so unrelated secrets are not inherited;
- tiny Codex smoke test before Graphify;
- tiny Graphify smoke test before full repo extraction;
- serial/low-concurrency extraction first.

Codex smoke test shape:

```bash
CODEX_HOME="<EVAL_ROOT>/codex-cli/home" codex exec \
  --ephemeral --sandbox read-only --skip-git-repo-check \
  --ignore-user-config --ignore-rules --json \
  'Return exactly this JSON object and nothing else: {"ok":true}'
```

Only run full semantic extraction if the installed Graphify supports the chosen backend and the smoke tests pass.

## Evaluation discipline

Record Graphify setup/extraction time and tokens separately from worker-answering metrics. Workers must not rerun extraction; they may use only the precomputed graph artifacts plus the source corpus and question list.
