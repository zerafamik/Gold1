#!/usr/bin/env bash
set -euo pipefail

# Prints three tab-separated fields on success:
#   installation_path<TAB>installation_version<TAB>cmake_generator
# Exits non-zero when no Visual Studio instance with the x64/x86 C++ tools is installed.

vswhere_candidates=(
  "${GOLD1_VSWHERE:-}"
  "/c/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"
  "/c/Program Files/Microsoft Visual Studio/Installer/vswhere.exe"
)
VSWHERE=""
for p in "${vswhere_candidates[@]}"; do
  [[ -n "$p" ]] || continue
  if [[ -x "$p" ]]; then VSWHERE="$p"; break; fi
done

if [[ -n "$VSWHERE" ]]; then
  INSTALL_PATH="$($VSWHERE -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath 2>/dev/null | tr -d '\r' | tail -n1)"
  INSTALL_VER="$($VSWHERE -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationVersion 2>/dev/null | tr -d '\r' | tail -n1)"
  if [[ -n "$INSTALL_PATH" && -n "$INSTALL_VER" ]]; then
    MAJOR="${INSTALL_VER%%.*}"
    case "$MAJOR" in
      17) GEN="Visual Studio 17 2022" ;;
      18) GEN="Visual Studio 18 2026" ;;
      *)
        echo "ERROR: Visual Studio C++ tools were found at '$INSTALL_PATH' but version '$INSTALL_VER' is not mapped to a CMake generator." >&2
        exit 4
        ;;
    esac
    printf '%s\t%s\t%s\n' "$INSTALL_PATH" "$INSTALL_VER" "$GEN"
    exit 0
  fi
fi

# Fallback for installations where vswhere is unavailable but the conventional
# VC auxiliary scripts exist. Prefer 2022 because it is the documented buyer
# prerequisite for this release.
for edition in BuildTools Community Professional Enterprise; do
  p="/c/Program Files/Microsoft Visual Studio/2022/$edition/VC/Auxiliary/Build/vcvars64.bat"
  if [[ -f "$p" ]]; then
    printf '%s\t%s\t%s\n' "C:\\Program Files\\Microsoft Visual Studio\\2022\\$edition" "17.x" "Visual Studio 17 2022"
    exit 0
  fi
done
for edition in BuildTools Community Professional Enterprise; do
  p="/c/Program Files/Microsoft Visual Studio/2026/$edition/VC/Auxiliary/Build/vcvars64.bat"
  if [[ -f "$p" ]]; then
    printf '%s\t%s\t%s\n' "C:\\Program Files\\Microsoft Visual Studio\\2026\\$edition" "18.x" "Visual Studio 18 2026"
    exit 0
  fi
done

exit 3
