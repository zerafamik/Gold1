#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$($ROOT/platform/fetch_primesieve.sh | tail -n1)"
PREFIX="$ROOT/third_party/primesieve-ucrt64-prefix"

# Use a short object directory on Windows.  Installation remains package-local
# so provenance/executable discovery is self-contained.
if [[ -n "${USERPROFILE:-}" ]] && command -v cygpath >/dev/null 2>&1; then
  SHORT_BASE="$(cygpath -u "$USERPROFILE")/.gold1-v231"
else
  SHORT_BASE="/c/.gold1-v231"
fi
BUILD="${GOLD1_UCRT64_PRIMESIEVE_BUILD_DIR:-$SHORT_BASE/primesieve-ucrt64-build}"
rm -rf "$BUILD" "$PREFIX"
mkdir -p "$BUILD"
cmake -S "$SRC" -B "$BUILD" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="$PREFIX" \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF
cmake --build "$BUILD" --parallel
cmake --install "$BUILD"
PS="$PREFIX/bin/primesieve.exe"
[[ -f "$PS" ]] || { echo "ERROR: primesieve.exe missing." >&2; exit 22; }
"$PS" --version
printf '%s\n' "$PS" > "$ROOT/third_party/primesieve.binary"
printf '%s\n' "$PREFIX" > "$ROOT/third_party/primesieve.prefix"
