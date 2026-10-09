#!/usr/bin/env python3
# Compatibility wrapper for the original fixed challenge.
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
from __future__ import annotations
import argparse, os
from interval_bench import benchmark_task, prepare_task, validate_task

L=1000000000000000000
H=1000000100000000000

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode", choices=["validate","benchmark"])
    ap.add_argument("--runs", type=int, default=int(os.environ.get("RANK_RUNS","5")))
    ap.add_argument("--timeout", type=int, default=int(os.environ.get("RANK_TIMEOUT","600")))
    a=ap.parse_args()
    if a.mode=="validate":
        task=prepare_task(L,H,timeout=max(a.timeout,1200))
        raise SystemExit(validate_task(task,True,a.timeout))
    benchmark_task(L,H,a.runs,a.timeout)

if __name__=="__main__": main()
