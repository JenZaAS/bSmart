#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <EVAL_ROOT>" >&2
  exit 2
fi

EVAL_ROOT="$1"
export CODEX_HOME="$EVAL_ROOT/codex-cli/home"
mkdir -p "$CODEX_HOME"

if ! command -v codex >/dev/null 2>&1; then
  echo "codex command not found. Install/authenticate Codex CLI before full semantic Graphify tests." >&2
  exit 1
fi

codex exec \
  --ephemeral --sandbox read-only --skip-git-repo-check \
  --ignore-user-config --ignore-rules --json \
  'Return exactly this JSON object and nothing else: {"ok":true}'
