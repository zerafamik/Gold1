#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
"$ROOT/platform/install_linux_prereqs.sh"
FORCE="${GOLD1_FORCE_REBUILD:-0}"
WITH_FP="${GOLD1_WITH_FASTPRIME:-0}"
have_linux_primesieve(){ local q="$ROOT/third_party/primesieve-linux-prefix/bin/primesieve"; [[ -x "$q" ]] && "$q" --version 2>/dev/null | grep -q '12\.15'; }
have_gold1(){ [[ -x "$ROOT/gold1/build/gold1-interval" && -x "$ROOT/gold1/build/primecount" ]]; }
have_fastprime(){ local f="$(cat "$ROOT/third_party/fast-prime.binary" 2>/dev/null || true)"; [[ -n "$f" && -x "$f" ]] && GOLD1_THREADS=1 POOL_MULT=1 "$f" 1000 2>/dev/null | grep -q '168'; }
if [[ "$FORCE" == "1" ]] || ! have_linux_primesieve; then echo "===== LINUX 1/2: pinned primesieve ====="; "$ROOT/platform/build_primesieve_linux.sh"; else echo "SKIP: pinned Linux primesieve already present."; fi
if [[ "$FORCE" == "1" ]] || ! have_gold1; then echo "===== LINUX 2/2: Gold1 + primecount ====="; "$ROOT/gold1/setup_and_build_linux.sh"; else echo "SKIP: Gold1/primecount binaries already present."; fi
if [[ "$WITH_FP" == "1" ]]; then echo "===== OPTIONAL: fast-prime comparator ====="; [[ "$FORCE" == "1" ]] || have_fastprime || "$ROOT/platform/build_fastprime_linux.sh"; else echo "OPTIONAL SKIP: fast-prime comparator/Rust download."; echo "To add it later: GOLD1_WITH_FASTPRIME=1 ./setup_all.sh"; fi
echo "Setup complete. Next: ./validate_all.sh"
