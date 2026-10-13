"""Smoke test for ``GET /api/health``. Owner: T2 — Tanuj."""

from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "version": "0.1.0",
        "honeycore_impl": "stub",
        "honeychecker": "unknown",
    }


def test_openapi_lists_health(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/health" in resp.json()["paths"]
