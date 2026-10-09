#!/usr/bin/env bash
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -ne 2 ]]; then
  echo "Usage: RANK_RUNS=5 ./run_interval_bench.sh L H" >&2
  exit 2
fi
RUNS="${RANK_RUNS:-5}"
PYTHON="$(command -v python3 || command -v python || true)"
[[ -n "$PYTHON" ]] || { echo "ERROR: Python 3.10+ not found." >&2; exit 3; }
"$PYTHON" "$ROOT/tools/interval_bench.py" benchmark "$1" "$2" --runs "$RUNS"
