#!/usr/bin/env bash
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(command -v python3 || command -v python || true)"
[[ -n "$PYTHON" ]] || { echo "ERROR: Python 3.10+ not found." >&2; exit 3; }
"$PYTHON" "$ROOT/tools/matrix.py"
