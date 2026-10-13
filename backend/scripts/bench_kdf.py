"""Benchmark Argon2id cost per KDF profile (PROJECT-BRIEF.md §7.6). Owner: T1 — Dhruv.

Usage (from backend/)::

    python scripts/bench_kdf.py --runs 20
    python scripts/bench_kdf.py --runs 5 --profile demo --profile server_lite

Each run derives a key from a fresh random password and salt, so nothing is cached. Prints the
mean and p95 (nearest-rank) wall-clock time in milliseconds per profile. Never prints keys.
"""

from __future__ import annotations

import argparse
import math
import secrets
import statistics
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:  # allow `python scripts/bench_kdf.py`
    sys.path.insert(0, str(BACKEND))

from honeycore.interfaces import KDF_PROFILES, KDFParams  # noqa: E402
from honeycore.kdf import Argon2KDF, new_salt  # noqa: E402


def p95(samples: list[float]) -> float:
    """95th percentile by the nearest-rank method."""
    ordered = sorted(samples)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def bench_profile(kdf: Argon2KDF, params: KDFParams, runs: int) -> list[float]:
    """Return ``runs`` derive timings in milliseconds."""
    timings: list[float] = []
    for _ in range(runs):
        password, salt = secrets.token_urlsafe(12), new_salt()
        start = time.perf_counter()
        kdf.derive(password, salt, params)
        timings.append((time.perf_counter() - start) * 1000)
    return timings


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=10, help="derives per profile (default 10)")
    parser.add_argument(
        "--profile",
        action="append",
        choices=sorted(KDF_PROFILES),
        help="profile to bench (repeatable; default: all)",
    )
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be >= 1")

    kdf = Argon2KDF()
    names = args.profile or list(KDF_PROFILES)
    print(f"Argon2id benchmark, {args.runs} run(s) per profile")
    print(f"{'profile':<12} {'t':>2} {'m (KiB)':>8} {'p':>2} {'mean ms':>9} {'p95 ms':>9}")
    for name in names:
        params = KDF_PROFILES[name]
        timings = bench_profile(kdf, params, args.runs)
        print(
            f"{name:<12} {params.time_cost:>2} {params.memory_cost_kib:>8} "
            f"{params.parallelism:>2} {statistics.fmean(timings):>9.1f} {p95(timings):>9.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
