"""Tests for GET /api/eval/summary.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §7.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_results(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "latest.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


class TestEvalSummary:
    """GET /api/eval/summary — no auth required."""

    def test_404_when_file_missing(self, client: TestClient, tmp_path: Path, monkeypatch) -> None:
        """Returns 404 with the correct detail when the results file does not exist."""
        missing = tmp_path / "nonexistent.json"
        monkeypatch.setenv("EVAL_RESULTS_PATH", str(missing))

        from app.config import get_settings

        get_settings.cache_clear()
        try:
            resp = client.get("/api/eval/summary")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 404
        assert resp.json()["detail"] == "No evaluation results yet"

    def test_200_returns_json_contents(
        self, client: TestClient, tmp_path: Path, monkeypatch
    ) -> None:
        """Returns the exact JSON contents of the results file."""
        payload = {"dte_accuracy": 0.92, "attack_resistance": 0.87, "samples": 1000}
        results_path = _write_results(tmp_path, payload)
        monkeypatch.setenv("EVAL_RESULTS_PATH", str(results_path))

        from app.config import get_settings

        get_settings.cache_clear()
        try:
            resp = client.get("/api/eval/summary")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 200
        assert resp.json() == payload

    def test_404_when_file_corrupt(self, client: TestClient, tmp_path: Path, monkeypatch) -> None:
        """Returns 404 (not 500) when the results file contains invalid JSON."""
        bad_file = tmp_path / "latest.json"
        bad_file.write_text("this is not json }{", encoding="utf-8")
        monkeypatch.setenv("EVAL_RESULTS_PATH", str(bad_file))

        from app.config import get_settings

        get_settings.cache_clear()
        try:
            resp = client.get("/api/eval/summary")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 404
        assert resp.json()["detail"] == "No evaluation results yet"

    def test_no_auth_required(self, client: TestClient, tmp_path: Path, monkeypatch) -> None:
        """Endpoint must be accessible without any Authorization header."""
        payload = {"status": "ok"}
        results_path = _write_results(tmp_path, payload)
        monkeypatch.setenv("EVAL_RESULTS_PATH", str(results_path))

        from app.config import get_settings

        get_settings.cache_clear()
        try:
            # Deliberately pass no Authorization header.
            resp = client.get("/api/eval/summary", headers={})
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 200

    def test_response_content_type_is_json(
        self, client: TestClient, tmp_path: Path, monkeypatch
    ) -> None:
        """Response Content-Type must be application/json."""
        payload = {"key": "value"}
        results_path = _write_results(tmp_path, payload)
        monkeypatch.setenv("EVAL_RESULTS_PATH", str(results_path))

        from app.config import get_settings

        get_settings.cache_clear()
        try:
            resp = client.get("/api/eval/summary")
        finally:
            get_settings.cache_clear()

        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
