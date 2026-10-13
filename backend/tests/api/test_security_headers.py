"""Tests for HTTP security headers middleware.

Owner: T5 — Aryan (security headers & evaluation).
"""

from __future__ import annotations

from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.config import Settings
from app.security_headers import (
    SecurityHeadersMiddleware,
    add_security_headers,
)


class TestSecurityHeaders:
    """Security headers test suite."""

    def test_every_header_present_on_api_health(self, client: TestClient) -> None:
        """Verify that /api/health response contains all baseline security headers."""
        resp = client.get("/api/health")
        assert resp.status_code == 200

        # Mandatory security headers
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("referrer-policy") == "no-referrer"
        assert resp.headers.get("permissions-policy") == "camera=(), microphone=(), geolocation=()"
        assert resp.headers.get("cross-origin-opener-policy") == "same-origin"
        assert resp.headers.get("cache-control") == "no-store"
        assert (
            resp.headers.get("content-security-policy")
            == "default-src 'none'; frame-ancestors 'none'"
        )

    def test_cache_control_no_store_on_api_path(self, client: TestClient) -> None:
        """Verify that paths starting with /api/ receive Cache-Control: no-store."""
        resp = client.get("/api/health")
        assert resp.headers.get("cache-control") == "no-store"

    def test_relaxed_csp_on_docs(self, client: TestClient) -> None:
        """Verify that /docs, /redoc, and /openapi.json get the relaxed CSP for Swagger & ReDoc."""
        for path in ("/docs", "/redoc", "/openapi.json"):
            resp = client.get(path)
            assert resp.status_code == 200
            csp = resp.headers.get("content-security-policy", "")
            assert "cdn.jsdelivr.net" in csp
            assert "'unsafe-inline'" in csp
            assert "data:" in csp
            # Cache-Control: no-store should not be injected on non-API docs paths
            assert resp.headers.get("cache-control") != "no-store"

    def test_hsts_absent_when_disabled(self, client: TestClient) -> None:
        """Strict-Transport-Security must be absent when enable_hsts is False (non-prod)."""
        resp = client.get("/api/health")
        assert "strict-transport-security" not in resp.headers

    def test_hsts_present_when_enabled(self) -> None:
        """Strict-Transport-Security must be set when enable_hsts is True."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

        @app.get("/api/health")
        def dummy_health():
            return {"status": "ok"}

        with TestClient(app) as hsts_client:
            resp = hsts_client.get("/api/health")
            assert resp.status_code == 200
            assert (
                resp.headers.get("strict-transport-security")
                == "max-age=31536000; includeSubDomains"
            )

    def test_add_security_headers_helper_hsts_by_app_env(self) -> None:
        """Helper add_security_headers enables HSTS only when app_env is 'production'."""
        prod_settings = Settings(
            app_env="production",
            bob_login_password="test-password-1",  # noqa: S106
            bob_master_password="test-password-2",  # noqa: S106
        )
        dev_settings = Settings(
            app_env="development",
            bob_login_password="test-password-1",  # noqa: S106
            bob_master_password="test-password-2",  # noqa: S106
        )

        prod_app = FastAPI()
        add_security_headers(prod_app, prod_settings)

        @prod_app.get("/api/test")
        def prod_route():
            return {"status": "ok"}

        with TestClient(prod_app) as prod_client:
            resp = prod_client.get("/api/test")
            assert (
                resp.headers.get("strict-transport-security")
                == "max-age=31536000; includeSubDomains"
            )

        dev_app = FastAPI()
        add_security_headers(dev_app, dev_settings)

        @dev_app.get("/api/test")
        def dev_route():
            return {"status": "ok"}

        with TestClient(dev_app) as dev_client:
            resp = dev_client.get("/api/test")
            assert "strict-transport-security" not in resp.headers

    def test_cors_preflight_returns_access_control_headers(self, client: TestClient) -> None:
        """CORS preflight (OPTIONS) request must return its Access-Control-* headers."""
        resp = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert resp.status_code == 200
        assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
        assert "access-control-allow-methods" in resp.headers
        assert "access-control-allow-headers" in resp.headers

    def test_existing_headers_not_overwritten(self) -> None:
        """Headers already set by endpoints or handlers must not be overwritten."""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)

        @app.get("/api/custom")
        def custom_route():
            return Response(
                content='{"custom": true}',
                media_type="application/json",
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "X-Frame-Options": "SAMEORIGIN",
                    "X-Content-Type-Options": "custom-nosniff",
                    "Referrer-Policy": "strict-origin",
                    "Permissions-Policy": "camera=*",
                    "Cross-Origin-Opener-Policy": "unsafe-none",
                    "Content-Security-Policy": "default-src 'self'",
                    "Strict-Transport-Security": "max-age=100",
                },
            )

        with TestClient(app) as custom_client:
            resp = custom_client.get("/api/custom")
            assert resp.status_code == 200
            assert resp.headers.get("cache-control") == "public, max-age=86400"
            assert resp.headers.get("x-frame-options") == "SAMEORIGIN"
            assert resp.headers.get("x-content-type-options") == "custom-nosniff"
            assert resp.headers.get("referrer-policy") == "strict-origin"
            assert resp.headers.get("permissions-policy") == "camera=*"
            assert resp.headers.get("cross-origin-opener-policy") == "unsafe-none"
            assert resp.headers.get("content-security-policy") == "default-src 'self'"
            assert resp.headers.get("strict-transport-security") == "max-age=100"

    def test_response_body_unmodified(self, client: TestClient) -> None:
        """Pure ASGI middleware must never read, log, or mutate the response body."""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
