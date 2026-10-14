"""API latency benchmark. Owner: T5 (Tanmay).

Usage:
    python -m scripts.bench_api --base-url URL --runs 20 [--out results.json] [--pace]
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
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


def warm_service(
    client: httpx.Client,
    max_attempts: int = 30,
    interval_seconds: float = 2.0,
) -> float:
    """Warm the API and Honeychecker using /api/health until healthy.

    Returns the elapsed cold-start/warm-up time in seconds.
    Does not run an unbounded polling loop (bounded by max_attempts).
    """
    t0 = time.perf_counter()
    for attempt in range(1, max_attempts + 1):
        with contextlib.suppress(Exception):
            res = client.get("/api/health")
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "ok" and data.get("honeychecker") == "ok":
                    return time.perf_counter() - t0

        if attempt < max_attempts:
            time.sleep(interval_seconds)

    raise RuntimeError(
        f"Service warming timed out: Honeychecker or API not healthy after {max_attempts} attempts."
    )


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    parser = argparse.ArgumentParser(description="API latency benchmark")
    parser.add_argument("--base-url", required=True, help="Base URL of the API")
    parser.add_argument("--runs", type=int, default=20, help="Number of runs (N)")
    parser.add_argument("--out", type=str, help="Output JSON file path")
    parser.add_argument(
        "--pace",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Pace requests to respect rate limits (<=15 logins/min, <=25 unlocks/min)",
    )
    parser.add_argument(
        "--delay-unlock",
        type=float,
        default=None,
        help="Delay in seconds between unlock operations (default: 2.5s when paced)",
    )
    parser.add_argument(
        "--delay-login",
        type=float,
        default=None,
        help="Delay in seconds between login operations (default: 4.2s when paced)",
    )
    parser.add_argument(
        "--warm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Warm the service via /api/health before benchmarking",
    )

    args = parser.parse_args(argv)
    runs = args.runs
    base_url = args.base_url.rstrip("/")

    # Enable pacing if explicitly set, or auto-enable for remote URLs when transport is None
    is_remote = base_url.startswith(("http://", "https://")) and not any(
        h in base_url for h in ("localhost", "127.0.0.1", "testserver")
    )
    should_pace = args.pace if args.pace is not None else (is_remote and transport is None)

    delay_unlock = (
        args.delay_unlock if args.delay_unlock is not None else (2.5 if should_pace else 0.0)
    )
    delay_login = (
        args.delay_login if args.delay_login is not None else (4.2 if should_pace else 0.0)
    )

    # Generate test credentials (never logged or printed)
    username = f"bench_{secrets.token_hex(4)}"
    login_pw = "login_" + secrets.token_urlsafe(16)
    master_pw = "master_" + secrets.token_urlsafe(16)

    client_kwargs: dict[str, Any] = {"base_url": base_url, "timeout": 30.0}
    if transport:
        client_kwargs["transport"] = transport

    client = httpx.Client(**client_kwargs)

    try:
        cold_start_s = 0.0
        if args.warm:
            print(f"Warming service at {base_url}...")
            cold_start_s = warm_service(client)
            print(f"Service healthy (cold-start / warm-up: {cold_start_s:.2f}s)")

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
            print(f"Failed to register: status {reg_res.status_code}")
            return 1

        # Initial login to get token
        login_res = client.post(
            "/api/auth/login",
            json={"username": username, "login_password": login_pw},
        )
        if login_res.status_code != 200:
            print(f"Failed to login: status {login_res.status_code}")
            return 1

        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Query vault export to detect KDF profile
        kdf_profile = "unknown"
        export_res = client.get("/api/vault/export", headers=headers)
        if export_res.status_code == 200:
            blob = export_res.json()
            kdf_info = blob.get("kdf", {})
            kdf_profile = kdf_info.get("profile", kdf_info.get("alg", "unknown"))

        # Add 3 initial entries
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
                print(f"Failed to add entry {i}: status {res.status_code}")
                return 1

        latencies: dict[str, list[float]] = {
            "unlock_correct": [],
            "unlock_wrong": [],
            "login": [],
        }

        # 1. Measure N unlocks with the correct master password
        print(f"Measuring {runs} correct-master unlocks (delay: {delay_unlock}s)...")
        for i in range(runs):
            t0 = time.perf_counter()
            res = client.post(
                "/api/vault/unlock",
                headers=headers,
                json={"master_password": master_pw},
            )
            elapsed = (time.perf_counter() - t0) * 1000.0
            latencies["unlock_correct"].append(elapsed)
            if res.status_code != 200:
                print(f"Unlock (correct) failed at run {i + 1}: status {res.status_code}")
                return 1
            if delay_unlock > 0 and i < runs - 1:
                time.sleep(delay_unlock)

        if delay_unlock > 0:
            time.sleep(delay_unlock)

        # 2. Measure N unlocks with wrong master passwords (must return HTTP 200)
        print(f"Measuring {runs} wrong-master unlocks (delay: {delay_unlock}s)...")
        for i in range(runs):
            wrong_pw = "wrong_" + secrets.token_urlsafe(16)
            t0 = time.perf_counter()
            res = client.post(
                "/api/vault/unlock",
                headers=headers,
                json={"master_password": wrong_pw},
            )
            elapsed = (time.perf_counter() - t0) * 1000.0
            latencies["unlock_wrong"].append(elapsed)
            if res.status_code != 200:
                print(f"Unlock (wrong) failed at run {i + 1}: status {res.status_code}")
                return 1
            if delay_unlock > 0 and i < runs - 1:
                time.sleep(delay_unlock)

        if delay_login > 0:
            time.sleep(delay_login)

        # 3. Measure N logins
        print(f"Measuring {runs} logins (delay: {delay_login}s)...")
        for i in range(runs):
            t0 = time.perf_counter()
            res = client.post(
                "/api/auth/login",
                json={"username": username, "login_password": login_pw},
            )
            elapsed = (time.perf_counter() - t0) * 1000.0
            latencies["login"].append(elapsed)
            if res.status_code != 200:
                print(f"Login failed at run {i + 1}: status {res.status_code}")
                return 1
            if delay_login > 0 and i < runs - 1:
                time.sleep(delay_login)

        # Summary computation
        summary: dict[str, Any] = {k: summarize(v) for k, v in latencies.items()}
        summary["cold_start_s"] = cold_start_s
        summary["kdf_profile"] = kdf_profile

        print(f"\nAPI Latency Benchmark ({runs} runs)")
        print(f"Target URL:    {base_url}")
        print(f"KDF Profile:   {kdf_profile}")
        print(f"Cold Start:    {cold_start_s:.2f}s")
        print(
            f"{'Operation':<20} | {'Mean (ms)':>10} | {'p50 (ms)':>10} | "
            f"{'p95 (ms)':>10} | {'Max (ms)':>10}"
        )
        print("-" * 71)
        for op in ("unlock_correct", "unlock_wrong", "login"):
            stats = summary[op]
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
