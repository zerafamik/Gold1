# Gold1 v0.9.1 — integrated balanced paired-AC + paired-D

Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.

This package integrates the two validated endpoint transformations used in Gold1 count mode:

- **AC:** ordinary upstream primecount v8.7 `AC(H)` and `AC(X)` executed concurrently under one fixed total thread budget. The target machine's v0.9 sweep selected **6+6** under a 12-thread budget.
- **D:** Gold1's validated paired-D thin-interval kernel from v0.7.1/v0.8.
- **Sigma, Phi0, B:** unchanged upstream endpoint calculations.

The exact interval identity remains

`delta_pi = delta_AC - delta_B + delta_D + delta_Phi0 + delta_Sigma`.

## Build / validate / benchmark

```bash
./setup_and_build_ucrt64.sh
./run_validate.sh
./run_bench_3.sh
```

Do not use timings unless validation passes first.

The benchmark compares against both the historical 14.292231 s target and the measured v0.8 median 13.030606 s.

The package-level v2.3.6 harness generalizes the historical 12-thread `6+6` split: `GOLD1_BENCH_THREADS=N` constrains every comparator to one total maximum concurrency budget. It uses repeated-median calibration with a documented near-tie margin and records the complete selection evidence. This changes benchmark orchestration only, not the Gold1 identity or kernels.

primecount remains Copyright (C) Kim Walisch and BSD 2-Clause licensed; see `THIRD_PARTY_NOTICE.md` and `PRIMECOUNT_BSD_2_CLAUSE.txt`.

## v2.3.4 endpoint-specific safety fallback

The preferred path above is unchanged. For generalized matrix intervals where no single endpoint-selected `(y,z,k)` tuple reconstructs both endpoints, `gold1-interval` now also accepts an explicit `--dual-cutoff` mode. It reconstructs `pi(H)` and `pi(X)` with each endpoint's own valid Gourdon tuple and returns their exact difference. This mode is deliberately labelled `dual_cutoff_endpoint_fallback`: it does **not** claim to use the common-cutoff paired-D optimization and should be interpreted separately in performance analysis.
