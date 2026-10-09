# Gold1 v0.9.1 direction freeze

Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.

## Preserved winner
Gold1 v0.8 exact interval count median: **13.030606 s**, target: **14.292231 s**.

## New isolated result
The v0.9 AC scheduler sweep selected **6+6** as the best split under the same total 12-thread budget.

## v0.9.1 hypothesis
Integrate balanced 6+6 AC endpoint concurrency into the already-correct v0.8 full interval path while preserving the paired-D thin-interval kernel unchanged.

No AC arithmetic is altered. The experiment changes scheduling only.

## Gates
1. AC(H), AC(X), delta_AC must equal upstream sequential 12-thread values.
2. Paired D must equal D(H)-D(X).
3. Full interval must equal 2,412,731,214.
4. Only then compare v0.9.1 wall time against v0.8 median 13.030606 s.
