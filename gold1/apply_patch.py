#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
from pathlib import Path
import shutil, sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_patch.py /path/to/primecount-8.7")
root = Path(sys.argv[1]).resolve()
cmake = root / "CMakeLists.txt"
gourdon = root / "include" / "gourdon.hpp"
if not cmake.exists() or not gourdon.exists():
    raise SystemExit(f"Not a primecount source tree: {root}")

ctext = cmake.read_text(encoding="utf-8")
if "project(primecount" not in ctext or "VERSION 8.7" not in ctext:
    raise SystemExit("Gold1 v0.9 is pinned to primecount v8.7; VERSION 8.7 not found.")

here = Path(__file__).resolve().parent
for name, dst in [
    ("D_delta_gold1.cpp", root / "src" / "gourdon" / "D_delta_gold1.cpp"),
    ("gold1_delta_d_main.cpp", root / "src" / "app" / "gold1_delta_d_main.cpp"),
    ("gold1_interval_main.cpp", root / "src" / "app" / "gold1_interval_main.cpp"),
    ("gold1_delta_ac_sched_main.cpp", root / "src" / "app" / "gold1_delta_ac_sched_main.cpp"),
]:
    shutil.copy2(here / "patch" / name, dst)

if "src/gourdon/D_delta_gold1.cpp" not in ctext:
    needle = "src/gourdon/D.cpp"
    if needle not in ctext:
        raise SystemExit("Could not find src/gourdon/D.cpp in CMakeLists.txt")
    ctext = ctext.replace(needle, needle + "\n            src/gourdon/D_delta_gold1.cpp", 1)

marker = "# Install header #####################################################"
block = r'''
# Gold1 experimental harnesses ########################################
find_package(Threads REQUIRED)

add_executable(gold1-delta-d src/app/gold1_delta_d_main.cpp)
target_link_libraries(gold1-delta-d PRIVATE primecount::primecount primesieve::primesieve)
target_include_directories(gold1-delta-d PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_definitions(gold1-delta-d PRIVATE ${PRIMECOUNT_COMPILE_DEFINITIONS})
target_compile_features(gold1-delta-d PRIVATE cxx_auto_type)

add_executable(gold1-interval src/app/gold1_interval_main.cpp)
target_link_libraries(gold1-interval PRIVATE primecount::primecount primesieve::primesieve Threads::Threads)
target_include_directories(gold1-interval PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_definitions(gold1-interval PRIVATE ${PRIMECOUNT_COMPILE_DEFINITIONS})
target_compile_features(gold1-interval PRIVATE cxx_auto_type)

add_executable(gold1-delta-ac-sched src/app/gold1_delta_ac_sched_main.cpp)
target_link_libraries(gold1-delta-ac-sched PRIVATE primecount::primecount primesieve::primesieve Threads::Threads)
target_include_directories(gold1-delta-ac-sched PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_compile_definitions(gold1-delta-ac-sched PRIVATE ${PRIMECOUNT_COMPILE_DEFINITIONS})
target_compile_features(gold1-delta-ac-sched PRIVATE cxx_auto_type)

'''
if "add_executable(gold1-delta-ac-sched" not in ctext:
    if marker not in ctext:
        raise SystemExit("Could not find CMake install-header marker")
    ctext = ctext.replace(marker, block + marker, 1)
cmake.write_text(ctext, encoding="utf-8")

gtext = gourdon.read_text(encoding="utf-8")
decl = "int64_t Gold1_D_delta(int64_t H, int64_t X, int64_t y, int64_t z, int64_t k, int threads, bool print = is_print());\n"
if "Gold1_D_delta" not in gtext:
    needle = "int64_t D(int64_t x, int64_t y, int64_t z, int64_t k, int threads, bool print = is_print());\n"
    if needle not in gtext:
        raise SystemExit("Could not find D() declaration in gourdon.hpp")
    gtext = gtext.replace(needle, needle + decl, 1)
    gourdon.write_text(gtext, encoding="utf-8")

print("Patched primecount v8.7 with Gold1 v0.9.1 integrated balanced paired-AC prototype.")
