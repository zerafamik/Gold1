#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -ne 1 || -z "${1// }" ]]; then
  echo 'usage: ./release_stamp.sh "Exact Legal Name"' >&2
  exit 2
fi
python3 "$ROOT/release_stamp.py" "$1"
