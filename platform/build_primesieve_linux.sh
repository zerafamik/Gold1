#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SRC="$($ROOT/platform/fetch_primesieve.sh | tail -n1)"
PREFIX="$ROOT/third_party/primesieve-linux-prefix"; BUILD="$ROOT/third_party/primesieve-linux-build"
rm -rf "$BUILD" "$PREFIX"
cmake -S "$SRC" -B "$BUILD" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$PREFIX" -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF
cmake --build "$BUILD" --parallel; cmake --install "$BUILD"
PS="$PREFIX/bin/primesieve"; [[ -x "$PS" ]] || { echo "ERROR: primesieve CLI missing." >&2; exit 21; }
"$PS" --version
printf '%s\n' "$PS" > "$ROOT/third_party/primesieve.binary"; printf '%s\n' "$PREFIX" > "$ROOT/third_party/primesieve.prefix"
