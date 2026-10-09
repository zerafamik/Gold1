# Troubleshooting

## `fast-prime binary path missing`
This is no longer a core setup error. Fast-prime is optional. Run the current package's `./validate_all.sh`; it should print `fastprime_available=False (optional comparator skipped)` and continue.

## Windows `_winapi.CreateProcess` traceback from `tools/matrix.py`

That v2.3.4 failure came from attempting to launch `run_interval_bench.sh` as a native Windows child. v2.3.5 launches `tools/interval_bench.py` through the current Python interpreter and does not require a shell child. Use the new package, open MSYS2 UCRT64, enter the single extracted package directory, and run `./run_interval_matrix.sh`.

## Four-worker run still reports `6+6`

That indicates the v2.3.4 harness. In v2.3.5, `GOLD1_BENCH_THREADS=4` reports either `sequential_4+4` or `concurrent_2+2`; no comparator may run `6+6` under that budget.

## Sequential/concurrent selection changed between otherwise similar cases

v2.3.6 addresses one-shot calibration noise with repeated medians. The default is three samples per protocol, plus two adaptive tie-break samples when the initial medians are within 2%. Increase `GOLD1_PROTOCOL_CALIBRATION_REPEATS` to 5 for a stricter external report, accepting the extra runtime.

## Want fast-prime too?
Run `GOLD1_WITH_FASTPRIME=1 ./setup_all.sh`. On Windows, install Visual Studio C++ Build Tools and Rust first.

## Windows shell
Use MSYS2 **UCRT64**, not ordinary Command Prompt or the MSYS shell.

## Force a clean rebuild
`GOLD1_FORCE_REBUILD=1 ./setup_all.sh`
