from __future__ import annotations

import httpx

from scripts.bench_api import main, summarize


def test_summarize():
    """Test the summarize pure function."""
    # Test empty list
    assert summarize([]) == {"mean": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}

    # Test single item
    assert summarize([10.0]) == {"mean": 10.0, "p50": 10.0, "p95": 10.0, "max": 10.0}

    # Test multiple items
    # 1 to 100
    latencies = [float(i) for i in range(1, 101)]
    s = summarize(latencies)
    assert s["mean"] == 50.5
    assert s["p50"] == 50.0  # math.ceil(0.50 * 100) - 1 = 49 -> 50.0
    assert s["p95"] == 95.0  # math.ceil(0.95 * 100) - 1 = 94 -> 95.0
    assert s["max"] == 100.0


def test_main_http_flow(capsys, tmp_path):
    """Test the HTTP flow using httpx.MockTransport."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/auth/register":
            return httpx.Response(201, json={"id": "user1", "username": "bench"})
        elif path == "/api/auth/login":
            return httpx.Response(
                200, json={"access_token": "fake-token", "token_type": "bearer", "user": {}}
            )
        elif path == "/api/vault/entries":
            return httpx.Response(201, json={"id": "entry-id"})
        elif path == "/api/vault/unlock":
            return httpx.Response(200, json={"entries": [], "sigil": {}})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)

    out_file = tmp_path / "results.json"

    # Run the main function
    args = [
        "--base-url",
        "http://testserver",
        "--runs",
        "5",
        "--out",
        str(out_file),
    ]

    ret = main(args, transport=transport)
    assert ret == 0

    # Check output format
    captured = capsys.readouterr()
    assert "API Latency Benchmark (5 runs)" in captured.out
    assert "unlock_correct" in captured.out
    assert "unlock_wrong" in captured.out
    assert "login" in captured.out

    # Check JSON output
    assert out_file.exists()
    import json

    with open(out_file) as f:
        data = json.load(f)

    assert "unlock_correct" in data
    assert "unlock_wrong" in data
    assert "login" in data
    assert "mean" in data["login"]
