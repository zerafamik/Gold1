# Copyright and provenance

Gold1-authored additions and modifications in this package are marked:

```text
Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
```

Replace `[YOUR LEGAL NAME]` package-wide before public or commercial redistribution using the root release stamper:

```bash
./release_stamp.sh "Exact Legal Name"
```

The older command remains supported as a compatibility wrapper:

```bash
python gold1/set_legal_name.py "Exact Legal Name"
```

Both routes now update the full release, not just `gold1/`, and regenerate the source provenance plus both SHA-256 manifests so owner stamping does not leave stale integrity metadata.

That claim applies only to Gold1-authored material and modifications. It does not replace upstream rights in primecount-derived portions. The derived D kernel preserves primecount attribution, and the upstream BSD 2-Clause text is included in `PRIMECOUNT_BSD_2_CLAUSE.txt`.
