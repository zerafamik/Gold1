#!/usr/bin/env python3
from pathlib import Path
import re, sys
if len(sys.argv) != 3: raise SystemExit("usage: patch_fastprime.py FASTPRIME_DIR PRIMESIEVE_LIBDIR")
fp=Path(sys.argv[1]).resolve(); libdir=sys.argv[2]
build=fp/'build.rs'; src=fp/'src/bin/prime_count_v8.rs'
if not build.exists() or not src.exists(): raise SystemExit(f"not a fast-prime checkout: {fp}")
s=build.read_text(encoding='utf-8')
s2,n=re.subn(r'println!\("cargo:rustc-link-search=native=[^\"]+"\);', f'println!("cargo:rustc-link-search=native={libdir}");', s, count=1)
if n != 1: raise SystemExit("ERROR: fast-prime build.rs link-search line changed")
build.write_text(s2,encoding='utf-8')
s=src.read_text(encoding='utf-8')
if 'GOLD1_RANKING_ADAPTER_V3' not in s:
    old='''    // Oversubscribe rayon thread pool for better work-stealing across B/AC/D\n    let num_cpus = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(24);\n    let pool_mult: usize = std::env::var("POOL_MULT").ok()\n        .and_then(|s| s.parse().ok()).unwrap_or(3);\n    rayon::ThreadPoolBuilder::new()\n        .num_threads(num_cpus * pool_mult)\n        .build_global()\n        .ok();\n'''
    new='''    // Oversubscribe rayon thread pool for better work-stealing across B/AC/D\n    let num_cpus = std::thread::available_parallelism().map(|n| n.get()).unwrap_or(24);\n    // GOLD1_RANKING_ADAPTER_V3: benchmark-only worker-budget override.\n    // With GOLD1_THREADS unset, upstream behavior is unchanged.\n    let base_threads: usize = std::env::var("GOLD1_THREADS").ok()\n        .and_then(|s| s.parse().ok()).unwrap_or(num_cpus);\n    let pool_mult: usize = std::env::var("POOL_MULT").ok()\n        .and_then(|s| s.parse().ok()).unwrap_or(3);\n    rayon::ThreadPoolBuilder::new()\n        .num_threads(base_threads * pool_mult)\n        .build_global()\n        .ok();\n\n    // GOLD1_RANKING_ADAPTER_V3: arbitrary-x CLI adapter only.\n    if let Some(arg) = std::env::args().nth(1) {\n        let limit: u64 = arg.parse().expect("expected one unsigned integer argument");\n        let count = count_primes(limit);\n        println!("{}", count);\n        return;\n    }\n'''
    if old not in s: raise SystemExit("ERROR: fast-prime V8 source insertion point changed")
    src.write_text(s.replace(old,new,1),encoding='utf-8')
print('PASS: fast-prime V8 portable adapter prepared')
