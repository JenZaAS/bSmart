# bSmart Extension: Graphify Evaluation Kit

```yaml
name: Graphify
status: bundled_optional_extension
source_root: /workspace/bSmart-System/bSmart-Extensions/Graphify
install_root: /workspace/bSmart-Extensions/Graphify
license: MIT
purpose: Reusable controlled baseline-vs-Graphify evaluation kit for AI containers.
```

## What this is

This extension packages the repeatable test protocol we used for evaluating Graphify as a possible bSmart `bGraph` backend.

It is **not** a claim that Graphify improves the base AI container. The clean docs-corpus test showed Graphify was usable and non-misleading, but not faster or cheaper than baseline search.

## Current conclusion from SschwAdmin docs-corpus test

- Baseline current: 5 sequential isolated workers, 3,154,518 total tokens, 2.63m average worker time.
- Graphify Codex-full current: 5 sequential isolated workers, 3,954,159 total tokens, 2.81m average worker time.
- Graphify extraction/mapping excluded from worker metrics.
- Worker subjective usefulness: 38 helped / 12 partly helped / 0 misleading, but this is **navigation feedback**, not proof of improvement.

Strict interpretation:

> Graphify did not improve the base docs-corpus workflow. It should be retested on code-heavy corpora, especially MATLAB, where graph relationships may matter more.

## Install/copy model

A bSmart setup helper may copy or sync this folder to:

```text
/workspace/bSmart-Extensions/Graphify
```

Other AI containers can then use the prompts/scripts here to run controlled comparisons without inheriting stale conclusions from SschwAdmin.

## Protocol requirements

Use the `controlled-tool-evaluation-protocol` skill.

Core rules:

1. Run baseline and Graphify phases from the same current container state.
2. Use the same execution mode for both phases: sequential vs sequential, or parallel vs parallel.
3. Use 5 isolated workers per phase unless a different sample size is explicitly chosen.
4. Workers must not read previous worker outputs, summaries, comparison files, or metrics files.
5. Baseline workers must not read Graphify artifacts.
6. Graphify workers may read only the explicit precomputed graph artifacts plus source corpus and question list.
7. Do not count extraction/mapping/indexing in worker-only performance.
8. Record setup/mapping costs separately.
9. Treat “helpful” as measurable improvement, not merely “found relevant files.”

## Files

- `prompts/baseline-worker.prompt.md` — strict baseline worker prompt template.
- `prompts/graphify-worker.prompt.md` — strict Graphify worker prompt template.
- `scripts/collect_hermes_worker_metrics.py` — collect worker token/time metrics from Hermes `state.db`.
- `templates/upstream-pr1787-comment.md` — polished upstream feedback draft for Graphify PR #1787.

## GitHub posting policy

There is no local bSmart policy forbidding AI-authored GitHub comments, but comments should be:

- explicitly authorized by Erling,
- transparent that they come from an AI/helper workflow if appropriate,
- posted through a configured machine user or GitHub App,
- limited to technical feedback and evidence,
- never include secrets or private corpus details.

Recommended shared channel: the dedicated GitHub machine user [JenZaAI](https://github.com/JenZaAI), with per-container SSH keys for git and a narrow token/GitHub App permission for API actions such as PR comments.
