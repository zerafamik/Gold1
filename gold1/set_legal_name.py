#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
"""Compatibility wrapper for the package-wide v2.3.6 release stamper."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STAMPER = ROOT / "release_stamp.py"
if len(sys.argv) != 2 or not sys.argv[1].strip():
    raise SystemExit('usage: python set_legal_name.py "Exact Legal Name"')
raise SystemExit(subprocess.call([sys.executable, str(STAMPER), sys.argv[1]]))
