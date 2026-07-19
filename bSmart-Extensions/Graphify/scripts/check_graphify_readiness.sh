#!/usr/bin/env bash
set -euo pipefail

printf 'Graphify evaluation readiness check\n'
printf '===================================\n'

if command -v uv >/dev/null 2>&1; then
  printf 'uv: OK (%s)\n' "$(uv --version 2>/dev/null | head -n1)"
else
  printf 'uv: MISSING\n'
fi

if command -v graphify >/dev/null 2>&1; then
  printf 'graphify: OK (%s)\n' "$(command -v graphify)"
  graphify --help >/tmp/graphify-help.$$ 2>&1 || true
  if grep -qi 'code-only' /tmp/graphify-help.$$; then
    printf 'graphify --code-only: visible in help\n'
  else
    printf 'graphify --code-only: not visible in top-level help; check extract help\n'
  fi
  graphify extract --help >/tmp/graphify-extract-help.$$ 2>&1 || true
  if grep -Eqi 'codex|backend|llm' /tmp/graphify-extract-help.$$; then
    printf 'semantic backend options: possible; inspect graphify extract --help\n'
  else
    printf 'semantic backend options: not obvious in extract help\n'
  fi
  rm -f /tmp/graphify-help.$$ /tmp/graphify-extract-help.$$
else
  printf 'graphify: MISSING\n'
fi

if command -v codex >/dev/null 2>&1; then
  printf 'codex: OK (%s)\n' "$(command -v codex)"
else
  printf 'codex: MISSING (only needed for codex-cli semantic extraction)\n'
fi

printf '\nConclusion hints:\n'
printf '%s\n' '- If graphify is MISSING: install graphifyy or provide a Graphify PR/local build.'
printf '%s\n' '- If graphify exists: code-only Graphify test may be possible.'
printf '%s\n' '- If codex/backend support is missing: full semantic Codex Graphify test is not ready.'
