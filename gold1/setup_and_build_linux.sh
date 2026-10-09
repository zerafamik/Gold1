#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; TOP="$(cd "$ROOT/.." && pwd)"; PREFIX="$(cat "$TOP/third_party/primesieve.prefix" 2>/dev/null || true)"
[[ -n "$PREFIX" && -d "$PREFIX" ]] || { echo "ERROR: pinned primesieve prefix missing." >&2; exit 30; }
cd "$ROOT"; SRC_TGZ="primecount-v8.7.tar.gz"; SRC_DIR="primecount-8.7"
if [[ ! -f "$SRC_TGZ" ]]; then curl -L --fail --retry 3 -o "$SRC_TGZ" https://github.com/kimwalisch/primecount/archive/refs/tags/v8.7.tar.gz; fi
rm -rf "$SRC_DIR" build; tar -xzf "$SRC_TGZ"; python3 ./apply_patch.py "$SRC_DIR"
cmake -S "$SRC_DIR" -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="$PREFIX" -DBUILD_LIBPRIMESIEVE=OFF -DBUILD_PRIMECOUNT=ON -DBUILD_STATIC_LIBS=ON -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF -DWITH_OPENMP=ON -DWITH_MULTIARCH=ON
cmake --build build --target gold1-delta-ac-sched gold1-interval gold1-delta-d primecount --parallel "${GOLD1_BUILD_JOBS:-12}"
c++ --version > "$ROOT/build-compiler.txt" 2>&1 || true
[[ -x "$ROOT/build/gold1-interval" && -x "$ROOT/build/primecount" ]] || { echo "ERROR: Gold1 Linux build incomplete." >&2; exit 31; }
