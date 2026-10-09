#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
case "$(uname -s 2>/dev/null || echo unknown)" in
  Linux*) exec "$ROOT/setup_linux.sh" "$@" ;;
  MINGW*|MSYS*|CYGWIN*) exec "$ROOT/setup_windows_ucrt64.sh" "$@" ;;
  *) echo "ERROR: supported hosts are Linux and Windows via MSYS2 UCRT64." >&2; exit 2 ;;
esac
