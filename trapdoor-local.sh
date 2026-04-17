#!/usr/bin/env bash
set -euo pipefail

# Local-only launcher: safest defaults, no tunnel

ROOT=${TRAPDOOR_ROOT:-/tmp/trapdoor}
PY=${TRAPDOOR_PY:-./venv/bin/python}

if [ ! -x "$PY" ]; then
  echo "Python not found at $PY. Set TRAPDOOR_PY to your interpreter or create venv at ./venv." >&2
  exit 1
fi

echo "Starting Trapdoor locally (limited mode, sandboxed at $ROOT, fresh token)..."

"$PY" server.py \
  --limited \
  --root "$ROOT" \
  --rotate-token \
  --host 127.0.0.1 \
  --port 6969
