# Third-party notice

Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved for Gold1-authored modifications, benchmark integration, scripts, provenance tooling and documentation.

This handover package builds or interfaces with third-party projects:

- **primecount 8.7** - Kim Walisch / contributors; upstream BSD licensing applies. Gold1 patches a pinned primecount 8.7 source tree locally during setup.
- **primesieve 12.15** - Kim Walisch / contributors; upstream BSD licensing applies. This release builds a pinned package-local copy for reproducibility.
- **fast-prime** - `secwest/fast-prime`, pinned at commit `ad2642f917526e2de0e45833b1a242c10963568f`; the upstream repository identifies the project as MIT licensed. The repository is cloned at setup time and is not bundled as Gold1-authored source.
- **Rust/rustup/Cargo and transitive crates** - used only when the optional fast-prime comparator is enabled; retain their respective upstream licenses.
- **MSYS2 / GCC / CMake / Ninja / Python** - core development/runtime tooling on Windows. Microsoft Visual C++ Build Tools are needed only for the optional Windows fast-prime comparator. All remain subject to their own terms.

Gold1's fast-prime adapter is benchmark plumbing only: native library search path, arbitrary-x CLI entry and an explicit benchmark worker-budget override. It does not replace `count_primes()` or claim authorship over fast-prime's algorithm.

For redistribution of any third-party source or binary produced by setup, retain all upstream copyright and license notices required by those projects. A commercial transfer of Gold1 should describe the assigned/licensed asset as Gold1-authored modifications, integration code, documentation, benchmark evidence and know-how, not exclusive ownership of upstream third-party projects.
