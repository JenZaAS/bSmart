# Blank bImprove case

Copy this folder into your own project (not into bSmart-System), rename it,
and fill in the placeholders. See "Add a new case" in `../../improve.md`.

- `kit.json`: name, version (raise it when the prompt, instance, or key
  changes), the target MDs, the prompt and the answer key. Use `phases`
  instead of `prompt`/`answer_key` for a multi-step case.
- `instance/`: the made-up starting files, with decoys. No real project,
  client, or private names.
- `answer-key.json`: script rows where possible (see the check table in
  `improve.md`), `judged` rows for quality.
