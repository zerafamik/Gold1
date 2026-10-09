#!/usr/bin/env python3
# Copyright (C) 2026 [YOUR LEGAL NAME]. All rights reserved.
"""Stamp the exact legal owner across the release and refresh provenance.

Usage:
    python release_stamp.py "Exact Legal Name"
    python release_stamp.py --refresh-only

The first form replaces every UTF-8 `[YOUR LEGAL NAME]` placeholder in
release-controlled text files, then regenerates SOURCE_PROVENANCE.sha256,
gold1/MANIFEST.sha256 and MANIFEST.sha256 in dependency order.
"""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLACEHOLDER = "[YOUR LEGAL NAME]"
SKIP_DIR_NAMES = {".git", "__pycache__", "build", "results", "third_party", "primecount-8.7"}
BINARY_SUFFIXES = {".pdf", ".docx", ".zip", ".gz", ".xz", ".7z", ".exe", ".dll", ".a", ".o", ".obj", ".png", ".jpg", ".jpeg", ".webp"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_tree_sha256(files: list[Path]) -> tuple[str, int]:
    selected = sorted({x.resolve() for x in files if x.exists() and x.is_file()}, key=lambda x: x.as_posix())
    h = hashlib.sha256()
    h.update(b"GOLD1_CANONICAL_SOURCE_TREE_SHA256_V1\0")
    for path in selected:
        rel = path.relative_to(ROOT.resolve()).as_posix()
        rb = rel.encode("utf-8")
        data = path.read_bytes()
        h.update(len(rb).to_bytes(4, "big"))
        h.update(rb)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest(), len(selected)


def release_controlled(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if path.name == "MANIFEST.sha256" and path.parent == ROOT:
        return False
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return False
    # Ignore downloaded/source archives and ephemeral compiled artifacts.
    if path.suffix.lower() in {".exe", ".dll", ".o", ".obj", ".a"}:
        return False
    return path.is_file()


def stamp_text_files(name: str) -> list[str]:
    changed: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not release_controlled(path):
            continue
        if path.name in {"MANIFEST.sha256", "SOURCE_PROVENANCE.sha256"}:
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PLACEHOLDER in text:
            path.write_text(text.replace(PLACEHOLDER, name), encoding="utf-8", newline="\n")
            changed.append(path.relative_to(ROOT).as_posix())
    return changed


def source_sets() -> tuple[list[Path], list[Path]]:
    gold_files = [ROOT / "gold1" / "apply_patch.py"]
    patch_dir = ROOT / "gold1" / "patch"
    gold_files.extend(x for x in patch_dir.rglob("*") if x.is_file())

    harness_files: list[Path] = []
    for rel in ("tools", "platform"):
        d = ROOT / rel
        if d.exists():
            harness_files.extend(x for x in d.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
    for name in (
        "run_interval_bench.sh", "run_interval_matrix.sh", "run_crossover_bench.sh",
        "run_ranking_bench.sh",
        "validate_interval.sh", "validate_all.sh", "setup_all.sh", "setup_linux.sh",
        "setup_windows_ucrt64.sh", "patch_and_rebuild_fastprime.sh",
    ):
        harness_files.append(ROOT / name)
    for name in ("setup_and_build_linux.sh", "setup_and_build_ucrt64.sh"):
        harness_files.append(ROOT / "gold1" / name)
    return gold_files, harness_files


def write_source_provenance() -> None:
    gold_files, harness_files = source_sets()
    gold_hash, gold_count = canonical_tree_sha256(gold_files)
    harness_hash, harness_count = canonical_tree_sha256(harness_files)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    lines = [
        "Gold1 source and harness provenance - v2.3.6 robust-calibration crossover handover",
        f"Generated UTC={now}", "",
        f"gold1_source_sha256={gold_hash}",
        "gold1_source_sha256_scope=gold1/apply_patch.py + gold1/patch/**",
        f"gold1_source_file_count={gold_count}", "",
        "Per-file Gold1 implementation SHA-256:",
    ]
    for path in sorted(gold_files, key=lambda p: p.relative_to(ROOT).as_posix()):
        if path.exists():
            lines.append(f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}")
    lines += ["", f"benchmark_harness_sha256={harness_hash}",
              "benchmark_harness_sha256_scope=tools/** + platform/** + setup/validation/runner entrypoints",
              f"benchmark_harness_file_count={harness_count}", "",
              "Per-file benchmark harness SHA-256:"]
    for path in sorted(harness_files, key=lambda p: p.relative_to(ROOT).as_posix()):
        if path.exists():
            lines.append(f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}")
    (ROOT / "SOURCE_PROVENANCE.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_manifest(base: Path, manifest: Path, paths: list[Path]) -> None:
    entries = []
    for path in sorted(paths, key=lambda p: p.relative_to(base).as_posix()):
        rel = path.relative_to(base).as_posix()
        entries.append(f"{sha256_file(path)}  ./{rel}")
    manifest.write_text("\n".join(entries) + "\n", encoding="utf-8", newline="\n")


def write_gold1_manifest() -> None:
    base = ROOT / "gold1"
    paths = []
    for path in base.rglob("*"):
        if not path.is_file() or path.name == "MANIFEST.sha256":
            continue
        rel = path.relative_to(base)
        if any(part in SKIP_DIR_NAMES for part in rel.parts):
            continue
        if path.suffix.lower() in {".exe", ".dll", ".a", ".o", ".obj", ".gz", ".zip"}:
            continue
        paths.append(path)
    write_manifest(base, base / "MANIFEST.sha256", paths)


def write_root_manifest() -> None:
    paths = []
    for path in ROOT.rglob("*"):
        if not release_controlled(path):
            continue
        # Root manifest signs the nested gold1 manifest, not itself.
        paths.append(path)
    write_manifest(ROOT, ROOT / "MANIFEST.sha256", paths)


def refresh_hashes() -> None:
    # Dependency order matters: source provenance first, nested manifest second,
    # root manifest last so it covers both regenerated files.
    write_source_provenance()
    write_gold1_manifest()
    write_root_manifest()


def find_placeholders() -> list[str]:
    found = []
    for path in sorted(ROOT.rglob("*")):
        if not release_controlled(path) or path.suffix.lower() in BINARY_SUFFIXES:
            continue
        if path.name in {"MANIFEST.sha256", "SOURCE_PROVENANCE.sha256"}:
            continue
        try:
            if PLACEHOLDER in path.read_text(encoding="utf-8"):
                found.append(path.relative_to(ROOT).as_posix())
        except (UnicodeDecodeError, OSError):
            pass
    return found


def main() -> None:
    ap = argparse.ArgumentParser(description="Stamp Gold1 legal owner and regenerate integrity metadata.")
    ap.add_argument("legal_name", nargs="?", help="Exact legal owner name")
    ap.add_argument("--refresh-only", action="store_true", help="Regenerate provenance/manifests without replacing placeholders")
    args = ap.parse_args()
    if args.refresh_only:
        refresh_hashes()
        print("Refreshed SOURCE_PROVENANCE.sha256, gold1/MANIFEST.sha256 and MANIFEST.sha256")
        return
    if not args.legal_name or not args.legal_name.strip():
        raise SystemExit('usage: python release_stamp.py "Exact Legal Name"')
    name = args.legal_name.strip()
    changed = stamp_text_files(name)
    refresh_hashes()
    remaining = find_placeholders()
    print(f"Stamped legal owner: {name}")
    print(f"Updated {len(changed)} release-controlled text file(s).")
    print("Regenerated SOURCE_PROVENANCE.sha256, gold1/MANIFEST.sha256 and MANIFEST.sha256.")
    if remaining:
        print("WARNING: placeholders remain in: " + ", ".join(remaining))
        raise SystemExit(3)
    print("PASS: no text placeholders remain and integrity metadata is current.")


if __name__ == "__main__":
    main()
