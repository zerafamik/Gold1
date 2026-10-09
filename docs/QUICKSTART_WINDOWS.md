# Windows quick start - minimum steps

1. Install MSYS2 and open **MSYS2 UCRT64**.
2. Extract the package and `cd` into its inner directory.
3. Run:
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

v2.3.5 launches each matrix child through the same UCRT64 Python interpreter, so Windows is not asked to execute a `.sh` file through `CreateProcess`.

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

No Visual Studio or Rust is required for the default Gold1 + primecount + primesieve benchmark.

Optional fast-prime comparator:
```bash
GOLD1_WITH_FASTPRIME=1 ./setup_all.sh
```
That optional Windows path requires Visual Studio C++ Build Tools and Rust/MSVC.
