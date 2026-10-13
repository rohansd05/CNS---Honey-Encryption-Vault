"""API latency benchmark. Owner: T5.

Usage:
    python -m scripts.bench_api --base-url URL --runs 30 [--out results.json]
"""

from __future__ import annotations

import argparse
import json
import secrets
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx


def summarize(latencies_ms: list[float]) -> dict[str, float]:
    """Return summary statistics for a list of latencies in milliseconds."""
    if not latencies_ms:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}

    s = sorted(latencies_ms)
    mean = statistics.fmean(s)

    def percentile(p: float) -> float:
        import math

        return s[max(0, math.ceil(p * len(s)) - 1)]

    p50 = percentile(0.50)
    p95 = percentile(0.95)
    max_val = s[-1]

    return {
        "mean": mean,
        "p50": p50,
        "p95": p95,
        "max": max_val,
    }


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    parser = argparse.ArgumentParser(description="API latency benchmark")
    parser.add_argument("--base-url", required=True, help="Base URL of the API")
    parser.add_argument("--runs", type=int, default=30, help="Number of runs (N)")
    parser.add_argument("--out", type=str, help="Output JSON file path")

    args = parser.parse_args(argv)
    runs = args.runs
    base_url = args.base_url.rstrip("/")

    username = f"bench_{secrets.token_hex(4)}"
    login_pw = "login_" + secrets.token_urlsafe(16)
    master_pw = "master_" + secrets.token_urlsafe(16)

    client_kwargs: dict[str, Any] = {"base_url": base_url, "timeout": 30.0}
    if transport:
        client_kwargs["transport"] = transport

    # Use a single client for all requests.
    client = httpx.Client(**client_kwargs)

    try:
        # Register
        reg_res = client.post(
            "/api/auth/register",
            json={
                "username": username,
                "login_password": login_pw,
                "master_password": master_pw,
            },
        )
        if reg_res.status_code != 201:
            print(f"Failed to register: {reg_res.status_code} {reg_res.text}")
            return 1

        # Login to get token
        login_res = client.post(
            "/api/auth/login",
            json={"username": username, "login_password": login_pw},
        )
        if login_res.status_code != 200:
            print(f"Failed to login: {login_res.status_code} {login_res.text}")
            return 1

        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add 3 entries
        for i in range(3):
            res = client.post(
                "/api/vault/entries",
                headers=headers,
                json={
                    "master_password": master_pw,
                    "service": f"service_{i}.com",
                    "username": f"user{i}",
                    "password": f"pass{i}",
                },
            )
            if res.status_code != 201:
                print(f"Failed to add entry {i}: {res.status_code} {res.text}")
                return 1

        # Benchmark variables
        latencies = {
            "unlock_correct": [],
            "unlock_wrong": [],
            "login": [],
        }

        # Measure N unlocks with the correct master password
        for _ in range(runs):
            t0 = time.perf_counter()
            res = client.post(
                "/api/vault/unlock",
                headers=headers,
                json={"master_password": master_pw},
            )
            latencies["unlock_correct"].append((time.perf_counter() - t0) * 1000.0)
            if res.status_code != 200:
                print(f"Unlock (correct) failed: {res.status_code} {res.text}")
                return 1

        # Measure N unlocks with random wrong master passwords
        for _ in range(runs):
            wrong_pw = secrets.token_urlsafe(16)
            t0 = time.perf_counter()
            res = client.post(
                "/api/vault/unlock",
                headers=headers,
                json={"master_password": wrong_pw},
            )
            latencies["unlock_wrong"].append((time.perf_counter() - t0) * 1000.0)
            if res.status_code != 200:
                print(f"Unlock (wrong) failed: {res.status_code} {res.text}")
                return 1

        # Measure N logins
        for _ in range(runs):
            t0 = time.perf_counter()
            res = client.post(
                "/api/auth/login",
                json={"username": username, "login_password": login_pw},
            )
            latencies["login"].append((time.perf_counter() - t0) * 1000.0)
            if res.status_code != 200:
                print(f"Login failed: {res.status_code} {res.text}")
                return 1

        # Summary
        summary = {k: summarize(v) for k, v in latencies.items()}

        print(f"API Latency Benchmark ({runs} runs)")
        print(
            f"{'Operation':<20} | {'Mean (ms)':>10} | {'p50 (ms)':>10} | "
            f"{'p95 (ms)':>10} | {'Max (ms)':>10}"
        )
        print("-" * 71)
        for op, stats in summary.items():
            print(
                f"{op:<20} | {stats['mean']:>10.1f} | {stats['p50']:>10.1f} | "
                f"{stats['p95']:>10.1f} | {stats['max']:>10.1f}"
            )

        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"\nWrote results to {args.out}")

    finally:
        client.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
