#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$($ROOT/platform/fetch_primesieve.sh | tail -n1)"

if [[ -n "${USERPROFILE:-}" ]] && command -v cygpath >/dev/null 2>&1; then
  SHORT_BASE="$(cygpath -u "$USERPROFILE")/.gold1-v232"
else
  SHORT_BASE="/c/.gold1-v232"
fi
BUILD="${GOLD1_MSVC_PRIMESIEVE_BUILD_DIR:-$SHORT_BASE/primesieve-msvc-build}"
OUT="$ROOT/third_party/primesieve-msvc-bin"
rm -rf "$BUILD" "$OUT"
mkdir -p "$BUILD" "$OUT"

WIN_CMAKE="${WINDOWS_CMAKE:-}"
if [[ -z "$WIN_CMAKE" ]]; then
  for c in "/c/Program Files/CMake/bin/cmake.exe" "/c/Program Files (x86)/CMake/bin/cmake.exe"; do
    [[ -x "$c" ]] && { WIN_CMAKE="$c"; break; }
  done
fi
if [[ -z "$WIN_CMAKE" ]]; then
  CAND="$(command -v cmake.exe 2>/dev/null || true)"
  [[ -n "$CAND" ]] && WIN_CMAKE="$CAND"
fi
if [[ -z "$WIN_CMAKE" || ! -x "$WIN_CMAKE" ]]; then
  cat >&2 <<'MSG'
ERROR: Windows-native Kitware CMake is required for the MSVC fast-prime bridge.
Install it from PowerShell, then reopen MSYS2 UCRT64:
  winget install -e --id Kitware.CMake
MSG
  exit 23
fi

DETECTED="$($ROOT/platform/detect_visual_studio.sh 2>/dev/null || true)"
if [[ -z "$DETECTED" ]]; then
  cat >&2 <<'MSG'
ERROR: No installed Visual Studio C++ toolchain was found.

Gold1 itself has already built successfully; this prerequisite is only for the
Windows fast-prime comparator, which uses Rust's x86_64-pc-windows-msvc target.

Open POWERSHELL (not MSYS2) and install the C++ Build Tools once:

  winget install -e --id Microsoft.VisualStudio.2022.BuildTools --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"

When the installer finishes, reopen MSYS2 UCRT64 and rerun:
  ./setup_all.sh

Completed Gold1/UCRT64 stages will be reused automatically.
MSG
  exit 24
fi
IFS=$'\t' read -r VS_PATH VS_VERSION GEN <<< "$DETECTED"

# Guard against a CMake installation that advertises a generator but cannot use
# it. The generator comes from the installed VS major version, never from
# parsing `cmake --help`.
if ! "$WIN_CMAKE" --help 2>/dev/null | grep -Fq "$GEN"; then
  echo "ERROR: installed Visual Studio requires CMake generator '$GEN', but '$WIN_CMAKE' does not provide it." >&2
  echo "Update Kitware CMake, then rerun ./setup_all.sh." >&2
  exit 25
fi

echo "Windows CMake: $WIN_CMAKE"
echo "Visual Studio installation: $VS_PATH"
echo "Visual Studio version: $VS_VERSION"
echo "Generator: $GEN"
echo "Short MSVC build dir: $BUILD"

"$WIN_CMAKE" -S "$(cygpath -m "$SRC")" -B "$(cygpath -m "$BUILD")" -G "$GEN" -A x64 \
  -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF
"$WIN_CMAKE" --build "$(cygpath -m "$BUILD")" --config Release --parallel

LIB=""
for c in \
  "$BUILD/Release/primesieve_static.lib" \
  "$BUILD/Release/primesieve.lib" \
  "$BUILD/lib/Release/primesieve_static.lib" \
  "$BUILD/lib/Release/primesieve.lib"; do
  [[ -f "$c" ]] && { LIB="$c"; break; }
done
if [[ -z "$LIB" ]]; then
  LIB="$(find "$BUILD" -type f \( -iname 'primesieve_static.lib' -o -iname 'primesieve.lib' \) | head -n1 || true)"
fi
[[ -n "$LIB" && -f "$LIB" ]] || { echo "ERROR: MSVC primesieve library not found." >&2; exit 26; }

FINAL_LIB="$OUT/primesieve.lib"
cp -f "$LIB" "$FINAL_LIB"
printf '%s\n' "$FINAL_LIB" > "$ROOT/third_party/primesieve-msvc.lib"
printf '%s\n' "$VS_PATH" > "$ROOT/third_party/visual-studio.installation-path"
printf '%s\n' "$VS_VERSION" > "$ROOT/third_party/visual-studio.installation-version"
printf '%s\n' "$GEN" > "$ROOT/third_party/visual-studio.cmake-generator"
echo "MSVC primesieve library: $FINAL_LIB"
