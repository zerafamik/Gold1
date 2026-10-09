#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
case "$(uname -s)" in
  Linux*) exec "$ROOT/platform/build_fastprime_linux.sh" ;;
  MINGW*|MSYS*|CYGWIN*) exec "$ROOT/platform/build_fastprime_windows.sh" ;;
  *) echo "ERROR: unsupported OS." >&2; exit 2 ;;
esac
