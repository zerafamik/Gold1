#!/usr/bin/env bash
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 2 ]]; then
  echo "Usage: ./validate_interval.sh L H" >&2
  exit 2
fi
PYTHON="$(command -v python3 || command -v python || true)"
[[ -n "$PYTHON" ]] || { echo "ERROR: Python 3.10+ not found." >&2; exit 3; }
"$PYTHON" "$ROOT/tools/interval_bench.py" validate "$1" "$2"
