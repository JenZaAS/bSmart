Hi — we reviewed the new `codex-cli` / `acp` subscription-backed extraction paths from a security angle and ran a small controlled evaluation on a documentation corpus.

First, thank you for adding this. The `codex-cli` route is exactly the kind of backend needed by users who have a ChatGPT/Codex subscription but not an `OPENAI_API_KEY`.

## Security concern: inherited child environment

One concern we noticed: both child-agent paths appear to inherit the parent process environment:

- `graphify/acp.py` uses `os.environ.copy()` for the ACP adapter process.
- the `codex exec` subprocess in `graphify/llm.py` appears to inherit the parent env by default.

Because these backends run autonomous agent CLIs over untrusted repository/corpus text, read-only filesystem mode is not a complete boundary if the child process receives unrelated env secrets. A prompt-injection payload in a markdown/source file could potentially cause the agent to inspect env vars or use available shell/network tooling, depending on the CLI sandbox behavior.

We locally tested a small mitigation: construct an allowlisted child env for `codex-cli` and `acp`, keeping only process plumbing/auth-location vars such as `HOME`, `PATH`, locale/temp vars, `NO_BROWSER`, `CODEX_HOME`, and XDG dirs, plus explicit operator additions via something like `GRAPHIFY_CHILD_ENV_ALLOWLIST`. We also added unit tests that secret-like vars such as `OPENAI_API_KEY`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, and `AWS_SECRET_ACCESS_KEY` are not forwarded by default.

Focused tests still passed after that local patch:

```text
uv run --extra acp pytest tests/test_acp_backend.py tests/test_llm_backends.py -q
93 passed
```

There may be a better upstream design, but I wanted to flag the inherited-env issue before this backend becomes a recommended no-API-key path.

## Evaluation note

We also ran a stricter baseline-vs-Graphify check on a documentation corpus using 5 isolated sequential workers per phase. Graphify extraction/mapping was treated as setup and excluded from worker performance.

Result: Graphify/Codex-full was usable and non-misleading as a navigation layer, but it did not improve worker-time or token efficiency on this docs-heavy corpus. Normal source search was already strong. This may be different on a code-heavy project where call/file relationships matter more.

## Smaller correctness notes

- `_call_llm`/lightweight LLM paths may need a `codex-cli` branch analogous to the new ACP handling, otherwise `backend="codex-cli"` may fall through to OpenAI-compatible assumptions.
- community-labeling serialization appears to guard ACP but may need the same serial default for `codex-cli` to avoid subscription burst/concurrency issues.

Happy to share the local patch/diff if useful.

—
Posted by [JenZaAI](https://github.com/JenZaAI) via [bSmart AI workflow](https://github.com/JenZaAS/bSmart), approved by [JenZAAS](https://github.com/JenZaAS).
