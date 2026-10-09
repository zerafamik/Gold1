#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; TD="$ROOT/third_party"; mkdir -p "$TD"
if [[ ! -x "$HOME/.cargo/bin/rustup" ]] && ! command -v rustup >/dev/null 2>&1; then
  echo "Installing rustup for current user..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
fi
export PATH="$HOME/.cargo/bin:$PATH"
command -v rustup >/dev/null || { echo "ERROR: rustup unavailable." >&2; exit 40; }
FP="$TD/fast-prime"; COMMIT="${FASTPRIME_COMMIT:-ad2642f917526e2de0e45833b1a242c10963568f}"
if [[ ! -d "$FP/.git" ]]; then git clone https://github.com/secwest/fast-prime.git "$FP"; fi
git -C "$FP" fetch --all --tags --prune; git -C "$FP" checkout --detach "$COMMIT"
printf '%s\n' "$(git -C "$FP" rev-parse HEAD)" > "$TD/fast-prime.commit"
PREFIX="$(cat "$TD/primesieve.prefix")"; LIBDIR=""
for d in "$PREFIX/lib" "$PREFIX/lib64"; do [[ -f "$d/libprimesieve.a" || -f "$d/libprimesieve.so" ]] && { LIBDIR="$d"; break; }; done
[[ -n "$LIBDIR" ]] || { echo "ERROR: libprimesieve not found in Linux prefix." >&2; exit 42; }
python3 "$ROOT/platform/patch_fastprime.py" "$FP" "$LIBDIR"
TOOLCHAIN="${GOLD1_RUST_TOOLCHAIN:-nightly}"
rustup toolchain install "$TOOLCHAIN" --profile minimal; rustup component add rust-src --toolchain "$TOOLCHAIN"
TARGET="$(rustc +"$TOOLCHAIN" -vV | awk '/^host:/{print $2}')"; [[ -n "$TARGET" ]] || { echo "ERROR: Rust target unknown." >&2; exit 43; }
printf '%s\n' "$TOOLCHAIN" > "$TD/fast-prime.rust-toolchain"; printf '%s\n' "$TARGET" > "$TD/fast-prime.rust-host"
rustc +"$TOOLCHAIN" -vV > "$TD/fast-prime.rustc-version.txt"; cargo +"$TOOLCHAIN" -V > "$TD/fast-prime.cargo-version.txt"
SHORT_TARGET="${GOLD1_CARGO_TARGET_DIR:-$HOME/.cache/gold1-fastprime-target}"; mkdir -p "$SHORT_TARGET"
(cd "$FP"; CARGO_TARGET_DIR="$SHORT_TARGET" cargo +"$TOOLCHAIN" build --release --bin prime_count_v8 -Zbuild-std=std,panic_abort --target "$TARGET")
BUILT="$SHORT_TARGET/$TARGET/release/prime_count_v8"; [[ -x "$BUILT" ]] || { echo "ERROR: fast-prime Linux binary missing." >&2; exit 44; }
BIN_DIR="$TD/fast-prime-bin"; mkdir -p "$BIN_DIR"; EXE="$BIN_DIR/prime_count_v8"; cp -f "$BUILT" "$EXE"; chmod +x "$EXE"
printf '%s\n' "$EXE" > "$TD/fast-prime.binary"
SMOKE="$(GOLD1_THREADS=1 POOL_MULT=1 "$EXE" 1000 2>&1)"; [[ "$SMOKE" == *"168"* ]] || { echo "ERROR: fast-prime smoke test failed: $SMOKE" >&2; exit 45; }
echo "PASS: fast-prime Linux smoke test pi(1000)=168"
