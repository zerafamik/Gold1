#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
"""Focused crossover suite around the measured Gold1/primesieve boundary."""
from __future__ import annotations

import matrix

BASE = 10**18
CROSSOVER_MATRIX = [
    (BASE, BASE + 125_000_000_000, "crossover_width_1p25e11_at_1e18"),
    (BASE, BASE + 150_000_000_000, "crossover_width_1p50e11_at_1e18"),
    (BASE, BASE + 175_000_000_000, "crossover_width_1p75e11_at_1e18"),
    (BASE, BASE + 200_000_000_000, "crossover_width_2p00e11_at_1e18"),
]


def main() -> None:
    matrix.main(CROSSOVER_MATRIX, suite_name="crossover_matrix")


if __name__ == "__main__":
    main()
