"""Tests for HoneycheckerClient with httpx.MockTransport.

Owner: T2 — Rohan. Phase 1 & Phase 3 (PROJECT-BRIEF.md §8, §10, ADR-005).
"""

from __future__ import annotations

import base64
import ssl
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr

from app.config import get_settings
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from honeycore.interfaces import InvalidSignatureError
from honeycore.pki import build_root_ca, generate_ec_key, issue_leaf
from honeycore.transport import ReplayCache, verify_signed_request

# ---------------------------------------------------------------------------
# Fixtures for signed & mtls transport tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def service_ca() -> dict[str, bytes]:
    """Module-scoped self-signed Service CA."""
    cert_pem, key_pem = build_root_ca("Test HoneyVault Service CA", 365)
    return {"cert_pem": cert_pem, "key_pem": key_pem}


@pytest.fixture(scope="module")
def api_client_cert(service_ca: dict[str, bytes]) -> dict[str, bytes]:
    """Client cert for 'honeyvault-api' signed by the Service CA with EKU clientAuth."""
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    cert_pem = issue_leaf(
        service_ca["cert_pem"],
        service_ca["key_pem"],
        "honeyvault-api",
        pub_pem,
        365,
        eku_client_auth=True,
    )
    key_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return {"cert_pem": cert_pem, "key_pem": key_pem}


@pytest.fixture
def replay_cache() -> ReplayCache:
    return ReplayCache(ttl_seconds=300)


# ---------------------------------------------------------------------------
# Existing Plain Mode Tests
# ---------------------------------------------------------------------------


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
        assert client.transport_mode == settings.honeychecker_transport
    finally:
        client.close()


# ---------------------------------------------------------------------------
# Signed Mode Tests (§10)
# ---------------------------------------------------------------------------


def _hv_headers(headers: httpx.Headers) -> dict[str, str]:
    """Extract headers mapping case-insensitively for verify_signed_request."""
    return {
        "X-HV-Cert": headers["X-HV-Cert"],
        "X-HV-Timestamp": headers["X-HV-Timestamp"],
        "X-HV-Nonce": headers["X-HV-Nonce"],
        "X-HV-Signature": headers["X-HV-Signature"],
    }


