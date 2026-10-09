#!/usr/bin/env bash
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; cd "$ROOT"
EXE="./build/gold1-interval.exe"; [[ -x "$EXE" ]] || EXE="./build/gold1-interval"
[[ -x "$EXE" ]] || { echo "Missing gold1-interval binary. Run ./setup_and_build_ucrt64.sh first." >&2; exit 2; }
./run_validate.sh >/dev/null
H=1000000100000000000; X=999999999999999999; Y=32221967; Z=32221967; K=8; THREADS=12
EXPECTED=2412731214; RUNS="${GOLD1_RUNS:-3}"; TARGET_SECONDS="${GOLD1_TARGET_SECONDS:-14.292231}"
V08_MEDIAN="${GOLD1_V08_MEDIAN:-13.030606}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"; OUTFILE="${STAMP}_gold1_v091_full_interval_bench.txt"
{
 echo "Gold1 v0.9.1 integrated balanced paired-AC + paired-D benchmark"
 echo "UTC=$STAMP"; echo "target_seconds=$TARGET_SECONDS"; echo "v08_median_seconds=$V08_MEDIAN"; echo
} | tee "$OUTFILE"
for ((i=1;i<=RUNS;++i)); do
 echo "===== RUN $i =====" | tee -a "$OUTFILE"
 OUT="$($EXE "$H" "$X" "$Y" "$Z" "$K" "$THREADS")"
 printf '%s\n' "$OUT" | tee -a "$OUTFILE"
 COUNT="$(printf '%s\n' "$OUT" | sed -n 's/^interval_count=//p' | head -n1)"
 [[ "$COUNT" == "$EXPECTED" ]] || { echo "BENCHMARK ABORT: expected $EXPECTED got $COUNT" | tee -a "$OUTFILE" >&2; exit 1; }
 echo | tee -a "$OUTFILE"
done
python - "$OUTFILE" "$TARGET_SECONDS" "$V08_MEDIAN" <<'PY' | tee -a "$OUTFILE"
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
import re,statistics,sys
p,target,v08=sys.argv[1],float(sys.argv[2]),float(sys.argv[3])
text=open(p,encoding='utf-8').read()
vals=[float(x) for x in re.findall(r'^gold1_seconds=([0-9.]+)$',text,re.M)]
acs=[float(x) for x in re.findall(r'^AC_pair_seconds=([0-9.]+)$',text,re.M)]
if not vals: raise SystemExit('No gold1_seconds values found')
mean=statistics.mean(vals); med=statistics.median(vals)
print('===== SUMMARY =====')
print('runs='+','.join(f'{v:.6f}' for v in vals))
if acs: print('ac_runs='+','.join(f'{v:.6f}' for v in acs))
print(f'mean_seconds={mean:.6f}'); print(f'median_seconds={med:.6f}')
print(f'min_seconds={min(vals):.6f}'); print(f'max_seconds={max(vals):.6f}')
print(f'target_seconds={target:.6f}'); print(f'target_margin_seconds={target-med:.6f}')
print(f'target_over_median={target/med:.6f}x')
print(f'v08_median_seconds={v08:.6f}'); print(f'v091_vs_v08_saved_seconds={v08-med:.6f}')
print(f'v091_vs_v08_speedup={v08/med:.6f}x')
print('TARGET_RESULT='+('PASS' if med<target else 'NOT_YET'))
print('V08_RESULT='+('FASTER' if med<v08 else 'NO_GAIN'))
PY
echo; echo "Saved benchmark: $OUTFILE"
