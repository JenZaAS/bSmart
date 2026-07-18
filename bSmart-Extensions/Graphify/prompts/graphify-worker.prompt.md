Respond in concise English.

STRICT GRAPHIFY RERUN for comparable metrics from current container state.

Do not use web. Do not use session_search. Do not rely on conversation context.

Do not read any prior worker outputs, summaries, comparison files, metrics files, or evaluation result files under `{{EVAL_ROOT}}` except `README.md` for the question list and the explicitly allowed Graphify artifact files below.

Do not rerun Graphify extraction/mapping/indexing.

Allowed evidence paths only:

- `{{CORPUS_ROOT}}`
- `{{EVAL_ROOT}}/README.md`
- precomputed Graphify artifacts under `{{GRAPHIFY_OUT}}`, normally:
  - `GRAPH_REPORT.md`
  - `graph.json`
  - `manifest.json`
  - `cache/stat-index.json`

Use Graphify artifacts first, then verify final answers in source corpus.

Write only:

- `{{EVAL_ROOT}}/graphify-current-worker-{{WORKER_N}}.md`

Answer the questions from `README.md`.

For each question include:

- Answer
- Files consulted
- Search terms used
- Confidence: high / medium / low
- Cross-file reasoning: yes / no
- Potential gaps
- Graphify usefulness: helped / partly helped / did not help / misleading

Important: Graphify usefulness is worker navigation feedback only. Final test reporting must count improvement only when it improves measurable performance or answer quality.

Record start/end UTC if easy.
