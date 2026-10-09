#!/usr/bin/env python3
from __future__ import annotations
import os, platform, shutil, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def yes(v): return "OK" if v else "MISSING"
def ver(cmd):
    try:
        p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
        return p.stdout.strip().splitlines()[0] if p.stdout.strip() else f"rc={p.returncode}"
    except Exception as e: return f"unavailable ({e})"

print("Gold1 v2.3.6 minimal environment doctor")
print(f"OS: {platform.platform()}")
print(f"Python: {sys.version.split()[0]}")
print(f"CPU visible: {os.cpu_count()}")
print(f"Benchmark thread budget: {os.environ.get('GOLD1_BENCH_THREADS', '12')}")
print(f"Protocol calibration repeats: {os.environ.get('GOLD1_PROTOCOL_CALIBRATION_REPEATS', '3')}")
print(f"Protocol tie-break repeats: {os.environ.get('GOLD1_PROTOCOL_TIE_BREAK_REPEATS', '2')}")
print(f"Protocol near-tie margin: {os.environ.get('GOLD1_PROTOCOL_NEAR_TIE', '0.02')}")
for c in ("git","curl","cmake","ninja","c++"):
    print(f"{c}: {yes(shutil.which(c))} {ver([c,'--version']) if shutil.which(c) else ''}")
print(f"rustup: {yes(shutil.which('rustup'))}")
print(f"cargo: {yes(shutil.which('cargo'))}")
for rel in ("gold1/build/gold1-interval","gold1/build/gold1-interval.exe","gold1/build/primecount","gold1/build/primecount.exe","third_party/fast-prime.binary","third_party/primesieve.binary"):
    p=ROOT/rel
    print(f"{rel}: {yes(p.exists())}")
if platform.system()=="Windows" or "MINGW" in platform.system().upper():
    print(f"MSYSTEM={os.environ.get('MSYSTEM','<unset>')}")
    candidates=[
        Path('/c/Program Files/CMake/bin/cmake.exe'),
        Path('/c/Program Files (x86)/CMake/bin/cmake.exe'),
    ]
    native=next((x for x in candidates if x.exists()), None)
    if native:
        print(f"Windows-native CMake: OK {native}")
    else:
        print("Windows-native CMake: MISSING/CHECK (optional; only needed for fast-prime comparator)")
    detector=ROOT/'platform'/'detect_visual_studio.sh'
    if detector.exists():
        try:
            r=subprocess.run(['bash',str(detector)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=10)
            if r.returncode==0 and r.stdout.strip():
                parts=r.stdout.strip().split('\t')
                print(f"Visual Studio C++ toolchain: OK {parts[-1]} ({parts[1] if len(parts)>1 else 'installed'})")
            else:
                print("Visual Studio C++ toolchain: OPTIONAL/MISSING (core Gold1 setup is unaffected)")
        except Exception as e:
            print(f"Visual Studio C++ toolchain: CHECK ({e})")
print("Core quick start: ./setup_all.sh && ./validate_all.sh")
print("Optional fourth comparator: GOLD1_WITH_FASTPRIME=1 ./setup_all.sh")
