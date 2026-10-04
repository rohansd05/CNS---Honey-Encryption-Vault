"""Tests for HoneycheckerClient with httpx.MockTransport.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import httpx
import pytest

from app.config import get_settings
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)


def test_client_check_match() -> None:
    """Client returns True when honeychecker returns match=True."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hc/check"
        return httpx.Response(200, json={"match": True})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    assert client.check(user_id="user-1", index=4) is True


def test_client_check_mismatch() -> None:
    """Client returns False when honeychecker returns match=False."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hc/check"
        return httpx.Response(200, json={"match": False})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    assert client.check(user_id="user-1", index=7) is False


def test_client_check_unknown_user_404() -> None:
    """Client returns False if honeychecker returns 404 for unknown user."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "Unknown user"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    assert client.check(user_id="ghost", index=1) is False


def test_client_check_unavailable_5xx() -> None:
    """Client raises HoneycheckerUnavailable on HTTP 500 or 503."""

    def handler_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler_500)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    with pytest.raises(HoneycheckerUnavailable, match="500"):
        client.check(user_id="user-1", index=4)

    def handler_503(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    transport_503 = httpx.MockTransport(handler_503)
    client_503 = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(
            transport=transport_503, base_url="http://test-hc:8001"
        ),
    )

    with pytest.raises(HoneycheckerUnavailable, match="503"):
        client_503.check(user_id="user-1", index=4)


def test_client_check_unavailable_network_error() -> None:
    """Client raises HoneycheckerUnavailable on network connect or timeout error."""

    def handler_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused", request=request)

    transport = httpx.MockTransport(handler_error)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    with pytest.raises(HoneycheckerUnavailable, match="network error"):
        client.check(user_id="user-1", index=4)


def test_client_register_success_and_conflict() -> None:
    """register succeeds on 201 and raises HTTPStatusError on 409 Conflict."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hc/register"
        if b"user-dup" in request.content:
            return httpx.Response(409, json={"detail": "Already registered"})
        return httpx.Response(201, json={"status": "registered"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    # Success case
    client.register(user_id="user-new", index=3)

    # 409 Conflict case
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        client.register(user_id="user-dup", index=3)
    assert exc_info.value.response.status_code == 409


def test_client_register_unavailable() -> None:
    """register raises HoneycheckerUnavailable on server 5xx or network error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="Bad Gateway")

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    with pytest.raises(HoneycheckerUnavailable):
        client.register(user_id="user-1", index=3)


def test_client_health() -> None:
    """health returns True when status and db are ok, False if db down, and raises on 5xx."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/hc/health"
        if request.headers.get("X-Simulate-Down") == "1":
            return httpx.Response(200, json={"status": "ok", "db": "down"})
        if request.headers.get("X-Simulate-500") == "1":
            return httpx.Response(500, text="Down")
        return httpx.Response(200, json={"status": "ok", "db": "ok"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    assert client.health() is True

    # When db is down, health returns False
    client_down = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(
            transport=transport,
            base_url="http://test-hc:8001",
            headers={"X-Simulate-Down": "1"},
        ),
    )
    assert client_down.health() is False

    # When server returns 500, raises HoneycheckerUnavailable
    client_err = HoneycheckerClient(
        base_url="http://test-hc:8001",
        client_factory=lambda: httpx.Client(
            transport=transport,
            base_url="http://test-hc:8001",
            headers={"X-Simulate-500": "1"},
        ),
    )
    with pytest.raises(HoneycheckerUnavailable):
        client_err.health()


def test_get_honeychecker_client_dependency() -> None:
    """FastAPI dependency get_honeychecker_client builds client from settings."""
    settings = get_settings()
    client = get_honeychecker_client()
    try:
        assert client.base_url == settings.honeychecker_url.rstrip("/")
        assert client.timeout == settings.honeychecker_timeout_seconds
    finally:
        client.close()
