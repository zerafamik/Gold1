#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
"""Gold1 generalized exact-interval ranking harness v2.3.6.

Benchmark-only orchestration. It does not modify the mathematics of Gold1,
primecount, fast-prime, or primesieve.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

THREADS = int(os.environ.get("GOLD1_BENCH_THREADS", "12"))
if THREADS < 2:
    raise RuntimeError("GOLD1_BENCH_THREADS must be >= 2")
SCHEMA_VERSION = "2.3.6-robust-calibration-crossover"
ROOT = Path(__file__).resolve().parents[1]
GOLD1 = ROOT / "gold1" / "build" / "gold1-interval.exe"
if not GOLD1.exists():
    GOLD1 = ROOT / "gold1" / "build" / "gold1-interval"
PRIMECOUNT = ROOT / "gold1" / "build" / "primecount.exe"
if not PRIMECOUNT.exists():
    PRIMECOUNT = ROOT / "gold1" / "build" / "primecount"
FP_BIN_FILE = ROOT / "third_party" / "fast-prime.binary"


class UnsupportedInterval(RuntimeError):
    pass


def thread_plan(total: int | None = None) -> dict[str, int]:
    """Allocate one fixed concurrency budget across two endpoint processes."""
    budget = THREADS if total is None else total
    if budget < 2:
        raise ValueError("thread budget must be >= 2")
    high = budget // 2
    return {
        "total": budget,
        "concurrent_high": high,
        "concurrent_low": budget - high,
        "sequential_per_endpoint": budget,
    }


def endpoint_pair_modes(total: int | None = None) -> tuple[str, str]:
    plan = thread_plan(total)
    sequential = f"sequential_{plan['sequential_per_endpoint']}+{plan['sequential_per_endpoint']}"
    concurrent = f"concurrent_{plan['concurrent_high']}+{plan['concurrent_low']}"
    return sequential, concurrent


def calibration_policy() -> tuple[int, int, float]:
    """Read and validate the robust protocol-selection policy."""
    repeats = int(os.environ.get("GOLD1_PROTOCOL_CALIBRATION_REPEATS", "3"))
    tie_break_repeats = int(os.environ.get("GOLD1_PROTOCOL_TIE_BREAK_REPEATS", "2"))
    near_tie = float(os.environ.get("GOLD1_PROTOCOL_NEAR_TIE", "0.02"))
    if repeats < 1:
        raise ValueError("GOLD1_PROTOCOL_CALIBRATION_REPEATS must be >= 1")
    if tie_break_repeats < 0:
        raise ValueError("GOLD1_PROTOCOL_TIE_BREAK_REPEATS must be >= 0")
    if not 0.0 <= near_tie < 1.0:
        raise ValueError("GOLD1_PROTOCOL_NEAR_TIE must be in [0, 1)")
    return repeats, tie_break_repeats, near_tie


def select_endpoint_protocol(sequential_samples: list[float],
                             concurrent_samples: list[float],
                             sequential_mode: str, concurrent_mode: str,
                             near_tie_margin: float) -> tuple[str, dict[str, Any]]:
    """Select the lower median and identify whether the result remains a near-tie."""
    if not sequential_samples or not concurrent_samples:
        raise ValueError("both calibration sample sets must be non-empty")
    sequential_median = statistics.median(sequential_samples)
    concurrent_median = statistics.median(concurrent_samples)
    concurrent_relative_gain = (
        (sequential_median - concurrent_median) / sequential_median
        if sequential_median > 0 else float("-inf")
    )
    relative_gap = abs(concurrent_relative_gain)
    near_tie = relative_gap < near_tie_margin
    selected = concurrent_mode if concurrent_median < sequential_median else sequential_mode
    reason = ("lower repeated median after near-tie evaluation" if near_tie
              else "lower repeated median")
    return selected, {
        # Retain the v2.3.5 scalar keys for downstream compatibility.
        "sequential": sequential_median,
        "concurrent": concurrent_median,
        "sequential_samples": sequential_samples,
        "concurrent_samples": concurrent_samples,
        "sequential_median": sequential_median,
        "concurrent_median": concurrent_median,
        "concurrent_relative_gain": concurrent_relative_gain,
        "relative_median_gap": relative_gap,
        "near_tie_margin": near_tie_margin,
        "near_tie": near_tie,
        "sequential_mode": sequential_mode,
        "concurrent_mode": concurrent_mode,
        "selected_mode": selected,
        "selection_reason": reason,
    }


@dataclass(frozen=True)
class Task:
    L: int
    H: int
    X: int
    pi_H: int
    pi_X: int
    interval: int
    # Common-cutoff fields are populated for the optimized Delta-Gourdon path.
    # On the endpoint-specific safety fallback they mirror the lower endpoint only
    # for backward compatibility and common_gourdon is emitted as null.
    y: int
    z: int
    k: int
    cutoff_source: str
    endpoint_status: dict[str, Any]
    execution_mode: str
    high_cutoff: dict[str, int]
    low_cutoff: dict[str, int]
    gold1_ac_mode: str
    ac_scheduler_qualification: dict[str, Any]


def clean_output(s: str) -> str:
    return re.sub(r"[,_\s]", "", s)


def run_cmd(cmd, env=None, timeout=600):
    e = os.environ.copy()
    if env:
        e.update({k: str(v) for k, v in env.items()})
    t0 = time.perf_counter()
    p = subprocess.run([str(x) for x in cmd], stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, env=e,
                       timeout=timeout)
    return p.returncode, p.stdout, time.perf_counter() - t0


def expected_in_output(out: str, expected: int) -> bool:
    return str(expected) in clean_output(out)


def parse_last_integer(out: str) -> int:
    # primecount's ordinary CLI prints pi(x) as the final integer-bearing line.
    vals = []
    for line in out.splitlines():
        t = line.strip().replace(",", "").replace("_", "")
        if re.fullmatch(r"[+-]?\d+", t):
            vals.append(int(t))
    if not vals:
        raise ValueError("no standalone integer found in output")
    return vals[-1]


def primecount_reference(n: int, timeout=600):
    rc, out, dt = run_cmd([PRIMECOUNT, n, "--gourdon", f"--threads={THREADS}"], timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"primecount reference failed for {n}:\n{out}")
    value = parse_last_integer(out)
    return {"value": value, "seconds": dt, "output": out, "returncode": rc}


def parse_gourdon_status(out: str) -> dict[str, int]:
    def one(name: str) -> int:
        m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(\d+)\s*$", out)
        if not m:
            raise ValueError(f"missing {name}=... in primecount status output")
        return int(m.group(1))
    return {"y": one("y"), "z": one("z"), "k": one("k")}


def primecount_status(n: int, expected: int, timeout=600):
    rc, out, dt = run_cmd(
        [PRIMECOUNT, n, "--gourdon", f"--threads={THREADS}", "--status"],
        timeout=timeout,
    )
    if rc != 0 or not expected_in_output(out, expected):
        raise RuntimeError(f"primecount status/reference mismatch for {n}:\n{out}")
    params = parse_gourdon_status(out)
    return {**params, "seconds": dt, "output": out}


def parse_gold1_verify(out: str) -> dict[str, int]:
    keys = ["pi_H_common", "pi_X_common", "reference_interval_count"]
    ans = {}
    for key in keys:
        m = re.search(rf"(?m)^{re.escape(key)}=(-?\d+)\s*$", out)
        if not m:
            raise ValueError(f"missing {key} from Gold1 verification output")
        ans[key] = int(m.group(1))
    return ans


def parse_gold1_dual_verify(out: str) -> dict[str, int]:
    keys = ["pi_H_endpoint", "pi_X_endpoint", "reference_interval_count"]
    ans = {}
    for key in keys:
        m = re.search(rf"(?m)^{re.escape(key)}=(-?\d+)\s*$", out)
        if not m:
            raise ValueError(f"missing {key} from Gold1 dual-cutoff verification output")
        ans[key] = int(m.group(1))
    return ans


def gold1_verify_candidate(H: int, X: int, y: int, z: int, k: int,
                           pi_H: int, pi_X: int, interval: int,
                           timeout=1200, ac_mode="balanced"):
    cmd = [GOLD1, H, X, y, z, k, THREADS, "--verify"]
    if ac_mode == "sequential":
        cmd.append("--ac-sequential")
    elif ac_mode != "balanced":
        raise ValueError(f"unknown Gold1 AC mode: {ac_mode}")
    rc, out, dt = run_cmd(cmd, timeout=timeout)
    parsed = {}
    try:
        parsed = parse_gold1_verify(out)
    except Exception:
        pass
    ok = (
        rc == 0
        and parsed.get("pi_H_common") == pi_H
        and parsed.get("pi_X_common") == pi_X
        and parsed.get("reference_interval_count") == interval
        and "PASS: selected AC scheduler, paired D, and integrated interval all match upstream." in out
    )
    return {"ok": ok, "seconds": dt, "output": out, "returncode": rc,
            "ac_mode": ac_mode, **parsed}


def gold1_verify_dual_candidate(H: int, X: int, high: dict[str, int], low: dict[str, int],
                                pi_H: int, pi_X: int, interval: int, timeout=1200):
    cmd = [GOLD1, H, X, high["y"], high["z"], high["k"],
           low["y"], low["z"], low["k"], THREADS, "--dual-cutoff", "--verify"]
    rc, out, dt = run_cmd(cmd, timeout=timeout)
    parsed = {}
    try:
        parsed = parse_gold1_dual_verify(out)
    except Exception:
        pass
    ok = (
        rc == 0
        and parsed.get("pi_H_endpoint") == pi_H
        and parsed.get("pi_X_endpoint") == pi_X
        and parsed.get("reference_interval_count") == interval
        and "PASS: endpoint-specific Gourdon fallback reconstructed both endpoints." in out
    )
    return {"ok": ok, "seconds": dt, "output": out, "returncode": rc, **parsed}


def prepare_task(L: int, H: int, timeout=1200) -> Task:
    if L < 2 or H < L:
        raise UnsupportedInterval("require H >= L >= 2")
    X = L - 1
    if H > 9_223_372_036_854_775_807:
        raise UnsupportedInterval("Gold1 current CLI uses signed int64 endpoints")
    if not GOLD1.exists() or not PRIMECOUNT.exists():
        raise RuntimeError("Gold1/primecount binaries missing; run ./setup_all.sh")

    # Reference generation is intentionally outside measured rounds.
    rh = primecount_reference(H, timeout)
    rx = primecount_reference(X, timeout)
    pi_H, pi_X = rh["value"], rx["value"]
    interval = pi_H - pi_X

    sh = primecount_status(H, pi_H, timeout)
    sx = primecount_status(X, pi_X, timeout)
    high_cutoff = {q: int(sh[q]) for q in ("y", "z", "k")}
    low_cutoff = {q: int(sx[q]) for q in ("y", "z", "k")}

    # Preferred path: one common cutoff, preserving the optimized paired-D design.
    # A small retry budget restores the earlier v2.2.3 behavior at cases such as
    # 10^15 where a correct sequential common-cutoff run has been observed.
    candidates = [
        ("lower_endpoint", sx["y"], sx["z"], sx["k"]),
        ("upper_endpoint", sh["y"], sh["z"], sh["k"]),
    ]
    seen = set()
    attempts = []
    chosen = None
    verify_attempts = max(1, int(os.environ.get("GOLD1_COMMON_VERIFY_ATTEMPTS", "3")))
    required_successes = min(2, verify_attempts)
    for source, y, z, k in candidates:
        tup = (y, z, k)
        if tup in seen:
            continue
        seen.add(tup)
        successes = 0
        for attempt_no in range(1, verify_attempts + 1):
            v = gold1_verify_candidate(H, X, y, z, k, pi_H, pi_X, interval,
                                       timeout, ac_mode="sequential")
            attempts.append({"source": source, "y": y, "z": z, "k": k,
                             "attempt": attempt_no, "ok": v["ok"],
                             "seconds": v["seconds"],
                             "verification_ac_mode": "sequential"})
            successes += int(bool(v["ok"]))
            if successes >= required_successes:
                chosen = (source, y, z, k)
                break
            if successes + (verify_attempts - attempt_no) < required_successes:
                break
        if chosen is not None:
            break

    status_meta = {
        "high": {x: sh[x] for x in ("y", "z", "k", "seconds")},
        "low": {x: sx[x] for x in ("y", "z", "k", "seconds")},
        "candidate_attempts": attempts,
        "reference_generation_seconds": {"pi_H": rh["seconds"], "pi_X": rx["seconds"]},
    }

    if chosen is None:
        # Safety path: retain the case in the SAME matrix and reconstruct H and X
        # with their own primecount-selected Gourdon cutoffs. This is exact but it
        # is not the proprietary common-cutoff paired-D optimization, so results
        # explicitly record the different execution mode.
        dual = gold1_verify_dual_candidate(H, X, high_cutoff, low_cutoff,
                                           pi_H, pi_X, interval, timeout)
        status_meta["dual_cutoff_verification"] = {
            "ok": dual["ok"], "seconds": dual["seconds"],
            "returncode": dual["returncode"]
        }
        if not dual["ok"]:
            detail = "; ".join(
                f"{a['source']} attempt={a['attempt']} y={a['y']} z={a['z']} k={a['k']} ok={a['ok']}"
                for a in attempts
            )
            raise UnsupportedInterval(
                "neither common-cutoff Delta-Gourdon nor endpoint-specific exact fallback "
                "reproduced both reference endpoints; " + detail
            )
        scheduler_qualification = {
            "selected_ac_mode": "endpoint_specific_sequential",
            "fallback_reason": (
                "no endpoint-selected common Gourdon cutoff passed sequential verification; "
                "using exact endpoint-specific Gourdon fallback inside the normal matrix"
            ),
            "common_verify_attempts_per_candidate": verify_attempts,
            "common_verify_required_successes": required_successes,
        }
        return Task(
            L=L, H=H, X=X, pi_H=pi_H, pi_X=pi_X, interval=interval,
            y=low_cutoff["y"], z=low_cutoff["z"], k=low_cutoff["k"],
            cutoff_source="not_applicable_endpoint_specific",
            endpoint_status=status_meta, execution_mode="dual_cutoff_endpoint_fallback",
            high_cutoff=high_cutoff, low_cutoff=low_cutoff,
            gold1_ac_mode="endpoint_specific_sequential",
            ac_scheduler_qualification=scheduler_qualification,
        )

    source, y, z, k = chosen

    # Qualify the faster balanced in-process AC scheduler for this exact
    # interval/cutoff tuple. If not repeatably exact, use sequential endpoint AC.
    qualify_repeats = int(os.environ.get("GOLD1_AC_QUALIFY_REPEATS", "3"))
    qualify_repeats = max(2, qualify_repeats)
    balanced_attempts = []
    balanced_ok = True
    for i in range(qualify_repeats):
        q = gold1_verify_candidate(H, X, y, z, k, pi_H, pi_X, interval,
                                   timeout, ac_mode="balanced")
        balanced_attempts.append({
            "attempt": i + 1, "ok": q["ok"], "seconds": q["seconds"],
            "returncode": q["returncode"]
        })
        if not q["ok"]:
            balanced_ok = False
            break

    gold1_ac_mode = "balanced" if balanced_ok else "sequential"
    hi_threads = THREADS // 2
    lo_threads = THREADS - hi_threads
    scheduler_qualification = {
        "requested_balanced_repeats": qualify_repeats,
        "balanced_attempts": balanced_attempts,
        "selected_ac_mode": gold1_ac_mode,
        "fallback_reason": None if balanced_ok else
            f"balanced {hi_threads}+{lo_threads} AC did not pass repeatable exact verification; "
            f"using sequential {THREADS}+{THREADS} AC",
        "common_verify_attempts_per_candidate": verify_attempts,
        "common_verify_required_successes": required_successes,
    }

    return Task(
        L=L, H=H, X=X, pi_H=pi_H, pi_X=pi_X, interval=interval,
        y=y, z=z, k=k, cutoff_source=source, endpoint_status=status_meta,
        execution_mode="common_cutoff_delta", high_cutoff=high_cutoff,
        low_cutoff=low_cutoff, gold1_ac_mode=gold1_ac_mode,
        ac_scheduler_qualification=scheduler_qualification,
    )


def switch_to_dual_fallback(task: Task, timeout=1200, reason: str = "common-cutoff validation failed") -> Task | None:
    dual = gold1_verify_dual_candidate(
        task.H, task.X, task.high_cutoff, task.low_cutoff,
        task.pi_H, task.pi_X, task.interval, timeout
    )
    if not dual["ok"]:
        return None
    status_meta = dict(task.endpoint_status)
    status_meta["dual_cutoff_verification_after_common_failure"] = {
        "ok": dual["ok"], "seconds": dual["seconds"], "returncode": dual["returncode"]
    }
    qualification = {
        "selected_ac_mode": "endpoint_specific_sequential",
        "fallback_reason": reason,
    }
    return replace(
        task,
        y=task.low_cutoff["y"], z=task.low_cutoff["z"], k=task.low_cutoff["k"],
        cutoff_source="not_applicable_endpoint_specific", endpoint_status=status_meta,
        execution_mode="dual_cutoff_endpoint_fallback",
        gold1_ac_mode="endpoint_specific_sequential",
        ac_scheduler_qualification=qualification,
    )


def check_gold1(task: Task, timeout=600):
    if task.execution_mode == "dual_cutoff_endpoint_fallback":
        cmd = [GOLD1, task.H, task.X,
               task.high_cutoff["y"], task.high_cutoff["z"], task.high_cutoff["k"],
               task.low_cutoff["y"], task.low_cutoff["z"], task.low_cutoff["k"],
               THREADS, "--dual-cutoff"]
    else:
        cmd = [GOLD1, task.H, task.X, task.y, task.z, task.k, THREADS]
        if task.gold1_ac_mode == "sequential":
            cmd.append("--ac-sequential")
    rc, out, dt = run_cmd(cmd, timeout=timeout)
    ok = rc == 0 and re.search(rf"(?m)^interval_count={task.interval}\s*$", out)
    if task.execution_mode == "dual_cutoff_endpoint_fallback":
        ok = bool(ok and re.search(rf"(?m)^pi_H_endpoint={task.pi_H}\s*$", out)
                  and re.search(rf"(?m)^pi_X_endpoint={task.pi_X}\s*$", out))
    return {"ok": bool(ok), "seconds": dt, "output": out, "returncode": rc}


def primecount_one(n: int, expected: int, threads: int, timeout=600):
    rc, out, dt = run_cmd([PRIMECOUNT, n, "--gourdon", f"--threads={threads}"], timeout=timeout)
    return {"ok": rc == 0 and expected_in_output(out, expected), "seconds": dt,
            "output": out, "returncode": rc, "value": expected}


def get_fastprime():
    if not FP_BIN_FILE.exists():
        raise RuntimeError("fast-prime binary path missing; run ./setup_all.sh")
    p = Path(FP_BIN_FILE.read_text(encoding="utf-8").strip())
    if not p.exists():
        raise RuntimeError(f"fast-prime binary does not exist: {p}")
    return p

def fastprime_available() -> bool:
    try:
        p = get_fastprime()
        return p.exists()
    except Exception:
        return False


def fastprime_env(threads: int):
    return {"GOLD1_THREADS": str(threads), "POOL_MULT": "1"}


def fastprime_one(n: int, expected: int, requested_threads=THREADS, timeout=600):
    rc, out, dt = run_cmd([get_fastprime(), n], env=fastprime_env(requested_threads), timeout=timeout)
    return {"ok": rc == 0 and expected_in_output(out, expected), "seconds": dt,
            "output": out, "returncode": rc, "value": expected}


def pair_concurrent(task: Task, exe_kind: str, th_hi: int, th_lo: int, timeout=600):
    env_hi = os.environ.copy(); env_lo = os.environ.copy()
    if exe_kind == "primecount":
        c_hi = [str(PRIMECOUNT), str(task.H), "--gourdon", f"--threads={th_hi}"]
        c_lo = [str(PRIMECOUNT), str(task.X), "--gourdon", f"--threads={th_lo}"]
    elif exe_kind == "fastprime":
        fp = get_fastprime()
        c_hi = [str(fp), str(task.H)]; c_lo = [str(fp), str(task.X)]
        env_hi.update(fastprime_env(th_hi)); env_lo.update(fastprime_env(th_lo))
    else:
        raise ValueError(exe_kind)
    t0 = time.perf_counter()
    p1 = subprocess.Popen(c_hi, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_hi)
    p2 = subprocess.Popen(c_lo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env_lo)
    try:
        o1, _ = p1.communicate(timeout=timeout)
        remain = max(1, timeout - (time.perf_counter() - t0))
        o2, _ = p2.communicate(timeout=remain)
    except subprocess.TimeoutExpired:
        p1.kill(); p2.kill(); raise
    dt = time.perf_counter() - t0
    ok = (p1.returncode == 0 and p2.returncode == 0 and
          expected_in_output(o1, task.pi_H) and expected_in_output(o2, task.pi_X))
    return {"ok": ok, "seconds": dt, "high_output": o1, "low_output": o2,
            "high_rc": p1.returncode, "low_rc": p2.returncode}


def primecount_sequential(task: Task, timeout=600):
    a = primecount_one(task.H, task.pi_H, THREADS, timeout)
    b = primecount_one(task.X, task.pi_X, THREADS, timeout)
    return {"ok": a["ok"] and b["ok"], "seconds": a["seconds"] + b["seconds"],
            "high": a, "low": b}


def fastprime_sequential(task: Task, timeout=600):
    a = fastprime_one(task.H, task.pi_H, THREADS, timeout)
    b = fastprime_one(task.X, task.pi_X, THREADS, timeout)
    return {"ok": a["ok"] and b["ok"], "seconds": a["seconds"] + b["seconds"],
            "high": a, "low": b}


def find_primesieve():
    pointer = ROOT / "third_party" / "primesieve.binary"
    if pointer.exists():
        try:
            p = Path(pointer.read_text(encoding="utf-8").strip())
            if p.exists():
                return p
        except Exception:
            pass
    for name in ("primesieve.exe", "primesieve"):
        p = shutil.which(name)
        if p:
            return Path(p)
    return None


def primesieve_direct(task: Task, timeout=600):
    ps = find_primesieve()
    if not ps:
        return {"ok": False, "available": False, "seconds": None,
                "output": "primesieve CLI not found in PATH", "returncode": 127}
    candidates = [
        [ps, str(task.L), str(task.H), "--count", f"--threads={THREADS}"],
        [ps, str(task.L), str(task.H), "-c", f"-t{THREADS}"],
    ]
    last = None
    for cmd in candidates:
        rc, out, dt = run_cmd(cmd, timeout=timeout)
        last = {"ok": rc == 0 and expected_in_output(out, task.interval), "available": True,
                "seconds": dt, "output": out, "returncode": rc,
                "cmd": [str(x) for x in cmd]}
        if last["ok"]:
            return last
    return last


def validate_task(task: Task, include_primesieve=True, timeout=600):
    print("===== GENERATED REFERENCE =====")
    print(f"L={task.L}")
    print(f"H={task.H}")
    print(f"X={task.X}")
    print(f"pi_H={task.pi_H}")
    print(f"pi_X={task.pi_X}")
    print(f"expected_interval_count={task.interval}")
    print(f"gold1_execution_mode={task.execution_mode}")
    if task.execution_mode == "common_cutoff_delta":
        print(f"common_y={task.y} common_z={task.z} common_k={task.k} source={task.cutoff_source}")
    else:
        print(f"high_y={task.high_cutoff['y']} high_z={task.high_cutoff['z']} high_k={task.high_cutoff['k']}")
        print(f"low_y={task.low_cutoff['y']} low_z={task.low_cutoff['z']} low_k={task.low_cutoff['k']}")
    print(f"gold1_ac_mode={task.gold1_ac_mode}")
    if task.ac_scheduler_qualification.get("fallback_reason"):
        print(f"gold1_ac_fallback={task.ac_scheduler_qualification['fallback_reason']}")

    print("===== GOLD1 =====")
    g = check_gold1(task, timeout)
    print(f"gold1_ok={g['ok']} wall_seconds={g['seconds']:.6f}")
    if not g["ok"]:
        print(g["output"]); return 1

    print("===== PRIMECOUNT 8.7 =====")
    ph = primecount_one(task.H, task.pi_H, THREADS, timeout)
    pl = primecount_one(task.X, task.pi_X, THREADS, timeout)
    print(f"primecount_H_ok={ph['ok']} seconds={ph['seconds']:.6f}")
    print(f"primecount_X_ok={pl['ok']} seconds={pl['seconds']:.6f}")
    if not (ph["ok"] and pl["ok"]):
        return 2

    if fastprime_available():
        print("===== FAST-PRIME V8 ADAPTER (OPTIONAL) =====")
        fh = fastprime_one(task.H, task.pi_H, THREADS, timeout)
        fl = fastprime_one(task.X, task.pi_X, THREADS, timeout)
        print(f"fastprime_H_ok={fh['ok']} seconds={fh['seconds']:.6f}")
        print(f"fastprime_X_ok={fl['ok']} seconds={fl['seconds']:.6f}")
        if not (fh["ok"] and fl["ok"]):
            probe = ROOT / "results" / f"fastprime_probe_{task.L}_{task.H}.txt"
            probe.parent.mkdir(exist_ok=True)
            probe.write_text("HIGH:\n" + fh["output"] + "\nLOW:\n" + fl["output"], encoding="utf-8")
            print(f"Probe output saved: {probe}")
            return 3
    else:
        print("===== FAST-PRIME V8 ADAPTER (OPTIONAL) =====")
        print("fastprime_available=False (optional comparator skipped)")

    if include_primesieve:
        print("===== PRIMESIEVE DIRECT INTERVAL =====")
        ps = primesieve_direct(task, timeout)
        if not ps.get("available"):
            print("primesieve_available=False (optional competitor skipped)")
        else:
            print(f"primesieve_ok={ps['ok']} seconds={ps['seconds']:.6f}")
            if not ps["ok"]:
                print(ps["output"]); return 4
    print("ALL_VALIDATION_PASS")
    return 0


def calibrate_implementation(task: Task, kind: str, timeout: int, repeats: int,
                             tie_break_repeats: int, near_tie_margin: float,
                             plan: dict[str, int],
                             seq_mode: str, con_mode: str) -> tuple[str, dict[str, Any]]:
    """Measure both endpoint protocols repeatedly with alternating order."""
    sequential_samples: list[float] = []
    concurrent_samples: list[float] = []
    order_by_repeat: list[list[str]] = []

    def run_one(mode: str) -> dict[str, Any]:
        if mode == "sequential":
            if kind == "primecount":
                return primecount_sequential(task, timeout)
            if kind == "fastprime":
                return fastprime_sequential(task, timeout)
        elif mode == "concurrent":
            return pair_concurrent(task, kind, plan["concurrent_high"],
                                   plan["concurrent_low"], timeout)
        raise ValueError(f"unknown calibration implementation/mode: {kind}/{mode}")

    def measure_repeat(index: int) -> None:
        order = (["sequential", "concurrent"] if index % 2 == 0
                 else ["concurrent", "sequential"])
        order_by_repeat.append(order)
        for mode in order:
            result = run_one(mode)
            if not result["ok"]:
                raise RuntimeError(f"{kind} {mode} calibration failed exact validation")
            samples = sequential_samples if mode == "sequential" else concurrent_samples
            samples.append(result["seconds"])
            print(f"{kind} calibration_repeat={index + 1} mode={mode} "
                  f"seconds={result['seconds']:.6f}")

    for index in range(repeats):
        measure_repeat(index)

    _, initial = select_endpoint_protocol(
        sequential_samples, concurrent_samples, seq_mode, con_mode, near_tie_margin
    )
    extra_repeats = tie_break_repeats if initial["near_tie"] else 0
    if extra_repeats:
        print(f"{kind}_near_tie=True; adding {extra_repeats} tie-break repeat(s)")
        for index in range(repeats, repeats + extra_repeats):
            measure_repeat(index)

    selected, summary = select_endpoint_protocol(
        sequential_samples, concurrent_samples, seq_mode, con_mode, near_tie_margin
    )
    summary["base_repeats"] = repeats
    summary["tie_break_repeats_requested"] = tie_break_repeats
    summary["tie_break_repeats_performed"] = extra_repeats
    summary["total_repeats"] = repeats + extra_repeats
    summary["initial_near_tie"] = initial["near_tie"]
    summary["initial_sequential_median"] = initial["sequential_median"]
    summary["initial_concurrent_median"] = initial["concurrent_median"]
    summary["order_by_repeat"] = order_by_repeat
    print(f"{kind} {seq_mode}_median={summary['sequential_median']:.6f}s")
    print(f"{kind} {con_mode}_median={summary['concurrent_median']:.6f}s")
    print(f"{kind}_concurrent_relative_gain={summary['concurrent_relative_gain']:.6%}")
    print(f"{kind}_selected={selected}")
    return selected, summary


def calibrate(task: Task, timeout=600):
    print("===== ROBUST PROTOCOL CALIBRATION =====")
    plan = thread_plan()
    seq_mode, con_mode = endpoint_pair_modes()
    repeats, tie_break_repeats, near_tie_margin = calibration_policy()
    print(f"calibration_repeats={repeats}")
    print(f"tie_break_repeats={tie_break_repeats}")
    print(f"near_tie_margin={near_tie_margin:.6%}")

    pc_mode, pc_summary = calibrate_implementation(
        task, "primecount", timeout, repeats, tie_break_repeats,
        near_tie_margin, plan, seq_mode, con_mode
    )
    cal = {
        "thread_plan": plan,
        "policy": {
            "repeats": repeats,
            "tie_break_repeats": tie_break_repeats,
            "near_tie_margin": near_tie_margin,
            "order": "alternating_sequential_first_then_concurrent_first",
            "selection": "lower_final_median",
        },
        "primecount": pc_summary,
    }

    fp_mode = None
    if fastprime_available():
        fp_mode, fp_summary = calibrate_implementation(
            task, "fastprime", timeout, repeats, tie_break_repeats,
            near_tie_margin, plan, seq_mode, con_mode
        )
        cal["fastprime"] = fp_summary
    else:
        print("fastprime_selected=SKIPPED_OPTIONAL")
    return pc_mode, fp_mode, cal


def run_selected(task: Task, name: str, mode: str, timeout=600):
    plan = thread_plan()
    seq_mode, con_mode = endpoint_pair_modes()
    if name == "gold1": return check_gold1(task, timeout)
    if name == "primecount":
        if mode == con_mode:
            return pair_concurrent(task, "primecount", plan["concurrent_high"],
                                   plan["concurrent_low"], timeout)
        if mode == seq_mode:
            return primecount_sequential(task, timeout)
        raise ValueError(f"primecount mode does not match {THREADS}-thread budget: {mode}")
    if name == "fastprime":
        if mode == con_mode:
            return pair_concurrent(task, "fastprime", plan["concurrent_high"],
                                   plan["concurrent_low"], timeout)
        if mode == seq_mode:
            return fastprime_sequential(task, timeout)
        raise ValueError(f"fastprime mode does not match {THREADS}-thread budget: {mode}")
    if name == "primesieve": return primesieve_direct(task, timeout)
    raise ValueError(name)


def stats(xs: list[float]) -> dict[str, float]:
    mean = statistics.mean(xs)
    median = statistics.median(xs)
    sd = statistics.stdev(xs) if len(xs) > 1 else 0.0
    return {
        "mean": mean,
        "median": median,
        "min": min(xs),
        "max": max(xs),
        "stdev": sd,
        "cv": (sd / mean) if mean else 0.0,
    }


def command_version(cmd: list[str]) -> str:
    try:
        rc, out, _ = run_cmd(cmd, timeout=20)
        if rc == 0:
            return out.strip().splitlines()[0] if out.strip() else ""
    except Exception:
        pass
    return "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256_file(path: Path | None) -> str:
    if path is None or not path.exists() or not path.is_file():
        return "unavailable"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_tree_sha256(files: list[Path]) -> tuple[str, int]:
    # Hash path names + raw bytes so the fingerprint identifies an exact source snapshot.
    selected = sorted({x.resolve() for x in files if x.exists() and x.is_file()}, key=lambda x: x.as_posix())
    h = hashlib.sha256()
    h.update(b"GOLD1_CANONICAL_SOURCE_TREE_SHA256_V1\0")
    for path in selected:
        try:
            rel = path.relative_to(ROOT.resolve()).as_posix()
        except ValueError:
            rel = path.name
        rb = rel.encode("utf-8")
        data = path.read_bytes()
        h.update(len(rb).to_bytes(4, "big"))
        h.update(rb)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest(), len(selected)


def source_fingerprints() -> dict[str, Any]:
    gold_files = [ROOT / "gold1" / "apply_patch.py"]
    patch_dir = ROOT / "gold1" / "patch"
    if patch_dir.exists():
        gold_files.extend(x for x in patch_dir.rglob("*") if x.is_file())
    gold_hash, gold_count = canonical_tree_sha256(gold_files)

    harness_files = []
    for rel in ("tools", "platform"):
        d = ROOT / rel
        if d.exists():
            harness_files.extend(x for x in d.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
    for name in (
        "run_interval_bench.sh", "run_interval_matrix.sh", "run_crossover_bench.sh",
        "run_ranking_bench.sh",
        "validate_interval.sh", "validate_all.sh", "setup_all.sh", "setup_linux.sh",
        "setup_windows_ucrt64.sh", "patch_and_rebuild_fastprime.sh"
    ):
        harness_files.append(ROOT / name)
    for name in ("setup_and_build_linux.sh", "setup_and_build_ucrt64.sh"):
        harness_files.append(ROOT / "gold1" / name)
    harness_hash, harness_count = canonical_tree_sha256(harness_files)
    return {
        "gold1_source_sha256": gold_hash,
        "gold1_source_sha256_scope": "gold1/apply_patch.py + gold1/patch/**",
        "gold1_source_file_count": gold_count,
        "benchmark_harness_sha256": harness_hash,
        "benchmark_harness_sha256_scope": "tools/** + platform/** + setup/validation/runner entrypoints",
        "benchmark_harness_file_count": harness_count,
    }


def _powershell_hardware() -> dict[str, Any]:
    ps = shutil.which("powershell.exe") or shutil.which("powershell") or shutil.which("pwsh")
    if not ps:
        return {}
    script = r"$ErrorActionPreference='Stop'; $cpu=@(Get-CimInstance Win32_Processor); $cs=Get-CimInstance Win32_ComputerSystem; $os=Get-CimInstance Win32_OperatingSystem; [pscustomobject]@{ cpu_model=(($cpu | ForEach-Object { $_.Name.Trim() } | Sort-Object -Unique) -join ' | '); physical_core_count=[int](($cpu | Measure-Object -Property NumberOfCores -Sum).Sum); logical_cpu_count=[int](($cpu | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum); total_ram_bytes=[int64]$cs.TotalPhysicalMemory; os_caption=[string]$os.Caption; os_version=[string]$os.Version; os_build_number=[string]$os.BuildNumber } | ConvertTo-Json -Compress"
    try:
        p = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command", script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=30)
        if p.returncode == 0 and p.stdout.strip():
            for line in reversed(p.stdout.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    return json.loads(line)
    except Exception:
        pass
    return {}


def _unix_hardware() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        text = Path("/proc/cpuinfo").read_text(errors="replace")
        models = []
        pairs = set()
        physical = core = None
        for line in text.splitlines() + [""]:
            if not line.strip():
                if physical is not None and core is not None:
                    pairs.add((physical, core))
                physical = core = None
                continue
            if ":" not in line:
                continue
            k, v = [x.strip() for x in line.split(":", 1)]
            if k in ("model name", "Hardware") and v and v not in models:
                models.append(v)
            elif k == "physical id":
                physical = v
            elif k == "core id":
                core = v
        if models:
            out["cpu_model"] = " | ".join(models)
        if pairs:
            out["physical_core_count"] = len(pairs)
    except Exception:
        pass
    try:
        mem = Path("/proc/meminfo").read_text()
        m = re.search(r"(?m)^MemTotal:\s+(\d+)\s+kB", mem)
        if m:
            out["total_ram_bytes"] = int(m.group(1)) * 1024
    except Exception:
        pass
    try:
        vals = {}
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k] = v.strip().strip('"')
        out["os_caption"] = vals.get("PRETTY_NAME", platform.system())
        out["os_version"] = vals.get("VERSION_ID", platform.release())
        out["os_build_number"] = platform.release()
    except Exception:
        pass
    return out


def hardware_metadata() -> dict[str, Any]:
    hw = _powershell_hardware() if os.name == "nt" or "MINGW" in platform.system().upper() else {}
    if not hw:
        hw = _unix_hardware()
    logical = hw.get("logical_cpu_count") or os.cpu_count()
    ram_bytes = hw.get("total_ram_bytes")
    ram_gib = round(ram_bytes / (1024 ** 3), 3) if isinstance(ram_bytes, int) and ram_bytes > 0 else None
    return {
        "cpu_model": hw.get("cpu_model") or platform.processor() or "unknown",
        "physical_core_count": hw.get("physical_core_count") or "unknown",
        "logical_cpu_count": logical or "unknown",
        "total_ram_bytes": ram_bytes if ram_bytes is not None else "unknown",
        "total_ram_gib": ram_gib if ram_gib is not None else "unknown",
        "os_caption": hw.get("os_caption") or platform.system() or "unknown",
        "os_version": hw.get("os_version") or platform.version() or "unknown",
        "os_build_number": hw.get("os_build_number") or platform.release() or "unknown",
    }


def _read_text(path: Path, default: str = "unknown") -> str:
    try:
        t = path.read_text(encoding="utf-8").strip()
        return t if t else default
    except Exception:
        return default

def metadata() -> dict[str, Any]:
    td = ROOT / "third_party"
    commit = td / "fast-prime.commit"
    host = td / "fast-prime.rust-host"
    toolchain = td / "fast-prime.rust-toolchain"
    rustc_build = td / "fast-prime.rustc-version.txt"
    cargo_build = td / "fast-prime.cargo-version.txt"
    compiler_build = ROOT / "gold1" / "build-compiler.txt"
    primesieve_ver = td / "primesieve.version"
    vs_path = td / "visual-studio.installation-path"
    vs_ver = td / "visual-studio.installation-version"
    vs_gen = td / "visual-studio.cmake-generator"
    ps = find_primesieve()
    hw = hardware_metadata()
    try:
        fp = get_fastprime()
    except Exception:
        fp = None
    exact_rustc = _read_text(rustc_build)
    return {
        **hw,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "compiler": _read_text(compiler_build, command_version(["c++", "--version"])) .splitlines()[0],
        "primecount": command_version([str(PRIMECOUNT), "--version"]),
        "primesieve": command_version([str(ps), "--version"]) if ps else "unavailable",
        "primesieve_pinned_version": _read_text(primesieve_ver),
        "visual_studio_installation_path": _read_text(vs_path, "not-applicable" if os.name != "nt" and "MINGW" not in platform.system().upper() else "unknown"),
        "visual_studio_installation_version": _read_text(vs_ver, "not-applicable" if os.name != "nt" and "MINGW" not in platform.system().upper() else "unknown"),
        "visual_studio_cmake_generator": _read_text(vs_gen, "not-applicable" if os.name != "nt" and "MINGW" not in platform.system().upper() else "unknown"),
        "rustc": exact_rustc.splitlines()[0] if exact_rustc != "unknown" else "unknown",
        "ambient_rustc": command_version(["rustc", "--version"]),
        "fastprime_build_rustc_verbose": exact_rustc,
        "fastprime_build_cargo": _read_text(cargo_build),
        "fastprime_toolchain": _read_text(toolchain),
        "fastprime_commit": _read_text(commit),
        "fastprime_rust_host": _read_text(host),
        "fastprime_pool_mult": 1,
        "fastprime_thread_override": "GOLD1_THREADS",
        "fastprime_large_pages": "implementation default" if fp else "not-built-optional",
        "fastprime_available": bool(fp),
        "fastprime_status": "included" if fp else "optional-skipped",
        **source_fingerprints(),
        "gold1_binary_sha256": sha256_file(GOLD1),
        "primecount_binary_sha256": sha256_file(PRIMECOUNT),
        "fastprime_binary_sha256": sha256_file(fp),
        "primesieve_binary_sha256": sha256_file(ps),
    }


def write_unsupported(L: int, H: int, reason: str, started_utc: str | None = None) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    finished_utc = utc_now_iso()
    outdir = ROOT / "results"; outdir.mkdir(exist_ok=True)
    p = outdir / f"{stamp}_interval_{L}_{H}_unsupported.json"
    p.write_text(json.dumps({
        "schema_version": SCHEMA_VERSION,
        "utc": stamp,
        "benchmark_started_utc": started_utc or finished_utc,
        "benchmark_finished_utc": finished_utc,
        "task": {"L": L, "H": H, "X": L - 1, "width": H - L},
        "thread_budget": THREADS,
        "thread_plan": thread_plan(),
        "validation_status": "unsupported", "reason": reason,
        "build_metadata": metadata(),
    }, indent=2), encoding="utf-8")
    return p


def write_validation_failure(L: int, H: int, reason: str, task: Task | None = None,
                             started_utc: str | None = None) -> Path:
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    finished_utc = utc_now_iso()
    outdir = ROOT / "results"; outdir.mkdir(exist_ok=True)
    p = outdir / f"{stamp}_interval_{L}_{H}_validation_failed.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "utc": stamp,
        "benchmark_started_utc": started_utc or finished_utc,
        "benchmark_finished_utc": finished_utc,
        "task": {"L": L, "H": H, "X": L - 1, "width": H - L},
        "thread_budget": THREADS,
        "thread_plan": thread_plan(),
        "validation_status": "failed",
        "reason": reason,
        "build_metadata": metadata(),
    }
    if task is not None:
        payload["task"].update({
            "pi_H": task.pi_H, "pi_X": task.pi_X,
            "interval_count": task.interval,
        })
        payload["gold1_execution_mode"] = task.execution_mode
        payload["common_gourdon"] = ({
            "y": task.y, "z": task.z, "k": task.k,
            "source": task.cutoff_source, "endpoint_status": task.endpoint_status,
        } if task.execution_mode == "common_cutoff_delta" else None)
        payload["endpoint_gourdon"] = {"high": task.high_cutoff, "low": task.low_cutoff}
        payload["cutoff_selection"] = task.endpoint_status
        payload["gold1_ac_mode"] = task.gold1_ac_mode
        payload["gold1_ac_scheduler_qualification"] = task.ac_scheduler_qualification
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return p


def benchmark_task(L: int, H: int, runs: int, timeout=600) -> Path:
    benchmark_started_utc = utc_now_iso()
    try:
        task = prepare_task(L, H, timeout=max(timeout, 1200))
    except UnsupportedInterval as e:
        p = write_unsupported(L, H, str(e), benchmark_started_utc)
        print(f"UNSUPPORTED: {e}")
        print(f"RESULT_JSON={p}")
        return p

    validation_rc = validate_task(task, include_primesieve=True, timeout=timeout)
    if validation_rc == 1 and task.execution_mode == "common_cutoff_delta" and task.gold1_ac_mode == "balanced":
        hi_threads = THREADS // 2
        lo_threads = THREADS - hi_threads
        q = dict(task.ac_scheduler_qualification)
        q["selected_ac_mode"] = "sequential"
        q["fallback_reason"] = (
            f"balanced {hi_threads}+{lo_threads} AC passed qualification but failed the independent "
            f"pre-benchmark validation run; falling back to sequential {THREADS}+{THREADS} AC"
        )
        task = replace(task, gold1_ac_mode="sequential", ac_scheduler_qualification=q)
        print("RETRY: Gold1 common-cutoff path with sequential AC fallback")
        validation_rc = validate_task(task, include_primesieve=True, timeout=timeout)
    if validation_rc == 1 and task.execution_mode == "common_cutoff_delta":
        dual_task = switch_to_dual_fallback(
            task, timeout=max(timeout, 1200),
            reason="common-cutoff path failed independent pre-benchmark validation; using exact endpoint-specific fallback",
        )
        if dual_task is not None:
            task = dual_task
            print("RETRY: Gold1 with endpoint-specific Gourdon fallback")
            validation_rc = validate_task(task, include_primesieve=True, timeout=timeout)
    if validation_rc != 0:
        p = write_validation_failure(L, H,
            f"pre-benchmark validation failed with code {validation_rc}", task, benchmark_started_utc)
        print(f"VALIDATION_FAILED: code={validation_rc}")
        print(f"RESULT_JSON={p}")
        return p
    pc_mode, fp_mode, cal = calibrate(task, timeout)
    hi_threads = THREADS // 2
    lo_threads = THREADS - hi_threads
    if task.execution_mode == "dual_cutoff_endpoint_fallback":
        gold1_mode = f"dual_cutoff_endpoint_fallback_sequential_{THREADS}+{THREADS}"
    else:
        gold1_mode = (f"direct_interval_balanced_{hi_threads}+{lo_threads}"
                      if task.gold1_ac_mode == "balanced"
                      else f"direct_interval_sequential_{THREADS}+{THREADS}")
    modes = {"gold1": gold1_mode, "primecount": pc_mode}
    if fp_mode:
        modes["fastprime"] = fp_mode
    ps0 = primesieve_direct(task, timeout)
    if ps0.get("available") and ps0.get("ok"):
        modes["primesieve"] = f"direct_interval_{THREADS}"

    print("===== WARMUP =====")
    for name in modes:
        r = run_selected(task, name, modes[name], timeout)
        if not r["ok"]:
            raise RuntimeError(f"{name} warmup failed")
        print(f"{name} warmup={r['seconds']:.6f}s")

    base_orders = [
        ["gold1", "primecount", "fastprime", "primesieve"],
        ["fastprime", "primesieve", "gold1", "primecount"],
        ["primecount", "gold1", "primesieve", "fastprime"],
        ["primesieve", "fastprime", "primecount", "gold1"],
    ]
    vals = {k: [] for k in modes}
    raw = []
    print("===== MEASURED RUNS =====")
    for i in range(runs):
        order = [n for n in base_orders[i % len(base_orders)] if n in modes]
        print(f"ROUND {i+1} order={','.join(order)}")
        for name in order:
            r = run_selected(task, name, modes[name], timeout)
            if not r["ok"]:
                raise RuntimeError(f"{name} failed exact validation in measured run")
            vals[name].append(r["seconds"])
            raw.append({"round": i + 1, "name": name, "seconds": r["seconds"], "mode": modes[name]})
            print(f"  {name}: {r['seconds']:.6f}s ({modes[name]})")

    summary = {k: stats(v) for k, v in vals.items()}
    med = {k: summary[k]["median"] for k in summary}
    ranking = sorted(med, key=med.get)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    benchmark_finished_utc = utc_now_iso()
    result = {
        "schema_version": SCHEMA_VERSION,
        "utc": stamp,
        "benchmark_started_utc": benchmark_started_utc,
        "benchmark_finished_utc": benchmark_finished_utc,
        "task": {"L": task.L, "H": task.H, "X": task.X, "width": task.H - task.L,
                 "relative_width": (task.H - task.L) / task.H,
                 "pi_H": task.pi_H, "pi_X": task.pi_X, "interval_count": task.interval},
        "runs": runs,
        "thread_budget": THREADS,
        "thread_plan": thread_plan(),
        "protocol_calibration_policy": cal["policy"],
        "gold1_execution_mode": task.execution_mode,
        "common_gourdon": ({"y": task.y, "z": task.z, "k": task.k,
                           "source": task.cutoff_source, "endpoint_status": task.endpoint_status}
                           if task.execution_mode == "common_cutoff_delta" else None),
        "endpoint_gourdon": {"high": task.high_cutoff, "low": task.low_cutoff},
        "cutoff_selection": task.endpoint_status,
        "gold1_ac_mode": task.gold1_ac_mode,
        "gold1_ac_scheduler_qualification": task.ac_scheduler_qualification,
        "modes": modes,
        "calibration": cal,
        "times": vals,
        "statistics": summary,
        "raw": raw,
        "ranking": ranking,
        "validation_status": "pass",
        "build_metadata": metadata(),
    }
    outdir = ROOT / "results"; outdir.mkdir(exist_ok=True)
    base = f"{stamp}_interval_{task.L}_{task.H}"
    jpath = outdir / f"{base}.json"
    tpath = outdir / f"{base}.txt"
    jpath.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "Gold1 generalized exact interval prime-count ranking benchmark v2.3.6 - robust calibration + crossover suite",
        f"UTC={stamp}",
        f"benchmark_started_utc={benchmark_started_utc}",
        f"benchmark_finished_utc={benchmark_finished_utc}",
        f"L={task.L}", f"H={task.H}", f"X={task.X}",
        f"width={task.H-task.L}", f"relative_width={(task.H-task.L)/task.H:.12e}",
        f"pi_H={task.pi_H}", f"pi_X={task.pi_X}", f"expected_interval_count={task.interval}",
        f"thread_budget={THREADS}",
        f"protocol_calibration_repeats={cal['policy']['repeats']}",
        f"protocol_tie_break_repeats={cal['policy']['tie_break_repeats']}",
        f"protocol_near_tie_margin={cal['policy']['near_tie_margin']:.6%}",
        f"gold1_execution_mode={task.execution_mode}",
        (f"common_y={task.y}" if task.execution_mode == "common_cutoff_delta" else "common_y=not_applicable"),
        (f"common_z={task.z}" if task.execution_mode == "common_cutoff_delta" else "common_z=not_applicable"),
        (f"common_k={task.k}" if task.execution_mode == "common_cutoff_delta" else "common_k=not_applicable"),
        f"common_cutoff_source={task.cutoff_source}",
        f"endpoint_high_y={task.high_cutoff['y']} endpoint_high_z={task.high_cutoff['z']} endpoint_high_k={task.high_cutoff['k']}",
        f"endpoint_low_y={task.low_cutoff['y']} endpoint_low_z={task.low_cutoff['z']} endpoint_low_k={task.low_cutoff['k']}",
        f"gold1_ac_mode={task.gold1_ac_mode}",
        f"gold1_ac_qualification={json.dumps(task.ac_scheduler_qualification, separators=(',', ':'))}", "",
        "===== SELECTED PROTOCOLS =====",
    ]
    lines += [f"{k}_mode={v}" for k, v in modes.items()]
    lines += ["", "===== RUNS / STATISTICS ====="]
    for k in modes:
        s = summary[k]
        lines.append(f"{k}_runs=" + ",".join(f"{x:.6f}" for x in vals[k]))
        lines.append(f"{k}_mean_seconds={s['mean']:.6f}")
        lines.append(f"{k}_median_seconds={s['median']:.6f}")
        lines.append(f"{k}_min_seconds={s['min']:.6f}")
        lines.append(f"{k}_max_seconds={s['max']:.6f}")
        lines.append(f"{k}_stdev_seconds={s['stdev']:.6f}")
        lines.append(f"{k}_cv={s['cv']:.6f}")
    lines += ["", "===== RANKING ====="]
    for i, k in enumerate(ranking, 1):
        lines.append(f"{i}. {k} {med[k]:.6f}s")
    lines.append(f"WINNER={ranking[0]}")
    for other in ranking[1:]:
        lines.append(f"{ranking[0]}_vs_{other}_speedup={med[other]/med[ranking[0]]:.6f}x")
        lines.append(f"{ranking[0]}_vs_{other}_saved_seconds={med[other]-med[ranking[0]]:.6f}")
    lines += ["", "===== BUILD METADATA ====="]
    for k, v in result["build_metadata"].items():
        lines.append(f"{k}={v}")
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n" + "\n".join(lines[-(10 + 2 * max(0, len(ranking)-1)):]))
    print(f"Saved: {tpath}")
    print(f"Saved: {jpath}")
    print(f"RESULT_JSON={jpath}")
    return jpath


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="mode", required=True)
    for mode in ("validate", "benchmark"):
        p = sp.add_parser(mode)
        p.add_argument("L", type=int)
        p.add_argument("H", type=int)
        p.add_argument("--timeout", type=int, default=int(os.environ.get("RANK_TIMEOUT", "600")))
        if mode == "benchmark":
            p.add_argument("--runs", type=int, default=int(os.environ.get("RANK_RUNS", "5")))
    a = ap.parse_args()
    if a.mode == "validate":
        try:
            task = prepare_task(a.L, a.H, timeout=max(a.timeout, 1200))
        except UnsupportedInterval as e:
            print(f"UNSUPPORTED: {e}")
            raise SystemExit(3)
        rc = validate_task(task, True, a.timeout)
        if rc == 1 and task.execution_mode == "common_cutoff_delta" and task.gold1_ac_mode == "balanced":
            q = dict(task.ac_scheduler_qualification)
            q["selected_ac_mode"] = "sequential"
            q["fallback_reason"] = "balanced AC failed validation; retrying common-cutoff path sequentially"
            task = replace(task, gold1_ac_mode="sequential", ac_scheduler_qualification=q)
            print("RETRY: common-cutoff sequential AC")
            rc = validate_task(task, True, a.timeout)
        if rc == 1 and task.execution_mode == "common_cutoff_delta":
            dual_task = switch_to_dual_fallback(task, max(a.timeout, 1200))
            if dual_task is not None:
                task = dual_task
                print("RETRY: endpoint-specific Gourdon fallback")
                rc = validate_task(task, True, a.timeout)
        raise SystemExit(rc)
    benchmark_task(a.L, a.H, a.runs, a.timeout)


if __name__ == "__main__":
    main()
