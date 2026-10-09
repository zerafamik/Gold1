# Gold1 v2.3.6 Installation and Handover

## Buyer acceptance path
Three commands are sufficient on the supported reference environments:

```bash
./setup_all.sh
./validate_all.sh
GOLD1_AC_QUALIFY_REPEATS=5 RANK_RUNS=5 ./run_interval_matrix.sh
```

### Default dependency surface
- C++17-capable GCC/Clang toolchain
- CMake + Ninja
- Python 3
- Git/curl/tar
- pinned primesieve 12.15 (built package-locally)
- pinned primecount 8.7 source patched with Gold1

On Windows these are installed through MSYS2 UCRT64 packages. On supported Linux distributions the package installer script bootstraps them.

### Optional comparator
fast-prime V8 is a fourth comparator only. It is **not required to build, validate, or benchmark Gold1**. Enable it with `GOLD1_WITH_FASTPRIME=1 ./setup_all.sh`. Windows then requires Visual Studio C++ Build Tools + Rust/MSVC; Linux uses native Rust.

### Reproducibility
Every result records available hardware/OS metadata, UTC start/finish times, source and harness hashes, and hashes for each comparator binary actually used. Optional components are labelled rather than silently omitted.

## v2.3.5 portable fixed-budget harness

The matrix runner launches benchmark children with the same Python executable that launched the matrix. This works on Linux and in Windows MSYS2 UCRT64 without passing a `.sh` file to Windows `CreateProcess`.

`GOLD1_BENCH_THREADS` is a fixed maximum concurrency budget shared by all ranked implementations. A four-worker run calibrates sequential `4+4` against concurrent `2+2`; it never silently uses the old hard-coded `6+6` comparator split. The selected budget, split, and modes are recorded in the result files. The Gold1 mathematical implementation is unchanged from v2.3.4.

## v2.3.6 robust selection and crossover measurement

Protocol calibration now uses repeated, alternating-order samples and median comparison. If the initial relative median gap is below `GOLD1_PROTOCOL_NEAR_TIE` (default 0.02), the harness adds `GOLD1_PROTOCOL_TIE_BREAK_REPEATS` measurements per protocol (default 2). It then selects the lower final median. This prevents a near-tie from being decided by one noisy measurement without imposing a preferred mode.

`run_crossover_bench.sh` measures four widths around the locally estimated Gold1/primesieve crossover at scale `1e18`. Results are emitted separately as `*_crossover_matrix.json` and `*.csv`, with the calibration evidence retained inside each child result.


## v2.3.4 full-matrix fallback
The standard matrix keeps all ten cases. Gold1 first tries the original common-cutoff Delta-Gourdon route. When neither endpoint-selected common tuple validates both endpoints, the same executable uses an exact endpoint-specific Gourdon fallback and records that mode explicitly. This avoids dropping the case while preserving the distinction between the optimized paired-D path and the safety fallback.

## Release stamping
Run `./release_stamp.sh "Exact Legal Name"` before redistribution. The package-wide stamper replaces owner placeholders and regenerates `SOURCE_PROVENANCE.sha256`, `gold1/MANIFEST.sha256`, and `MANIFEST.sha256`, so legal-name stamping cannot silently invalidate the integrity metadata.