def test_signed_mode_register_headers_and_verification(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    replay_cache: ReplayCache,
) -> None:
    """MockTransport captures requests; headers are present and verify_signed_request accepts."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json={"status": "registered"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        transport_mode="signed",
        client_cert_pem=api_client_cert["cert_pem"],
        client_key_pem=api_client_cert["key_pem"],
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    client.register(user_id="user-signed-1", index=5)

    assert len(captured) == 1
    req = captured[0]

    # Verify headers exist
    assert "X-HV-Cert" in req.headers
    assert "X-HV-Timestamp" in req.headers
    assert "X-HV-Nonce" in req.headers
    assert "X-HV-Signature" in req.headers
    assert req.headers["Content-Type"] == "application/json"

    # Verify request body is JSON bytes
    assert b"user-signed-1" in req.content

    # verify_signed_request must accept the captured request
    cert_info = verify_signed_request(
        method=req.method,
        path=req.url.raw_path.decode("ascii"),
        body=req.content,
        headers=_hv_headers(req.headers),
        trusted_ca_pems=[service_ca["cert_pem"]],
        allowed_cn="honeyvault-api",
        replay_cache=replay_cache,
    )
    assert cert_info.subject_cn == "honeyvault-api"


def test_signed_mode_check_and_health_verification(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    replay_cache: ReplayCache,
) -> None:
    """Signed mode signs POST /hc/check and GET /hc/health successfully."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == "/hc/check":
            return httpx.Response(200, json={"match": True})
        if request.url.path == "/hc/health":
            return httpx.Response(200, json={"status": "ok", "db": "ok"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        transport_mode="signed",
        client_cert_pem=api_client_cert["cert_pem"],
        client_key_pem=api_client_cert["key_pem"],
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    # Check request
    match_result = client.check(user_id="user-check-1", index=2)
    assert match_result is True
    check_req = captured[-1]
    verify_signed_request(
        method=check_req.method,
        path=check_req.url.raw_path.decode("ascii"),
        body=check_req.content,
        headers=_hv_headers(check_req.headers),
        trusted_ca_pems=[service_ca["cert_pem"]],
        allowed_cn="honeyvault-api",
        replay_cache=replay_cache,
    )

    # Health request (empty body)
    health_result = client.health()
    assert health_result is True
    health_req = captured[-1]
    verify_signed_request(
        method=health_req.method,
        path=health_req.url.raw_path.decode("ascii"),
        body=health_req.content,
        headers=_hv_headers(health_req.headers),
        trusted_ca_pems=[service_ca["cert_pem"]],
        allowed_cn="honeyvault-api",
        replay_cache=replay_cache,
    )


def test_signed_mode_tampered_body_fails_verification(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    replay_cache: ReplayCache,
) -> None:
    """Changing the body after signing fails verification."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json={"status": "registered"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        transport_mode="signed",
        client_cert_pem=api_client_cert["cert_pem"],
        client_key_pem=api_client_cert["key_pem"],
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    client.register(user_id="user-tamper", index=1)
    req = captured[0]

    # Tampered body bytes
    tampered_body = req.content + b" tampered!"
    with pytest.raises(InvalidSignatureError, match="Signature verification failed"):
        verify_signed_request(
            method=req.method,
            path=req.url.raw_path.decode("ascii"),
            body=tampered_body,
            headers=_hv_headers(req.headers),
            trusted_ca_pems=[service_ca["cert_pem"]],
            allowed_cn="honeyvault-api",
            replay_cache=ReplayCache(),
        )

    # Tampered path fails
    with pytest.raises(InvalidSignatureError, match="Signature verification failed"):
        verify_signed_request(
            method=req.method,
            path="/hc/other-path",
            body=req.content,
            headers=_hv_headers(req.headers),
            trusted_ca_pems=[service_ca["cert_pem"]],
            allowed_cn="honeyvault-api",
            replay_cache=ReplayCache(),
        )

    # Tampered method fails
    with pytest.raises(InvalidSignatureError, match="Signature verification failed"):
        verify_signed_request(
            method="GET",
            path=req.url.raw_path.decode("ascii"),
            body=req.content,
            headers=_hv_headers(req.headers),
            trusted_ca_pems=[service_ca["cert_pem"]],
            allowed_cn="honeyvault-api",
            replay_cache=ReplayCache(),
        )


def test_signed_mode_loading_from_b64(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    replay_cache: ReplayCache,
) -> None:
    """Client loads cert and key from base64 strings."""
    cert_b64 = base64.b64encode(api_client_cert["cert_pem"]).decode("ascii")
    key_b64 = base64.b64encode(api_client_cert["key_pem"]).decode("ascii")

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json={"status": "registered"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        transport_mode="signed",
        client_cert_b64=cert_b64,
        client_key_b64=SecretStr(key_b64),
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    client.register(user_id="user-b64", index=9)
    req = captured[0]

    cert_info = verify_signed_request(
        method=req.method,
        path=req.url.raw_path.decode("ascii"),
        body=req.content,
        headers=_hv_headers(req.headers),
        trusted_ca_pems=[service_ca["cert_pem"]],
        allowed_cn="honeyvault-api",
        replay_cache=replay_cache,
    )
    assert cert_info.subject_cn == "honeyvault-api"


def test_signed_mode_loading_from_paths(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    replay_cache: ReplayCache,
    tmp_path: Path,
) -> None:
    """Client loads cert and key from file paths."""
    cert_file = tmp_path / "api-client.crt"
    key_file = tmp_path / "api-client.key"
    cert_file.write_bytes(api_client_cert["cert_pem"])
    key_file.write_bytes(api_client_cert["key_pem"])

    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(201, json={"status": "registered"})

    transport = httpx.MockTransport(handler)
    client = HoneycheckerClient(
        base_url="http://test-hc:8001",
        transport_mode="signed",
        client_cert_path=str(cert_file),
        client_key_path=str(key_file),
        client_factory=lambda: httpx.Client(transport=transport, base_url="http://test-hc:8001"),
    )

    client.register(user_id="user-path", index=8)
    req = captured[0]

    cert_info = verify_signed_request(
        method=req.method,
        path=req.url.raw_path.decode("ascii"),
        body=req.content,
        headers=_hv_headers(req.headers),
        trusted_ca_pems=[service_ca["cert_pem"]],
        allowed_cn="honeyvault-api",
        replay_cache=replay_cache,
    )
    assert cert_info.subject_cn == "honeyvault-api"


def test_signed_mode_misconfigurations_raise_runtime_error(
    api_client_cert: dict[str, bytes],
    tmp_path: Path,
) -> None:
    """Misconfiguration in signed mode raises clear RuntimeError at construction time."""
    # 1. Missing both cert and key
    with pytest.raises(RuntimeError, match="[Cc]lient cert"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_path=str(tmp_path / "nonexistent.crt"),
            client_key_path=str(tmp_path / "nonexistent.key"),
        )

    # 2. Invalid base64 in cert
    with pytest.raises(RuntimeError, match="decode failed"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_b64="!!!not-base-64!!!",
            client_key_pem=api_client_cert["key_pem"],
        )

    # 3. Invalid PEM content in cert
    with pytest.raises(RuntimeError, match="Invalid client certificate PEM"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_pem=b"not-a-valid-cert",
            client_key_pem=api_client_cert["key_pem"],
        )

    # 4. Missing private key
    with pytest.raises(RuntimeError, match="[Cc]lient.*key"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_pem=api_client_cert["cert_pem"],
            client_key_path=str(tmp_path / "nonexistent.key"),
        )

    # 5. Invalid PEM content in key
    with pytest.raises(RuntimeError, match="Invalid client private key PEM"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_pem=api_client_cert["cert_pem"],
            client_key_pem=b"not-a-valid-key",
        )

    # 6. Non-EC private key (e.g. RSA key)
    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_key_pem = rsa_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    with pytest.raises(RuntimeError, match="EC private key"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="signed",
            client_cert_pem=api_client_cert["cert_pem"],
            client_key_pem=rsa_key_pem,
        )


# ---------------------------------------------------------------------------
# mTLS Mode Tests (§10)
# ---------------------------------------------------------------------------


def test_mtls_kwargs_built_from_paths_no_network(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    tmp_path: Path,
) -> None:
    """mTLS kwargs built from paths without real network."""
    cert_file = tmp_path / "api-client.crt"
    key_file = tmp_path / "api-client.key"
    ca_file = tmp_path / "service-ca.crt"

    cert_file.write_bytes(api_client_cert["cert_pem"])
    key_file.write_bytes(api_client_cert["key_pem"])
    ca_file.write_bytes(service_ca["cert_pem"])

    client = HoneycheckerClient(
        base_url="https://honeychecker:8001",
        transport_mode="mtls",
        client_cert_path=str(cert_file),
        client_key_path=str(key_file),
        ca_cert_path=str(ca_file),
    )
    try:
        assert client.transport_mode == "mtls"
        assert "cert" in client._mtls_kwargs
        assert client._mtls_kwargs["cert"] == (str(cert_file), str(key_file))
        assert "verify" in client._mtls_kwargs
        assert isinstance(client._mtls_kwargs["verify"], ssl.SSLContext)
    finally:
        client.close()


def test_mtls_misconfigurations_raise_runtime_error(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    tmp_path: Path,
) -> None:
    """mTLS misconfiguration raises clear RuntimeError at construction time."""
    cert_file = tmp_path / "api-client.crt"
    key_file = tmp_path / "api-client.key"
    ca_file = tmp_path / "service-ca.crt"

    cert_file.write_bytes(api_client_cert["cert_pem"])
    key_file.write_bytes(api_client_cert["key_pem"])
    ca_file.write_bytes(service_ca["cert_pem"])

    # 1. Non-https base_url
    with pytest.raises(RuntimeError, match="https://"):
        HoneycheckerClient(
            base_url="http://honeychecker:8001",
            transport_mode="mtls",
            client_cert_path=str(cert_file),
            client_key_path=str(key_file),
            ca_cert_path=str(ca_file),
        )

    # 2. Missing client_cert_path
    with pytest.raises(RuntimeError, match="requires client_cert_path"):
        HoneycheckerClient(
            base_url="https://honeychecker:8001",
            transport_mode="mtls",
            client_cert_path=None,
            client_key_path=str(key_file),
            ca_cert_path=str(ca_file),
        )

    # 3. Nonexistent file
    with pytest.raises(RuntimeError, match="file not found"):
        HoneycheckerClient(
            base_url="https://honeychecker:8001",
            transport_mode="mtls",
            client_cert_path=str(tmp_path / "nonexistent.crt"),
            client_key_path=str(key_file),
            ca_cert_path=str(ca_file),
        )

    # 4. Corrupt CA file fails TLS context loading
    bad_ca = tmp_path / "bad-ca.crt"
    bad_ca.write_bytes(b"corrupted ca content")
    with pytest.raises(RuntimeError, match="Failed to configure mTLS transport"):
        HoneycheckerClient(
            base_url="https://honeychecker:8001",
            transport_mode="mtls",
            client_cert_path=str(cert_file),
            client_key_path=str(key_file),
            ca_cert_path=str(bad_ca),
        )


def test_unknown_transport_mode_raises_runtime_error() -> None:
    """Unknown transport mode raises clear RuntimeError at construction time."""
    with pytest.raises(RuntimeError, match="Unknown transport mode"):
        HoneycheckerClient(
            base_url="http://test-hc:8001",
            transport_mode="bogus",
        )


def test_get_honeychecker_client_modes(
    service_ca: dict[str, bytes],
    api_client_cert: dict[str, bytes],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_honeychecker_client builds client reflecting settings transport mode."""
    settings = get_settings()

    # Plain mode
    monkeypatch.setattr(settings, "honeychecker_transport", "plain")
    c_plain = get_honeychecker_client()
    try:
        assert c_plain.transport_mode == "plain"
    finally:
        c_plain.close()

    # Signed mode
    cert_b64 = base64.b64encode(api_client_cert["cert_pem"]).decode("ascii")
    key_b64 = base64.b64encode(api_client_cert["key_pem"]).decode("ascii")
    monkeypatch.setattr(settings, "honeychecker_transport", "signed")
    monkeypatch.setattr(settings, "hc_client_cert_b64", cert_b64)
    monkeypatch.setattr(settings, "hc_client_key_b64", SecretStr(key_b64))

    c_signed = get_honeychecker_client()
    try:
        assert c_signed.transport_mode == "signed"
    finally:
        c_signed.close()
