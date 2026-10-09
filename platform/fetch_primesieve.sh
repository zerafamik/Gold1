#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${PRIMESIEVE_VERSION:-12.15}"
TD="$ROOT/third_party"; TGZ="$TD/primesieve-v${VER}.tar.gz"; SRC="$TD/primesieve-${VER}"
mkdir -p "$TD"
if [[ ! -f "$TGZ" ]]; then curl -L --fail --retry 3 -o "$TGZ" "https://github.com/kimwalisch/primesieve/archive/refs/tags/v${VER}.tar.gz"; fi
rm -rf "$SRC"; tar -xzf "$TGZ" -C "$TD"
[[ -f "$SRC/CMakeLists.txt" ]] || { echo "ERROR: primesieve extraction failed." >&2; exit 20; }
printf '%s\n' "$VER" > "$TD/primesieve.version"
echo "$SRC"
