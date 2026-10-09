# Packaging notes

Source: original GOLD1 v2.3.6 archive supplied by the project owner. The original archive is unchanged.

Excluded: generated build trees, executable/object/binary artifacts, vendored compressed archives, and original checksum manifests that would become invalid after repackaging.

Original excluded paths are recorded below for audit. The package was not compiled or benchmarked. Third-party licensing and confidential-information clearance remain the publisher's responsibility.

## Excluded paths

- `gold1/build/.ninja_deps`
- `gold1/build/.ninja_log`
- `gold1/build/build.ninja`
- `gold1/build/CMakeCache.txt`
- `gold1/build/CMakeFiles/4.4.3/CMakeCXXCompiler.cmake`
- `gold1/build/CMakeFiles/4.4.3/CMakeDetermineCompilerABI_CXX.bin`
- `gold1/build/CMakeFiles/4.4.3/CMakeRCCompiler.cmake`
- `gold1/build/CMakeFiles/4.4.3/CMakeSystem.cmake`
- `gold1/build/CMakeFiles/4.4.3/CompilerIdCXX/a.exe`
- `gold1/build/CMakeFiles/4.4.3/CompilerIdCXX/CMakeCXXCompilerId.cpp`
- `gold1/build/CMakeFiles/cmake.check_cache`
- `gold1/build/CMakeFiles/CMakeConfigureLog.yaml`
- `gold1/build/CMakeFiles/Export/764f0ab8f423d9408419179ac32c4940/primecountStatic-release.cmake`
- `gold1/build/CMakeFiles/Export/764f0ab8f423d9408419179ac32c4940/primecountStatic.cmake`
- `gold1/build/CMakeFiles/FindOpenMP/ompver_CXX.bin`
- `gold1/build/CMakeFiles/gold1-delta-ac-sched.dir/src/app/gold1_delta_ac_sched_main.cpp.obj`
- `gold1/build/CMakeFiles/gold1-delta-d.dir/src/app/gold1_delta_d_main.cpp.obj`
- `gold1/build/CMakeFiles/gold1-interval.dir/src/app/gold1_interval_main.cpp.obj`
- `gold1/build/CMakeFiles/InstallScripts.json`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/api.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/api_c.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/arch/x86/cpuid.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/BitSieve240.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/deleglise-rivat/pi_deleglise_rivat.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/deleglise-rivat/S2_easy.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/deleglise-rivat/S2_hard.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/deleglise-rivat/S2_trivial.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/FactorTable.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/generate_primes.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/AC.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/B.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/D.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/D_delta_gold1.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/LoadBalancerAC.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/Phi0.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/pi_gourdon.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/SegmentedPiTable.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/gourdon/Sigma.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo1.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo2.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo3.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo4.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo5.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/lmo/pi_lmo_parallel.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/LoadBalancerP2.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/LoadBalancerS2.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/LogarithmicIntegral.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/nth_prime.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/nth_prime_sieve.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/P2.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/P3.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/phi.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/PhiTiny.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/phi_vector.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/PiTable.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/pi_legendre.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/pi_lehmer.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/pi_meissel.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/pi_primesieve.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/print.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/RiemannR.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/S1.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/sieve/pre_sieve.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/sieve/Sieve.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/StatusS2.cpp.obj`
- `gold1/build/CMakeFiles/libprimecount-static.dir/src/util.cpp.obj`
- `gold1/build/CMakeFiles/primecount.dir/src/app/CmdOptions.cpp.obj`
- `gold1/build/CMakeFiles/primecount.dir/src/app/help.cpp.obj`
- `gold1/build/CMakeFiles/primecount.dir/src/app/main.cpp.obj`
- `gold1/build/CMakeFiles/primecount.dir/src/app/test.cpp.obj`
- `gold1/build/CMakeFiles/rules.ninja`
- `gold1/build/CMakeFiles/TargetDirectories.txt`
- `gold1/build/cmake_install.cmake`
- `gold1/build/gold1-delta-ac-sched.exe`
- `gold1/build/gold1-delta-d.exe`
- `gold1/build/gold1-interval.exe`
- `gold1/build/libprimecount.a`
- `gold1/build/primecount.exe`
- `gold1/build/primecount.pc`
- `gold1/build/primecountConfig.cmake`
- `gold1/build/primecountConfigVersion.cmake`
- `gold1/MANIFEST.sha256`
- `gold1/primecount-v8.7.tar.gz`
- `MANIFEST.sha256`
- `results/20260914T103623010415Z_two_way_matrix.zip`
- `SOURCE_PROVENANCE.sha256`
- `third_party/primesieve-ucrt64-prefix/bin/primesieve.exe`
- `third_party/primesieve-v12.15.tar.gz`
- `third_party/primesieve.binary`
- `third_party/primesieve.prefix`
