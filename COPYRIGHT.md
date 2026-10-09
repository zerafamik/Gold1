# Gold1 ranking benchmark copyright

Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.

This claim covers Gold1-authored algorithm modifications, benchmark scripts, adapters, integration code, portable build/bootstrap tooling, provenance logic, documentation and handover materials only.

Before public or commercial redistribution, stamp the exact legal owner across the whole package with:

```bash
./release_stamp.sh "Exact Legal Name"
```

or:

```bash
python3 release_stamp.py "Exact Legal Name"
```

The release stamper replaces all release-controlled text placeholders and then regenerates `SOURCE_PROVENANCE.sha256`, `gold1/MANIFEST.sha256`, and the root `MANIFEST.sha256` in dependency order. The compatibility command `python gold1/set_legal_name.py "Exact Legal Name"` delegates to the same package-wide workflow.

This does not supersede third-party copyright or licenses for primecount, primesieve, fast-prime, Rust/Cargo crates, compilers, build systems or operating-system tooling. See `THIRD_PARTY_NOTICE.md` and `gold1/PRIMECOUNT_BSD_2_CLAUSE.txt`.
