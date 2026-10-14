from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from scripts.bench_api import main, summarize, warm_service


def test_summarize():
    """Test the summarize pure function."""
    # Test empty list
    assert summarize([]) == {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}

    # Test single item
    assert summarize([10.0]) == {"mean": 10.0, "p50": 10.0, "p95": 10.0, "max": 10.0}

    # Test multiple items (1 to 100)
    latencies = [float(i) for i in range(1, 101)]
    s = summarize(latencies)
    assert s["mean"] == 50.5
    assert s["p50"] == 50.0  # math.ceil(0.50 * 100) - 1 = 49 -> 50.0
    assert s["p95"] == 95.0  # math.ceil(0.95 * 100) - 1 = 94 -> 95.0
    assert s["max"] == 100.0


def test_warm_service_success():
    """Test warm_service succeeds when /api/health reports ok."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/health"
        return httpx.Response(200, json={"status": "ok", "honeychecker": "ok"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(base_url="http://testserver", transport=transport)
    elapsed = warm_service(client, max_attempts=3, interval_seconds=0.01)
    assert elapsed >= 0.0


def test_warm_service_retry_and_timeout():
    """Test warm_service retries and raises RuntimeError on timeout."""
    attempts = 0

    def retry_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return httpx.Response(503, json={"status": "degraded", "honeychecker": "down"})
        return httpx.Response(200, json={"status": "ok", "honeychecker": "ok"})

    client_retry = httpx.Client(
        base_url="http://testserver", transport=httpx.MockTransport(retry_handler)
    )
    elapsed = warm_service(client_retry, max_attempts=5, interval_seconds=0.01)
    assert elapsed >= 0.0
    assert attempts == 2

    # Timeout case
    def fail_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"status": "down", "honeychecker": "down"})

    client_fail = httpx.Client(
        base_url="http://testserver", transport=httpx.MockTransport(fail_handler)
    )
    with pytest.raises(RuntimeError, match="Service warming timed out"):
        warm_service(client_fail, max_attempts=3, interval_seconds=0.01)


def test_main_http_flow(capsys, tmp_path: Path):
    """Test the HTTP flow using httpx.MockTransport with pacing disabled."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/health":
            return httpx.Response(200, json={"status": "ok", "honeychecker": "ok"})
        elif path == "/api/auth/register":
            return httpx.Response(201, json={"id": "user1", "username": "bench"})
        elif path == "/api/auth/login":
            return httpx.Response(
                200,
                json={"access_token": "fake-jwt-token-xyz", "token_type": "bearer", "user": {}},
            )
        elif path == "/api/vault/export":
            return httpx.Response(
                200, json={"v": 1, "kdf": {"alg": "argon2id", "profile": "server_lite"}}
            )
        elif path == "/api/vault/entries":
            return httpx.Response(201, json={"id": "entry-id"})
        elif path == "/api/vault/unlock":
            return httpx.Response(
                200,
                json={"entries": [], "sigil": {"emojis": ["a", "b", "c"], "color": "#112233"}},
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    out_file = tmp_path / "results.json"

    args = [
        "--base-url",
        "http://testserver",
        "--runs",
        "5",
        "--out",
        str(out_file),
        "--no-pace",
    ]

    ret = main(args, transport=transport)
    assert ret == 0

    captured = capsys.readouterr()
    assert "API Latency Benchmark (5 runs)" in captured.out
    assert "unlock_correct" in captured.out
    assert "unlock_wrong" in captured.out
    assert "login" in captured.out
    assert "fake-jwt-token-xyz" not in captured.out
    assert "master_" not in captured.out
    assert "login_" not in captured.out

    assert out_file.exists()
    with open(out_file, encoding="utf-8") as f:
        data = json.load(f)

    assert "unlock_correct" in data
    assert "unlock_wrong" in data
    assert "login" in data
    assert data["kdf_profile"] == "server_lite"
    assert "cold_start_s" in data
    assert data["login"]["mean"] >= 0.0


def test_wrong_unlock_non_200_fails(capsys):
    """Test that wrong-master unlock returning non-200 causes main to exit with code 1."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/health":
            return httpx.Response(200, json={"status": "ok", "honeychecker": "ok"})
        elif path == "/api/auth/register":
            return httpx.Response(201, json={"id": "user1", "username": "bench"})
        elif path == "/api/auth/login":
            return httpx.Response(
                200, json={"access_token": "token", "token_type": "bearer", "user": {}}
            )
        elif path == "/api/vault/export":
            return httpx.Response(200, json={"kdf": {"profile": "server_lite"}})
        elif path == "/api/vault/entries":
            return httpx.Response(201, json={"id": "entry-id"})
        elif path == "/api/vault/unlock":
            body = json.loads(request.read())
            # Fail if password is wrong (violates HE invariant)
            if body.get("master_password", "").startswith("wrong_"):
                return httpx.Response(400, json={"detail": "Wrong password"})
            return httpx.Response(200, json={"entries": [], "sigil": {}})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    args = [
        "--base-url",
        "http://testserver",
        "--runs",
        "2",
        "--no-pace",
    ]

    ret = main(args, transport=transport)
    assert ret == 1
    captured = capsys.readouterr()
    assert "Unlock (wrong) failed at run 1: status 400" in captured.out
