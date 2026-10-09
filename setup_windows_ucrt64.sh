#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ "${MSYSTEM:-}" != "UCRT64" ]]; then
  echo "ERROR: run from the MSYS2 UCRT64 shell (MSYSTEM=UCRT64)." >&2
  exit 2
fi
pacman -S --needed --noconfirm git curl tar python mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake mingw-w64-ucrt-x86_64-ninja >/dev/null
FORCE="${GOLD1_FORCE_REBUILD:-0}"
WITH_FP="${GOLD1_WITH_FASTPRIME:-0}"

have_ucrt_primesieve() {
  local q="$ROOT/third_party/primesieve-ucrt64-prefix/bin/primesieve.exe"
  [[ -x "$q" ]] && "$q" --version 2>/dev/null | grep -q '12\.15'
}
have_gold1() { [[ -x "$ROOT/gold1/build/gold1-interval.exe" && -x "$ROOT/gold1/build/primecount.exe" ]]; }
have_msvc_bridge() { local f="$(cat "$ROOT/third_party/primesieve-msvc.lib" 2>/dev/null || true)"; [[ -n "$f" && -f "$f" ]]; }
have_fastprime() { local f="$(cat "$ROOT/third_party/fast-prime.binary" 2>/dev/null || true)"; [[ -n "$f" && -x "$f" ]] && GOLD1_THREADS=1 POOL_MULT=1 "$f" 1000 2>/dev/null | grep -q '168'; }

if [[ "$FORCE" == "1" ]] || ! have_ucrt_primesieve; then
  echo "===== WINDOWS 1/2: pinned UCRT64 primesieve ====="
  "$ROOT/platform/build_primesieve_ucrt64.sh"
else echo "SKIP: pinned UCRT64 primesieve already present."; fi

if [[ "$FORCE" == "1" ]] || ! have_gold1; then
  echo "===== WINDOWS 2/2: Gold1 + primecount ====="
  "$ROOT/gold1/setup_and_build_ucrt64.sh"
else echo "SKIP: Gold1/primecount binaries already present."; fi

if [[ "$WITH_FP" == "1" ]]; then
  echo "===== OPTIONAL: fast-prime comparator ====="
  if [[ "$FORCE" == "1" ]] || ! have_msvc_bridge; then "$ROOT/platform/build_primesieve_msvc.sh"; fi
  if [[ "$FORCE" == "1" ]] || ! have_fastprime; then "$ROOT/platform/build_fastprime_windows.sh"; fi
else
  echo "OPTIONAL SKIP: fast-prime comparator (no Visual Studio required)."
  echo "To add it later: GOLD1_WITH_FASTPRIME=1 ./setup_all.sh"
fi

echo "Setup complete. Next: ./validate_all.sh"
