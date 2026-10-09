#!/usr/bin/env bash
set -euo pipefail
if [[ "${GOLD1_SKIP_OS_PACKAGES:-0}" == "1" ]]; then echo "Skipping OS package install."; exit 0; fi
if [[ "$(id -u)" -eq 0 ]]; then SUDO=""; elif command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else echo "ERROR: root or sudo required." >&2; exit 10; fi
if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update
  $SUDO apt-get install -y build-essential cmake ninja-build git curl ca-certificates python3 pkg-config tar xz-utils
elif command -v dnf >/dev/null 2>&1; then
  $SUDO dnf install -y gcc gcc-c++ cmake ninja-build git curl ca-certificates python3 pkgconf-pkg-config tar xz
elif command -v pacman >/dev/null 2>&1; then
  $SUDO pacman -S --needed --noconfirm base-devel cmake ninja git curl ca-certificates python pkgconf tar xz
elif command -v zypper >/dev/null 2>&1; then
  $SUDO zypper --non-interactive install gcc gcc-c++ cmake ninja git curl ca-certificates python3 pkg-config tar xz
else
  echo "ERROR: unsupported package manager. Install a C/C++ compiler, CMake, Ninja, Git, curl, Python 3.10+, pkg-config, tar and xz." >&2; exit 11
fi
for c in c++ cmake ninja git curl python3; do command -v "$c" >/dev/null || { echo "ERROR: missing $c" >&2; exit 12; }; done
