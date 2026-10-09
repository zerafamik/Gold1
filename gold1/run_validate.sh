#!/usr/bin/env bash
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
EXE="./build/gold1-interval.exe"; [[ -x "$EXE" ]] || EXE="./build/gold1-interval"
[[ -x "$EXE" ]] || { echo "Missing gold1-interval binary. Run ./setup_and_build_ucrt64.sh first." >&2; exit 2; }
H=1000000100000000000; X=999999999999999999; Y=32221967; Z=32221967; K=8; THREADS=12
EXPECTED_INTERVAL=2412731214; EXPECTED_H=24739956700472074; EXPECTED_X=24739954287740860
EXPECTED_D=2369207085; EXPECTED_AC=917059744
set +e
OUT="$($EXE "$H" "$X" "$Y" "$Z" "$K" "$THREADS" --verify 2>&1)"; STATUS=$?
set -e
printf '%s\n' "$OUT"
[[ $STATUS -eq 0 ]] || { echo "VALIDATION FAIL: executable returned status $STATUS" >&2; exit "$STATUS"; }
get_field(){ printf '%s\n' "$OUT" | sed -n "s/^$1=//p" | head -n1; }
[[ "$(get_field interval_count)" == "$EXPECTED_INTERVAL" ]] || { echo "FAIL interval" >&2; exit 1; }
[[ "$(get_field reference_interval_count)" == "$EXPECTED_INTERVAL" ]] || { echo "FAIL reference interval" >&2; exit 1; }
[[ "$(get_field pi_H_common)" == "$EXPECTED_H" ]] || { echo "FAIL pi(H)" >&2; exit 1; }
[[ "$(get_field pi_X_common)" == "$EXPECTED_X" ]] || { echo "FAIL pi(X)" >&2; exit 1; }
[[ "$(get_field delta_D)" == "$EXPECTED_D" ]] || { echo "FAIL delta D" >&2; exit 1; }
[[ "$(get_field delta_AC)" == "$EXPECTED_AC" ]] || { echo "FAIL delta AC" >&2; exit 1; }
[[ "$(get_field reference_delta_AC)" == "$EXPECTED_AC" ]] || { echo "FAIL reference delta AC" >&2; exit 1; }
echo "TARGET CHECK PASS: interval_count=$EXPECTED_INTERVAL"
echo "ENDPOINT CHECK PASS: pi(H)=$EXPECTED_H pi(X)=$EXPECTED_X"
echo "AC CHECK PASS: scheduler=6+6 delta_AC=$EXPECTED_AC"
echo "D CHECK PASS: delta_D=$EXPECTED_D"
