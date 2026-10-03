"""Smoke test for ``GET /hc/health``. Owner: T2 — Rohan."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_ok() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/hc/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "honeychecker", "version": "0.1.0"}
