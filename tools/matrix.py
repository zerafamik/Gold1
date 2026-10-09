#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
from __future__ import annotations
import csv, json, os, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "tools" / "interval_bench.py"
SCHEMA_VERSION = "2.3.6-robust-calibration-crossover"

MATRIX = [
    # Fixed scale 10^18, varying width.
    (10**18, 10**18 + 10**8, "width_1e8_at_1e18"),
    (10**18, 10**18 + 10**9, "width_1e9_at_1e18"),
    (10**18, 10**18 + 10**10, "width_1e10_at_1e18"),
    (10**18, 10**18 + 10**11, "width_1e11_at_1e18"),
    (10**18, 10**18 + 10**12, "width_1e12_at_1e18"),
    # Fixed width 10^11, varying location.
    (10**14, 10**14 + 10**11, "scale_1e14_width_1e11"),
    (10**15, 10**15 + 10**11, "scale_1e15_width_1e11"),
    (10**16, 10**16 + 10**11, "scale_1e16_width_1e11"),
    (10**17, 10**17 + 10**11, "scale_1e17_width_1e11"),
    (10**18, 10**18 + 10**11, "scale_1e18_width_1e11"),
]


def med(d, k):
    try: return d["statistics"][k]["median"]
    except Exception: return None


def ratio(a, b):
    return (b / a) if a and b else None


def benchmark_command(L: int, H: int, runs: int) -> list[str]:
    """Return a cross-platform child command using this Python interpreter."""
    return [sys.executable, str(BENCHMARK), "benchmark", str(L), str(H),
            "--runs", str(runs)]


def preflight():
    gold1 = ROOT / "gold1" / "build" / "gold1-interval.exe"
    if not gold1.exists():
        gold1 = ROOT / "gold1" / "build" / "gold1-interval"
    primecount = ROOT / "gold1" / "build" / "primecount.exe"
    if not primecount.exists():
        primecount = ROOT / "gold1" / "build" / "primecount"
    missing=[]
    if not gold1.exists(): missing.append(str(gold1))
    if not primecount.exists(): missing.append(str(primecount))
    if missing:
        raise SystemExit("ERROR: setup incomplete; run ./setup_all.sh before the matrix. Missing: " + ", ".join(missing))

