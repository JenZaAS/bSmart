#!/usr/bin/env bash
set -euo pipefail
TARGET_HOME="${1:-/opt/data}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$EXT_ROOT/plugins/session-shortcuts"
DEST="$TARGET_HOME/plugins/session-shortcuts"
if [ ! -f "$SRC/plugin.yaml" ] || [ ! -f "$SRC/__init__.py" ]; then
  echo "ERROR: plugin source not found: $SRC" >&2
  exit 1
fi
mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
cp -a "$SRC" "$DEST"
echo "Installed session-shortcuts plugin to $DEST"
