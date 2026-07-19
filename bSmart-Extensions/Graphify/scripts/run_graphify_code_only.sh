#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <CORPUS_ROOT> <EVAL_ROOT>" >&2
  exit 2
fi

CORPUS_ROOT="$1"
EVAL_ROOT="$2"
OUT_ROOT="$EVAL_ROOT/graphify-code-only/out"
LOG="$EVAL_ROOT/graphify-code-only/graphify-code-only.log"

if ! command -v graphify >/dev/null 2>&1; then
  echo "graphify command not found. Install with: uv tool install graphifyy" >&2
  exit 1
fi

mkdir -p "$(dirname "$LOG")" "$OUT_ROOT"
{
  echo "[bSmart Graphify] corpus=$CORPUS_ROOT"
  echo "[bSmart Graphify] out=$OUT_ROOT"
  date -u '+[bSmart Graphify] start_utc=%Y-%m-%dT%H:%M:%SZ'
  graphify extract "$CORPUS_ROOT" --code-only --no-cluster --out "$OUT_ROOT"
  if graphify cluster-only "$OUT_ROOT"; then
    echo "[bSmart Graphify] cluster-only complete"
  else
    echo "[bSmart Graphify] cluster-only failed or unsupported; extraction may still have graph.json"
  fi
  date -u '+[bSmart Graphify] end_utc=%Y-%m-%dT%H:%M:%SZ'
} 2>&1 | tee "$LOG"

echo "[bSmart Graphify] artifacts normally under: $OUT_ROOT/graphify-out"