def main(cases=None, suite_name="interval_matrix"):
    preflight()
    matrix_cases = MATRIX if cases is None else list(cases)
    runs = int(os.environ.get("RANK_RUNS", "5"))
    thread_budget = int(os.environ.get("GOLD1_BENCH_THREADS", "12"))
    if thread_budget < 2:
        raise SystemExit("ERROR: GOLD1_BENCH_THREADS must be >= 2")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    outdir = ROOT / "results"; outdir.mkdir(exist_ok=True)
    rows=[]; detail=[]
    for idx, (L,H,label) in enumerate(matrix_cases,1):
        print(f"\n===== MATRIX {idx}/{len(matrix_cases)} {label} [{L},{H}] =====", flush=True)
        env=os.environ.copy(); env["RANK_RUNS"] = str(runs)
        child_retries = max(0, int(os.environ.get("MATRIX_CHILD_RETRIES", "1")))
        p = None
        m = []
        child_attempts = []
        for child_attempt in range(1, child_retries + 2):
            p=subprocess.run(benchmark_command(L, H, runs),cwd=ROOT,env=env,
                             stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            print(p.stdout, end="")
            m=re.findall(r"(?m)^RESULT_JSON=(.+)$",p.stdout)
            child_attempts.append({"attempt": child_attempt, "returncode": p.returncode,
                                   "produced_result_json": bool(m)})
            if m:
                break
            if child_attempt <= child_retries:
                print(f"RETRY: {label} child produced no RESULT_JSON (attempt {child_attempt}); retrying once.", flush=True)
        if not m:
            rows.append({
                "label": label, "L": L, "H": H, "width": H-L,
                "thread budget": thread_budget,
                "validation_status": "child_failed",
                "error": f"benchmark child exit={p.returncode}; no RESULT_JSON produced after {len(child_attempts)} attempt(s)",
            })
            detail.append({
                "label": label, "result_json": None,
                "child_returncode": p.returncode, "child_output": p.stdout,
                "child_attempts": child_attempts,
            })
            print(f"WARNING: {label} failed without RESULT_JSON after retry; recorded and continuing.", flush=True)
            continue
        jp=Path(m[-1].strip())
        try: d=json.loads(jp.read_text(encoding="utf-8"))
        except Exception as e:
            rows.append({"label":label,"L":L,"H":H,"width":H-L,
                         "thread budget":thread_budget,
                         "validation_status":"error","error":str(e)})
            continue
        detail.append({"label":label,"result_json":str(jp),"result":d,"child_attempts":child_attempts})
        status=d.get("validation_status","unknown")
        if status != "pass":
            bm=d.get("build_metadata",{})
            modes=d.get("modes") or {}
            pcal=(d.get("calibration") or {}).get("primecount") or {}
            rows.append({"label":label,"L":L,"H":H,"width":H-L,
                         "thread budget":d.get("thread_budget", thread_budget),
                         "expected_count":d.get("task",{}).get("interval_count"),
                         "CPU model":bm.get("cpu_model"),
                         "RAM GiB":bm.get("total_ram_gib"),
                         "physical cores":bm.get("physical_core_count"),
                         "logical cores":bm.get("logical_cpu_count"),
                         "OS":bm.get("os_caption"),
                         "OS version":bm.get("os_version"),
                         "OS build":bm.get("os_build_number"),
                         "benchmark started UTC":d.get("benchmark_started_utc"),
                         "benchmark finished UTC":d.get("benchmark_finished_utc"),
                         "Gold1 source SHA256":bm.get("gold1_source_sha256"),
                         "Gold1 binary SHA256":bm.get("gold1_binary_sha256"),
                         "benchmark harness SHA256":bm.get("benchmark_harness_sha256"),
                         "primecount binary SHA256":bm.get("primecount_binary_sha256"),
                         "fast-prime binary SHA256":bm.get("fastprime_binary_sha256"),
                         "primesieve binary SHA256":bm.get("primesieve_binary_sha256"),
                         "primesieve pinned version":bm.get("primesieve_pinned_version"),
            "Visual Studio version":bm.get("visual_studio_installation_version"),
            "Visual Studio CMake generator":bm.get("visual_studio_cmake_generator"),
                         "fast-prime commit":bm.get("fastprime_commit"),
                         "fast-prime Rust toolchain":bm.get("fastprime_toolchain"),
                         "fast-prime build rustc":bm.get("rustc"),
                         "ambient rustc":bm.get("ambient_rustc"),
                         "Gold1 execution mode":d.get("gold1_execution_mode"),
                         "Gold1 AC mode":d.get("gold1_ac_mode"),
                         "primecount mode":modes.get("primecount"),
                         "primecount calibration total repeats":pcal.get("total_repeats"),
                         "primecount initial near tie":pcal.get("initial_near_tie"),
                         "primecount tie-break repeats":pcal.get("tie_break_repeats_performed"),
                         "primecount concurrent relative gain":pcal.get("concurrent_relative_gain"),
                         "primecount selection reason":pcal.get("selection_reason"),
                         "fast-prime mode":modes.get("fastprime"),
                         "primesieve mode":modes.get("primesieve"),
                         "validation_status":status,"error":d.get("reason","")})
            continue
        mg=med(d,"gold1"); mp=med(d,"primesieve"); mc=med(d,"primecount"); mf=med(d,"fastprime")
        ranking=d.get("ranking",[])
        cg=d.get("common_gourdon") or {}
        eg=d.get("endpoint_gourdon") or {}
        egh=eg.get("high") or {}; egl=eg.get("low") or {}
        bm=d.get("build_metadata",{})
        modes=d.get("modes") or {}
        pcal=(d.get("calibration") or {}).get("primecount") or {}
        rows.append({
            "label":label,"L":L,"H":H,"width":H-L,
            "thread budget":d.get("thread_budget", thread_budget),
            "expected_count":d["task"]["interval_count"],
            "Gold1 median":mg,"primesieve median":mp,"primecount median":mc,"fast-prime median":mf,
            "winner":ranking[0] if ranking else None,
            "Gold1/primesieve speedup":ratio(mg,mp),
            "Gold1/primecount speedup":ratio(mg,mc),
            "Gold1/fast-prime speedup":ratio(mg,mf),
            "y":cg.get("y"),"z":cg.get("z"),"k":cg.get("k"),
            "CPU model":bm.get("cpu_model"),
            "RAM GiB":bm.get("total_ram_gib"),
            "physical cores":bm.get("physical_core_count"),
            "logical cores":bm.get("logical_cpu_count"),
            "OS":bm.get("os_caption"),
            "OS version":bm.get("os_version"),
            "OS build":bm.get("os_build_number"),
            "benchmark started UTC":d.get("benchmark_started_utc"),
            "benchmark finished UTC":d.get("benchmark_finished_utc"),
            "Gold1 source SHA256":bm.get("gold1_source_sha256"),
            "Gold1 binary SHA256":bm.get("gold1_binary_sha256"),
            "benchmark harness SHA256":bm.get("benchmark_harness_sha256"),
            "primecount binary SHA256":bm.get("primecount_binary_sha256"),
            "fast-prime binary SHA256":bm.get("fastprime_binary_sha256"),
            "primesieve binary SHA256":bm.get("primesieve_binary_sha256"),
            "primesieve pinned version":bm.get("primesieve_pinned_version"),
            "Visual Studio version":bm.get("visual_studio_installation_version"),
            "Visual Studio CMake generator":bm.get("visual_studio_cmake_generator"),
            "fast-prime commit":bm.get("fastprime_commit"),
            "fast-prime Rust toolchain":bm.get("fastprime_toolchain"),
            "fast-prime build rustc":bm.get("rustc"),
            "ambient rustc":bm.get("ambient_rustc"),
            "Gold1 execution mode":d.get("gold1_execution_mode"),
            "endpoint high y":egh.get("y"),"endpoint high z":egh.get("z"),"endpoint high k":egh.get("k"),
            "endpoint low y":egl.get("y"),"endpoint low z":egl.get("z"),"endpoint low k":egl.get("k"),
            "Gold1 AC mode":d.get("gold1_ac_mode"),
            "primecount mode":modes.get("primecount"),
            "primecount calibration total repeats":pcal.get("total_repeats"),
            "primecount initial near tie":pcal.get("initial_near_tie"),
            "primecount tie-break repeats":pcal.get("tie_break_repeats_performed"),
            "primecount concurrent relative gain":pcal.get("concurrent_relative_gain"),
            "primecount selection reason":pcal.get("selection_reason"),
            "fast-prime mode":modes.get("fastprime"),
            "primesieve mode":modes.get("primesieve"),
            "validation_status":"pass",
        })

    csvp=outdir/f"{stamp}_{suite_name}.csv"
    jsonp=outdir/f"{stamp}_{suite_name}.json"
    fields=["label","L","H","width","thread budget","expected_count","Gold1 median","primesieve median",
            "primecount median","fast-prime median","winner","Gold1/primesieve speedup",
            "Gold1/primecount speedup","Gold1/fast-prime speedup","y","z","k",
            "CPU model","RAM GiB","physical cores","logical cores","OS","OS version","OS build",
            "benchmark started UTC","benchmark finished UTC","Gold1 source SHA256",
            "Gold1 binary SHA256","benchmark harness SHA256","primecount binary SHA256",
            "fast-prime binary SHA256","primesieve binary SHA256","primesieve pinned version",
            "Visual Studio version","Visual Studio CMake generator",
            "fast-prime commit","fast-prime Rust toolchain","fast-prime build rustc","ambient rustc",
            "Gold1 execution mode","endpoint high y","endpoint high z","endpoint high k",
            "endpoint low y","endpoint low z","endpoint low k",
            "Gold1 AC mode","primecount mode","primecount calibration total repeats",
            "primecount initial near tie","primecount tie-break repeats",
            "primecount concurrent relative gain","primecount selection reason",
            "fast-prime mode","primesieve mode",
            "validation_status","error"]
    with csvp.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    first_pass = next((x["result"] for x in detail if x.get("result",{}).get("validation_status") == "pass"), None)
    jsonp.write_text(json.dumps({
        "schema_version":SCHEMA_VERSION,
        "suite":suite_name,"utc":stamp,"runs":runs,"thread_budget":thread_budget,
        "thread_plan": first_pass.get("thread_plan", {}) if first_pass else {},
        "protocol_calibration_policy": first_pass.get("protocol_calibration_policy", {}) if first_pass else {},
        "provenance": {
            "build_metadata": first_pass.get("build_metadata",{}) if first_pass else {},
            "benchmark_started_utc": first_pass.get("benchmark_started_utc") if first_pass else None,
        },
        "rows":rows,"details":detail
    },indent=2),encoding="utf-8")
    print(f"\nSaved aggregate CSV: {csvp}")
    print(f"Saved aggregate JSON: {jsonp}")

if __name__=="__main__": main()
