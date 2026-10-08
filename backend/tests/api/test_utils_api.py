"""Tests for POST /api/utils/strength.

Owner: T5 — Aryan. Contract: docs/api-contract.md §9.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestPasswordStrengthAPI:
    """POST /api/utils/strength endpoint test suite."""

    def test_common_password_score_zero(self, client: TestClient) -> None:
        """Common password '123456' returns 200, score 0, and non-empty feedback."""
        resp = client.post("/api/utils/strength", json={"password": "123456"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 0
        assert isinstance(data["entropy_bits"], (int, float))
        assert isinstance(data["feedback"], list)
        assert len(data["feedback"]) > 0

    def test_long_random_mixed_string_score_four(self, client: TestClient) -> None:
        """A long random mixed string with all character classes returns 200, score 4."""
        resp = client.post(
            "/api/utils/strength",
            json={"password": "kX9#mP2$vL5&qW8*zR1!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 4
        assert data["entropy_bits"] >= 80.0
        assert data["feedback"] == []

    def test_response_keys_exact(self, client: TestClient) -> None:
        """Response keys must match the contract exactly: score, entropy_bits, feedback."""
        resp = client.post(
            "/api/utils/strength",
            json={"password": "ValidComplexPassphrase123!"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"score", "entropy_bits", "feedback"}

    def test_empty_password_returns_422(self, client: TestClient) -> None:
        """An empty password violates min_length=1 and returns 422."""
        resp = client.post("/api/utils/strength", json={"password": ""})
        assert resp.status_code == 422

    def test_password_longer_than_limit_returns_422(self, client: TestClient) -> None:
        """A password exceeding 128 characters violates max_length=128 and returns 422."""
        long_pwd = "A" * 129
        resp = client.post("/api/utils/strength", json={"password": long_pwd})
        assert resp.status_code == 422

    def test_422_body_does_not_contain_submitted_password(self, client: TestClient) -> None:
        """Validation error (422) handler must not leak the submitted password in the body."""
        secret_too_long = "SUPER_SECRET_PAYLOAD_LEAK_TEST_" + ("Z" * 120)
        resp = client.post("/api/utils/strength", json={"password": secret_too_long})
        assert resp.status_code == 422
        assert secret_too_long not in resp.text
        assert "SUPER_SECRET_PAYLOAD_LEAK_TEST_" not in resp.text

    def test_response_never_includes_password(self, client: TestClient) -> None:
        """Successful 200 responses must never echo the submitted password."""
        sensitive_sample = "MyUnleakedPassword999!"  # noqa: S105
        resp = client.post("/api/utils/strength", json={"password": sensitive_sample})
        assert resp.status_code == 200
        assert sensitive_sample not in resp.text
        assert "password" not in resp.json()

    def test_missing_body_returns_422(self, client: TestClient) -> None:
        """Empty JSON object or missing request body returns 422."""
        resp_empty_json = client.post("/api/utils/strength", json={})
        assert resp_empty_json.status_code == 422

        resp_no_body = client.post(
            "/api/utils/strength",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp_no_body.status_code == 422

    def test_no_authentication_required(self, client: TestClient) -> None:
        """Endpoint is unauthenticated and works without Authorization header."""
        resp = client.post(
            "/api/utils/strength",
            json={"password": "TestingUnauthenticatedAccess1!"},
            headers={},
        )
        assert resp.status_code == 200

    def test_boundary_passwords(self, client: TestClient) -> None:
        """Passwords at length bounds 1 and 128 are accepted (200)."""
        resp_single_char = client.post("/api/utils/strength", json={"password": "a"})
        assert resp_single_char.status_code == 200

        resp_128_chars = client.post("/api/utils/strength", json={"password": "a" * 128})
        assert resp_128_chars.status_code == 200
