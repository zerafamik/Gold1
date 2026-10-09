# GOLD1 — Prime-counting ranking benchmark (v2.3.6)

Source-oriented public review package derived from the original September 14, 2026 archive. This repository contains C++/Python source, build scripts, validation tools, methodology and recorded benchmark outputs. It does **not** contain RED2.

## What this demonstrates

GOLD1 benchmarks prime-counting approaches against pinned comparator versions using controlled worker budgets, repeated measurements, and robust protocol calibration. See the original project documentation below for precise claims and reproduction steps. Recorded benchmark results are historical artifacts, **not** independent validation or proof of general superiority.

## Quick start

The original documented Linux / MSYS2 UCRT64 workflow is:

```bash
./setup_all.sh
./validate_all.sh
GOLD1_AC_QUALIFY_REPEATS=5 RANK_RUNS=5 ./run_interval_matrix.sh
```

**Important:** This GitHub-oriented source distribution excludes cached vendor tarballs, compiled build outputs, and generated checksums. Some setup scripts may assume bundled dependency archives. Obtain the versions listed in `DEPENDENCIES.lock`, review setup scripts, and verify dependency availability before executing. Commands above are from the original documentation and have **not** been executed against this repackaged distribution.

## Evidence and attribution

- `results/`: historical measurements (environment and comparison constraints matter).
- `docs/`: setup, history, changes, troubleshooting and handover material.
- `tools/`: benchmark and harness utilities.
- `gold1/`: implementation and associated source.
- `THIRD_PARTY_NOTICE.md`, `gold1/PRIMECOUNT_BSD_2_CLAUSE.txt`: third-party notices.
- `COPYRIGHT.md`: original rights statement; **legal-owner placeholder has not been filled in**. Confirm rights and replace it before publishing.

Do not imply that third-party source is solely original work. The existing licensing documents should be reviewed before public distribution; this packaging is not a legal clearance.

## Archive changes

See `GITHUB_PACKAGING_NOTES.md`.

---

## Original project README

# Gold1 Ranking Benchmark v2.3.6 - Robust Calibration + Crossover Suite

The default setup is intentionally dependency-light: **fast-prime is optional and never blocks Gold1**.

## Three-command path (Windows MSYS2 UCRT64 or Linux)
```bash
./setup_all.sh
./validate_all.sh
GOLD1_AC_QUALIFY_REPEATS=5 RANK_RUNS=5 ./run_interval_matrix.sh
```

Default ranked comparators: Gold1, pinned primecount 8.7, pinned primesieve 12.15.

## Fixed total thread budget

The default is 12 workers. To run a fair four-worker matrix:

```bash
GOLD1_BENCH_THREADS=4 \
GOLD1_AC_QUALIFY_REPEATS=5 \
RANK_RUNS=5 \
./run_interval_matrix.sh
```

Every ranked implementation now honors the same maximum concurrent budget. For two-endpoint comparators, calibration tests sequential `4+4` (four workers per endpoint, one endpoint at a time) against concurrent `2+2` (two workers per endpoint at the same time), then selects the lower robust median. Result JSON and CSV record the budget and selected modes. Compare timings only when the machine, build, interval matrix, run count, and thread budget match.

## Robust protocol calibration

v2.3.6 measures each sequential and concurrent endpoint protocol three times by default, alternating which mode runs first. If the initial medians are within 2%, it automatically adds two tie-break measurements per protocol. It then selects the lower final median, without favoring either implementation. Complete samples, medians, relative gap, tie-break activity, selection, and reason are recorded.

Controls:

```bash
GOLD1_PROTOCOL_CALIBRATION_REPEATS=3
GOLD1_PROTOCOL_TIE_BREAK_REPEATS=2
GOLD1_PROTOCOL_NEAR_TIE=0.02
```

## Focused crossover suite

The validated four-worker matrix placed the Gold1/primesieve crossover near width `1.5e11` at scale `1e18`. Measure the boundary directly with:

```bash
GOLD1_BENCH_THREADS=4 \
GOLD1_PROTOCOL_CALIBRATION_REPEATS=3 \
GOLD1_PROTOCOL_TIE_BREAK_REPEATS=2 \
GOLD1_PROTOCOL_NEAR_TIE=0.02 \
GOLD1_AC_QUALIFY_REPEATS=5 \
RANK_RUNS=7 \
./run_crossover_bench.sh
```

This runs widths `1.25e11`, `1.50e11`, `1.75e11`, and `2.00e11`, saving a separate `crossover_matrix` JSON/CSV pair.

## Optional fast-prime comparator
Only if you want the fourth comparator:
```bash
GOLD1_WITH_FASTPRIME=1 ./setup_all.sh
./validate_all.sh
```
On Windows this optional path needs Visual Studio C++ Build Tools and Rust/MSVC. On Linux it uses native Rust.

## Safety and provenance
Exact validation gates ranking. Gold1 AC repeatability qualification/fallback is retained. CPU/RAM/OS/timestamps, source SHA-256, harness SHA-256 and available binary SHA-256 fingerprints are recorded. Missing optional fast-prime is explicitly recorded as `optional-skipped`; it is never silently treated as a failed competitor.

v2.3.6 preserves the v2.3.4 mathematical implementation, the v2.3.5 portable launcher and fixed thread budget, and every exact-validation gate. Its changes are confined to more robust protocol selection, crossover measurement, reporting, tests, and documentation.

The v2.3.4 optimized common-cutoff Delta-Gourdon path and correctness-first endpoint-specific Gourdon fallback are unchanged. The fallback remains in the same 10-case matrix and is explicitly labelled in result metadata; it is not represented as the paired-D optimized path. The matrix runner still retries one child execution that exits without producing `RESULT_JSON`.

## Complete 10-case matrix
The normal matrix still contains all ten cases, including the 10^14 and 10^15 fixed-width scale tests. A common-cutoff case uses `gold1_execution_mode=common_cutoff_delta`. If no common tuple validates, Gold1 switches to `gold1_execution_mode=dual_cutoff_endpoint_fallback`, reconstructing each endpoint with its own independently selected valid Gourdon tuple before taking the exact difference.

## Owner stamping
Before redistribution, run `./release_stamp.sh "Exact Legal Name"`. This replaces `[YOUR LEGAL NAME]` across release-controlled text and regenerates source provenance plus both SHA-256 manifests.
