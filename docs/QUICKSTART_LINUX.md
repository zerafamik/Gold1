# Linux quick start - minimum steps

Extract the package, enter the directory, then run:
```bash
./setup_all.sh
./validate_all.sh
GOLD1_AC_QUALIFY_REPEATS=5 RANK_RUNS=5 ./run_interval_matrix.sh
```

For a fixed four-worker comparison:

```bash
GOLD1_BENCH_THREADS=4 \
GOLD1_AC_QUALIFY_REPEATS=5 \
RANK_RUNS=5 \
./run_interval_matrix.sh
```

All implementations use the same maximum concurrent thread budget. Do not compare results produced with different budgets as if they were the same benchmark.

Focused crossover measurement:

```bash
GOLD1_BENCH_THREADS=4 \
GOLD1_PROTOCOL_CALIBRATION_REPEATS=3 \
GOLD1_PROTOCOL_TIE_BREAK_REPEATS=2 \
GOLD1_PROTOCOL_NEAR_TIE=0.02 \
GOLD1_AC_QUALIFY_REPEATS=5 \
RANK_RUNS=7 \
./run_crossover_bench.sh
```
`setup_all.sh` installs supported distro prerequisites and builds pinned primesieve 12.15 plus Gold1/primecount. Rust is not downloaded by default.

Optional fast-prime comparator:
```bash
GOLD1_WITH_FASTPRIME=1 ./setup_all.sh
```
