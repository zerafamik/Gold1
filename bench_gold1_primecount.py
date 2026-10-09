#!/usr/bin/env python3
"""Gold1 / primecount only: higher-range benchmarks using an existing v2.3.6 build.

Put this file beside run_crossover_bench.sh. No rebuild or third-party download.
Example: python -u bench_gold1_primecount.py --bases 2e18 4e18 --width 1e12
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path


# These defaults are also available as command-line options.
DEFAULT_BASES = ("2e18", "4e18")
DEFAULT_WIDTH = "1e12"
DEFAULT_THREADS = 4
DEFAULT_RUNS = 5
SCHEMA = "2.3.7-gold1-primecount-only"
INT64_MAX = 9_223_372_036_854_775_807
NAMES = ("gold1", "primecount")
SELECTION = {
    "gold1": "included", "primecount": "included",
    "primesieve": "excluded_by_selection", "fastprime": "excluded_by_selection",
}
VALIDATION_SCOPE = (
    "Gold1 verification plus exact primecount endpoint checks. "
    "Gold1 reuses primecount components; no primesieve or third-algorithm check."
)


class ValidationFailure(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def announce(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def integer(text):
    """Accept exact decimal/scientific integers without floating-point rounding."""
    try:
        value = Decimal(text)
        if not value.is_finite() or value < 0 or value > INT64_MAX:
            raise ValueError()
        if value != value.to_integral_value():
            raise ValueError()
        return int(value)
    except (InvalidOperation, ValueError, OverflowError):
        raise argparse.ArgumentTypeError(
            f"expected a nonnegative integer at most {INT64_MAX}; got {text!r}"
        ) from None


def positive_integer(text):
    result = integer(text)
    if result < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def atomic_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_harness(package, threads):
    path = package / "tools" / "interval_bench.py"
    if not path.is_file():
        raise ValueError("Put this runner in the built Gold1 package folder, or pass --package PATH.")
    os.environ["GOLD1_BENCH_THREADS"] = str(threads)
    spec = importlib.util.spec_from_file_location("_gold1_two_way_base_harness", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # Required by dataclasses during import.
    spec.loader.exec_module(module)
    if module.SCHEMA_VERSION != "2.3.6-robust-calibration-crossover":
        raise ValueError("This add-on targets the v2.3.6 benchmark package. Use that built folder.")
    module.THREADS = threads
    for binary in (module.GOLD1, module.PRIMECOUNT):
        if not binary.is_file():
            raise ValueError(f"Existing executable missing: {binary}. Select your already-built package.")
    return module


def exact_output_count(output):
    """The ordinary primecount CLI must contain exactly one standalone integer."""
    numbers = []
    for line in output.splitlines():
        token = line.strip().replace(",", "").replace("_", "")
        if re.fullmatch(r"[+]?[0-9]+", token):
            numbers.append(int(token))
    if len(numbers) != 1:
        raise ValueError(f"expected one standalone count, found {len(numbers)}")
    return numbers[0]


def check_count(returncode, output, expected):
    try:
        value = exact_output_count(output)
    except ValueError as error:
        return {"ok": False, "value": None, "expected": expected, "parse_error": str(error)}
    return {"ok": returncode == 0 and value == expected, "value": value, "expected": expected}


def primecount_one(core, number, expected, threads, timeout):
    command = [str(core.PRIMECOUNT), str(number), "--gourdon", f"--threads={threads}"]
    rc, output, seconds = core.run_cmd(command, timeout=timeout)
    return {"command": command, "returncode": rc, "output": output, "seconds": seconds,
            **check_count(rc, output, expected)}


def primecount_pair(core, task, mode, threads, timeout):
    if mode == "sequential":
        high = primecount_one(core, task.H, task.pi_H, threads, timeout)
        low = primecount_one(core, task.X, task.pi_X, threads, timeout)
        return {"ok": high["ok"] and low["ok"], "seconds": high["seconds"] + low["seconds"],
                "high": high, "low": low}
    if mode != "concurrent":
        raise ValueError(f"unknown endpoint mode: {mode}")
    split = core.thread_plan(threads)
    commands = [
        [str(core.PRIMECOUNT), str(task.H), "--gourdon", f"--threads={split['concurrent_high']}"],
        [str(core.PRIMECOUNT), str(task.X), "--gourdon", f"--threads={split['concurrent_low']}"],
    ]
    processes, outputs = [], []
    start = time.perf_counter()
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, stdout=subprocess.PIPE,
                                               stderr=subprocess.STDOUT, text=True))
        for process in processes:
            remaining = timeout - (time.perf_counter() - start)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(process.args, timeout)
            output, _ = process.communicate(timeout=remaining)
            outputs.append(output)
        seconds = time.perf_counter() - start
    finally:
        # Covers timeout, a failed second launch, and Ctrl+C. No orphan pair.
        for process in processes:
            if process.poll() is None:
                process.kill()
        for process in processes:
            process.communicate()
    endpoints = []
    for process, command, output, expected in zip(
            processes, commands, outputs, (task.pi_H, task.pi_X)):
        endpoints.append({"command": command, "returncode": process.returncode, "output": output,
                          **check_count(process.returncode, output, expected)})
    return {"ok": all(e["ok"] for e in endpoints), "seconds": seconds,
            "high": endpoints[0], "low": endpoints[1]}


def require_ok(record, stage):
    if not record.get("ok"):
        raise ValidationFailure(f"{stage}: exact output validation failed; inspect the saved JSON.")
    seconds = record.get("seconds")
    if seconds is not None and (not math.isfinite(seconds) or seconds <= 0):
        raise ValidationFailure(f"{stage}: invalid duration {seconds}")


def snapshot_task(task):
    value = asdict(task)
    value.update({"width": task.H - task.L, "interval_count": task.interval})
    return value


def prepare_validated(core, low, high, args, data, save):
    announce("Preparing endpoint references, cutoffs and Gold1 qualification; this can take several minutes.")
    task = core.prepare_task(low, high, timeout=max(1200, args.timeout))
    data["task"] = snapshot_task(task)
    save()
    announce("Checking Gold1 against the prepared reference count.")
    data["validation_attempts"] = []

    def probe(current):
        result = core.check_gold1(current, args.timeout)
        data["validation_attempts"].append({"execution_mode": current.execution_mode,
                                             "ac_mode": current.gold1_ac_mode, "result": result})
        data["task"] = snapshot_task(current)
        save()
        return result

    checked = probe(task)
    if not checked["ok"] and task.execution_mode == "common_cutoff_delta" and task.gold1_ac_mode == "balanced":
        qualification = dict(task.ac_scheduler_qualification)
        qualification.update({"selected_ac_mode": "sequential",
                              "fallback_reason": "balanced AC failed pre-benchmark exact validation"})
        task = replace(task, gold1_ac_mode="sequential", ac_scheduler_qualification=qualification)
        announce("Retrying Gold1 with sequential endpoint AC.")
        checked = probe(task)
    if not checked["ok"] and task.execution_mode == "common_cutoff_delta":
        announce("Checking the endpoint-specific Gold1 fallback.")
        fallback = core.switch_to_dual_fallback(
            task, max(1200, args.timeout), reason="common-cutoff pre-benchmark validation failed")
        if fallback is not None:
            task = fallback
            checked = probe(task)
    require_ok(checked, "Gold1 pre-benchmark validation")
    announce("Checking both primecount endpoints with exact numeric parsing.")
    pc = primecount_pair(core, task, "sequential", args.threads, args.timeout)
    data["primecount_validation"] = pc
    save()
    require_ok(pc, "primecount pre-benchmark validation")
    return task


def calibrate(core, task, args, data, save):
    sequential, concurrent = [], []
    cal = {"samples": [], "policy": {"repeats": args.calibration_repeats,
           "tie_break_repeats": args.tie_break_repeats, "near_tie_margin": args.near_tie,
           "order": "alternating", "selection": "lower_final_median"}}
    data["calibration"] = cal
    seq_label, con_label = core.endpoint_pair_modes(args.threads)

    def repeat(index):
        order = ("sequential", "concurrent") if index % 2 == 0 else ("concurrent", "sequential")
        for mode in order:
            announce(f"Calibration {index + 1}: primecount {mode}.")
            record = primecount_pair(core, task, mode, args.threads, args.timeout)
            cal["samples"].append({"repeat": index + 1, "mode": mode, "result": record})
            save()
            require_ok(record, f"primecount {mode} calibration")
            (sequential if mode == "sequential" else concurrent).append(record["seconds"])

    for index in range(args.calibration_repeats):
        repeat(index)
    _, initial = core.select_endpoint_protocol(sequential, concurrent, seq_label, con_label, args.near_tie)
    extra = args.tie_break_repeats if initial["near_tie"] else 0
    if extra:
        announce(f"Calibration near-tie: adding {extra} sample(s) per mode.")
    for index in range(args.calibration_repeats, args.calibration_repeats + extra):
        repeat(index)
    selected, summary = core.select_endpoint_protocol(sequential, concurrent, seq_label, con_label, args.near_tie)
    summary.update({"base_repeats": args.calibration_repeats, "total_repeats": len(sequential),
                    "initial_near_tie": initial["near_tie"], "tie_break_repeats_performed": extra})
    cal["primecount"] = summary
    save()
    announce(f"Selected primecount protocol: {selected}.")
    return "concurrent" if selected == con_label else "sequential", selected


def build_metadata(core):
    """Collect provenance without discovering or invoking either excluded comparator."""
    source = core.source_fingerprints()
    runner_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    base_hash = source["benchmark_harness_sha256"]
    combined = hashlib.sha256((base_hash + "\n" + runner_hash + "\n").encode("ascii")).hexdigest()
    compiler_file = core.ROOT / "gold1" / "build-compiler.txt"
    compiler = compiler_file.read_text(encoding="utf-8").strip() if compiler_file.exists() else "unknown"
    return {**core.hardware_metadata(), **source,
            "base_harness_schema": core.SCHEMA_VERSION,
            "base_benchmark_harness_sha256": base_hash,
            "benchmark_harness_sha256": combined,
            "benchmark_harness_sha256_scope": "SHA256(base tree hash + LF + two-way runner hash + LF)",
            "two_way_runner_sha256": runner_hash,
            "gold1_binary_sha256": core.sha256_file(core.GOLD1),
            "primecount_binary_sha256": core.sha256_file(core.PRIMECOUNT),
            "primecount": core.command_version([str(core.PRIMECOUNT), "--version"]),
            "compiler": compiler, "python": platform.python_version(),
            "platform": platform.platform(), "machine": platform.machine(),
            "primesieve_status": "excluded_by_selection", "fastprime_status": "excluded_by_selection"}


def run_case(core, low, high, args, case_index, path, metadata):
    started = time.perf_counter()
    data = {"schema_version": SCHEMA, "benchmark_started_utc": utc_now(),
            "task": {"L": low, "H": high, "X": low - 1, "width": high - low},
            "runs": args.runs, "thread_budget": args.threads, "thread_plan": core.thread_plan(args.threads),
            "comparators": dict(SELECTION), "validation_scope": VALIDATION_SCOPE,
            "validation_status": "running", "stage": "prepare", "build_metadata": metadata,
            "settings": {"timeout_seconds": args.timeout, "preparation_timeout_seconds": max(1200, args.timeout),
                         "ac_qualify_repeats": args.qualify_repeats,
                         "common_verify_attempts": args.common_verify_attempts},
            "times": {name: [] for name in NAMES}, "raw": [], "statistics": {}, "ranking": []}

    def save():
        data["updated_utc"] = utc_now()
        data["elapsed_seconds"] = time.perf_counter() - started
        atomic_json(path, data)

    try:
        save()
        task = prepare_validated(core, low, high, args, data, save)
        data["gold1_execution_mode"] = task.execution_mode
        data["gold1_ac_mode"] = task.gold1_ac_mode
        data["stage"] = "calibration"
        save()
        pc_mode, pc_label = calibrate(core, task, args, data, save)
        plan = core.thread_plan(args.threads)
        gold_label = (f"direct_interval_balanced_{plan['concurrent_high']}+{plan['concurrent_low']}"
                      if task.gold1_ac_mode == "balanced" else f"{task.execution_mode}_sequential_{args.threads}+{args.threads}")
        data["modes"] = {"gold1": gold_label, "primecount": pc_label}

        def measure(name):
            if name == "gold1":
                return core.check_gold1(task, args.timeout)
            return primecount_pair(core, task, pc_mode, args.threads, args.timeout)

        data["stage"] = "warmup"
        data["warmups"] = {}
        for name in NAMES:
            announce(f"Warmup: {name}.")
            record = measure(name)
            data["warmups"][name] = record
            save()
            require_ok(record, f"{name} warmup")

        data["stage"] = "measured_runs"
        for round_index in range(args.runs):
            # Alternate first place, including which implementation starts each case.
            order = NAMES if (round_index + case_index) % 2 == 0 else tuple(reversed(NAMES))
            for name in order:
                announce(f"Round {round_index + 1}/{args.runs}: {name}.")
                record = measure(name)
                entry = {"round": round_index + 1, "name": name, "mode": data["modes"][name],
                         "seconds": record["seconds"], "result": record}
                data["raw"].append(entry)  # Keep failed stdout too; never rank a failed run.
                save()
                require_ok(record, f"{name} measured round {round_index + 1}")
                data["times"][name].append(record["seconds"])
                save()
                announce(f"  {name}: {record['seconds']:.6f} s; exact check passed.")
        data["statistics"] = {name: core.stats(data["times"][name]) for name in NAMES}
        data["ranking"] = sorted(NAMES, key=lambda name: data["statistics"][name]["median"])
        data["validation_status"] = "pass"
        data["stage"] = "complete"
    except KeyboardInterrupt:
        data.update({"validation_status": "interrupted", "reason": "Interrupted by user; completed records retained."})
    except core.UnsupportedInterval as error:
        data.update({"validation_status": "unsupported", "reason": str(error)})
    except Exception as error:
        data.update({"validation_status": "failed", "reason": f"{type(error).__name__}: {error}"})
    finally:
        data["benchmark_finished_utc"] = utc_now()
        save()
    return data


def row_for(data, case_file):
    task, stats = data["task"], data["statistics"]
    gold = stats.get("gold1", {}).get("median")
    pc = stats.get("primecount", {}).get("median")
    return {"L": task["L"], "H": task["H"], "width": task["width"],
            "expected_count": task.get("interval_count"), "thread budget": data["thread_budget"],
            "Gold1 median": gold, "primecount median": pc,
            "Gold1/primecount speedup": pc / gold if gold and pc else None,
            "Gold1 time saved percent": 100 * (1 - gold / pc) if gold and pc else None,
            "winner": data["ranking"][0] if data["ranking"] else None,
            "validation_status": data["validation_status"], "stage": data["stage"],
            "Gold1 execution mode": data.get("gold1_execution_mode"),
            "Gold1 completed runs": len(data["times"]["gold1"]),
            "primecount completed runs": len(data["times"]["primecount"]),
            "result_json": str(case_file), "reason": data.get("reason", "")}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent,
                        help="existing built v2.3.6 folder; default: this script's folder")
    parser.add_argument("--bases", type=integer, nargs="+", default=[integer(s) for s in DEFAULT_BASES])
    parser.add_argument("--width", type=positive_integer, default=integer(DEFAULT_WIDTH))
    parser.add_argument("--threads", type=positive_integer, default=DEFAULT_THREADS)
    parser.add_argument("--runs", type=positive_integer, default=DEFAULT_RUNS)
    parser.add_argument("--timeout", type=positive_integer, default=3600,
                        help="seconds per subprocess / concurrent pair (default 3600)")
    parser.add_argument("--qualify-repeats", type=positive_integer, default=5)
    parser.add_argument("--common-verify-attempts", type=positive_integer, default=3)
    parser.add_argument("--calibration-repeats", type=positive_integer, default=3)
    parser.add_argument("--tie-break-repeats", type=integer, default=2)
    parser.add_argument("--near-tie", type=float, default=0.02)
    parser.add_argument("--dry-run", action="store_true", help="show exact cases without importing a harness or launching binaries")
    args = parser.parse_args(argv)
    if args.threads < 2 or args.qualify_repeats < 2 or args.common_verify_attempts < 2:
        parser.error("threads, qualify-repeats and common-verify-attempts must each be at least 2")
    if not math.isfinite(args.near_tie) or not 0 <= args.near_tie < 1:
        parser.error("near-tie must be in [0, 1)")
    if len(set(args.bases)) != len(args.bases):
        parser.error("bases must not contain duplicates")
    for low in args.bases:
        if low < 2 or low + args.width > INT64_MAX:
            parser.error(f"require 2 <= L <= H <= {INT64_MAX}; L={low}, H={low + args.width}")
    args.package = args.package.resolve()
    return args


def main(argv=None):
    args = parse_args(argv)
    announce(f"Gold1 and primecount only | {args.threads} workers | {args.runs} measured rounds per case.")
    print(f"Width = {args.width:,}; endpoints must fit signed int64.\n{VALIDATION_SCOPE}", flush=True)
    for index, low in enumerate(args.bases, 1):
        print(f"CASE {index}: L={low}  H={low + args.width}  width={args.width}", flush=True)
    if args.dry_run:
        return 0
    try:
        core = load_harness(args.package, args.threads)
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    os.environ["GOLD1_AC_QUALIFY_REPEATS"] = str(args.qualify_repeats)
    os.environ["GOLD1_COMMON_VERIFY_ATTEMPTS"] = str(args.common_verify_attempts)
    metadata = build_metadata(core)
    output_dir = args.package / "results"
    output_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    aggregate_path = output_dir / f"{stamp}_two_way_matrix.json"
    csv_path = aggregate_path.with_suffix(".csv")
    aggregate = {"schema_version": SCHEMA, "suite": "higher_endpoint_two_way", "utc": stamp,
                 "runs": args.runs, "thread_budget": args.threads,
                 "comparators": dict(SELECTION), "validation_scope": VALIDATION_SCOPE,
                 "planned_cases": [{"L": low, "H": low + args.width} for low in args.bases],
                 "build_metadata": metadata, "status": "running", "rows": [], "details": []}
    atomic_json(aggregate_path, aggregate)
    announce(f"Results: {aggregate_path}")
    exit_code = 0
    for index, low in enumerate(args.bases):
        case_path = output_dir / f"{stamp}_two_way_case{index + 1:02d}.json"
        announce(f"Starting case {index + 1}/{len(args.bases)}. Checkpoint: {case_path.name}")
        data = run_case(core, low, low + args.width, args, index, case_path, metadata)
        row = row_for(data, case_path)
        aggregate["rows"].append(row)
        aggregate["details"].append({"label": f"case_{index + 1}", "result_json": str(case_path), "result": data})
        atomic_json(aggregate_path, aggregate)
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerows(aggregate["rows"])
        if data["validation_status"] != "pass":
            exit_code = 130 if data["validation_status"] == "interrupted" else 1
            aggregate["status"] = "stopped"
            announce(f"STOPPED: {data.get('reason')}; saved completed records. Later cases were not started.")
            break
        announce(f"PASS: Gold1 median {row['Gold1 median']:.6f} s | primecount {row['primecount median']:.6f} s | "
                 f"speedup {row['Gold1/primecount speedup']:.3f}x.")
    if not exit_code:
        aggregate["status"] = "complete"
    aggregate["finished_utc"] = utc_now()
    atomic_json(aggregate_path, aggregate)
    announce(f"Saved aggregate JSON: {aggregate_path}")
    announce(f"Saved aggregate CSV: {csv_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
