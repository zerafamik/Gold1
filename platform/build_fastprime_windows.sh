#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; TD="$ROOT/third_party"; mkdir -p "$TD"
if [[ -n "${USERPROFILE:-}" ]] && command -v cygpath >/dev/null 2>&1; then CARGO_BIN="$(cygpath -u "$USERPROFILE")/.cargo/bin"; [[ -d "$CARGO_BIN" ]] && export PATH="$CARGO_BIN:$PATH"; fi
if ! command -v rustup >/dev/null 2>&1; then echo "ERROR: install Rust via rustup/winget, reopen UCRT64, rerun." >&2; exit 40; fi
FP="$TD/fast-prime"; COMMIT="${FASTPRIME_COMMIT:-ad2642f917526e2de0e45833b1a242c10963568f}"
if [[ ! -d "$FP/.git" ]]; then git clone https://github.com/secwest/fast-prime.git "$FP"; fi
git -C "$FP" fetch --all --tags --prune; git -C "$FP" checkout --detach "$COMMIT"
printf '%s\n' "$(git -C "$FP" rev-parse HEAD)" > "$TD/fast-prime.commit"
LIB="$(cat "$TD/primesieve-msvc.lib" 2>/dev/null || true)"; [[ -f "$LIB" ]] || { echo "ERROR: MSVC primesieve library missing." >&2; exit 41; }
BRIDGE="$TD/primesieve-msvc-link"; mkdir -p "$BRIDGE"; cp -f "$LIB" "$BRIDGE/primesieve.lib"; LIBDIR_WIN="$(cygpath -m "$BRIDGE")"
python "$ROOT/platform/patch_fastprime.py" "$FP" "$LIBDIR_WIN"
TOOLCHAIN="${GOLD1_RUST_TOOLCHAIN:-nightly-x86_64-pc-windows-msvc}"; TARGET="x86_64-pc-windows-msvc"
rustup toolchain install "$TOOLCHAIN" --profile minimal; rustup component add rust-src --toolchain "$TOOLCHAIN"
printf '%s\n' "$TOOLCHAIN" > "$TD/fast-prime.rust-toolchain"; printf '%s\n' "$TARGET" > "$TD/fast-prime.rust-host"
rustc +"$TOOLCHAIN" -vV > "$TD/fast-prime.rustc-version.txt"; cargo +"$TOOLCHAIN" -V > "$TD/fast-prime.cargo-version.txt"
if [[ -n "${USERPROFILE:-}" ]]; then SHORT_TARGET="$(cygpath -u "$USERPROFILE")/.gold1-fastprime-target-v230"; else SHORT_TARGET="/c/gold1-fastprime-target-v230"; fi
mkdir -p "$SHORT_TARGET"; SHORT_TARGET_WIN="$(cygpath -m "$SHORT_TARGET")"
(cd "$FP"; CARGO_TARGET_DIR="$SHORT_TARGET_WIN" cargo +"$TOOLCHAIN" build --release --bin prime_count_v8 -Zbuild-std=std,panic_abort --target "$TARGET")
BUILT="$SHORT_TARGET/$TARGET/release/prime_count_v8.exe"; [[ -f "$BUILT" ]] || { echo "ERROR: fast-prime Windows binary missing." >&2; exit 42; }
BIN_DIR="$TD/fast-prime-bin"; mkdir -p "$BIN_DIR"; EXE="$BIN_DIR/prime_count_v8.exe"; cp -f "$BUILT" "$EXE"; printf '%s\n' "$EXE" > "$TD/fast-prime.binary"
SMOKE="$(GOLD1_THREADS=1 POOL_MULT=1 "$EXE" 1000 2>&1)"; [[ "$SMOKE" == *"168"* ]] || { echo "ERROR: fast-prime smoke test failed: $SMOKE" >&2; exit 43; }
echo "PASS: fast-prime Windows smoke test pi(1000)=168"
