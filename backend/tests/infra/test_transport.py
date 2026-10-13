"""Tests for honeycore/transport.py (Phase 3 — T4).

Owner: T4 — Parth.

Certs are generated in-test with honeycore.pki helpers; nothing is written to disk.
"""

from __future__ import annotations

import time

import pytest
from cryptography.hazmat.primitives import serialization

from honeycore.interfaces import InvalidSignatureError
from honeycore.pki import build_issuing_ca, build_root_ca, generate_ec_key, issue_leaf
from honeycore.transport import (
    ReplayCache,
    canonical_request,
    httpx_client_kwargs,
    sign_request,
    verify_signed_request,
)

# ---------------------------------------------------------------------------
# Fixtures — shared CA hierarchy and client certs
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ca_hierarchy():
    """Module-scoped CA hierarchy: root + issuing."""
    root_cert_pem, root_key_pem = build_root_ca("Test Root CA", 365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem, root_key_pem, "Test Issuing CA", 365
    )
    return {
        "root_cert_pem": root_cert_pem,
        "issuing_cert_pem": issuing_cert_pem,
        "issuing_key_pem": issuing_key_pem,
        "trusted_cas": [root_cert_pem, issuing_cert_pem],
    }


@pytest.fixture(scope="module")
def api_client_cert(ca_hierarchy):
    """Client cert for 'honeyvault-api' with EKU clientAuth."""
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    cert_pem = issue_leaf(
        ca_hierarchy["issuing_cert_pem"],
        ca_hierarchy["issuing_key_pem"],
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


@pytest.fixture(scope="module")
def user_cert_no_client_auth(ca_hierarchy):
    """A user cert WITHOUT EKU clientAuth (issued by the same CA)."""
    priv = generate_ec_key()
    pub_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # issue_leaf defaults: eku_client_auth=False
    cert_pem = issue_leaf(
        ca_hierarchy["issuing_cert_pem"],
        ca_hierarchy["issuing_key_pem"],
        "no-client-auth-user",
        pub_pem,
        365,
        eku_client_auth=False,
    )
    key_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return {"cert_pem": cert_pem, "key_pem": key_pem}


@pytest.fixture
def replay_cache():
    return ReplayCache(ttl_seconds=300)


# ---------------------------------------------------------------------------
# Helper — sign and verify
# ---------------------------------------------------------------------------


def _do_sign_verify(
    method,
    path,
    body,
    cert_pem,
    key_pem,
    trusted_cas,
    allowed_cn,
    replay_cache,
    *,
    now=None,
):
    headers = sign_request(method, path, body, cert_pem, key_pem, now=now)
    return verify_signed_request(
        method,
        path,
        body,
        headers,
        trusted_cas,
        allowed_cn,
        replay_cache,
        now=now,
    )


# ---------------------------------------------------------------------------
# 1. canonical_request
# ---------------------------------------------------------------------------


def test_canonical_request_format():
    out = canonical_request("POST", "/hc/check?x=1", "1234567890", "abc123", b"body!")
    lines = out.decode("utf-8").splitlines()
    assert lines[0] == "POST"
    assert lines[1] == "/hc/check?x=1"
    assert lines[2] == "1234567890"
    assert lines[3] == "abc123"
    # last line = sha256hex of b"body!"
    import hashlib

    assert lines[4] == hashlib.sha256(b"body!").hexdigest()


def test_canonical_request_method_uppercased():
    out1 = canonical_request("post", "/path", "ts", "n", b"")
    out2 = canonical_request("POST", "/path", "ts", "n", b"")
    assert out1 == out2


# ---------------------------------------------------------------------------
# 2. Valid round-trip
# ---------------------------------------------------------------------------


def test_valid_signature_passes(api_client_cert, ca_hierarchy, replay_cache):
    cert_info = _do_sign_verify(
        "POST",
        "/hc/check",
        b'{"user_id":"u1","index":0}',
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        ca_hierarchy["trusted_cas"],
        "honeyvault-api",
        replay_cache,
        now=time.time(),
    )
    assert cert_info.subject_cn == "honeyvault-api"


# ---------------------------------------------------------------------------
# 3. Tampered body → signature mismatch
# ---------------------------------------------------------------------------


def test_tampered_body_fails(api_client_cert, ca_hierarchy, replay_cache):
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"original-body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    with pytest.raises(InvalidSignatureError):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"tampered-body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=now,
        )


# ---------------------------------------------------------------------------
# 4. Tampered path → signature mismatch
# ---------------------------------------------------------------------------


def test_tampered_path_fails(api_client_cert, ca_hierarchy, replay_cache):
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    with pytest.raises(InvalidSignatureError):
        verify_signed_request(
            "POST",
            "/hc/evil",  # different path
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=now,
        )


# ---------------------------------------------------------------------------
# 5. Tampered method → signature mismatch
# ---------------------------------------------------------------------------


def test_tampered_method_fails(api_client_cert, ca_hierarchy, replay_cache):
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    with pytest.raises(InvalidSignatureError):
        verify_signed_request(
            "GET",  # different method
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=now,
        )


# ---------------------------------------------------------------------------
# 6. Old timestamp (beyond max_skew)
# ---------------------------------------------------------------------------


def test_old_timestamp_fails(api_client_cert, ca_hierarchy, replay_cache):
    past = time.time() - 120  # 2 minutes ago
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=past,
    )
    with pytest.raises(InvalidSignatureError, match="Timestamp out of window"):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=time.time(),  # present time → skew > 60 s
        )


# ---------------------------------------------------------------------------
# 7. Replay — same nonce used twice
# ---------------------------------------------------------------------------


def test_replay_fails(api_client_cert, ca_hierarchy, replay_cache):
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    # First request succeeds
    verify_signed_request(
        "POST",
        "/hc/check",
        b"body",
        headers,
        ca_hierarchy["trusted_cas"],
        "honeyvault-api",
        replay_cache,
        now=now,
    )
    # Second request with same headers (replay) must fail
    with pytest.raises(InvalidSignatureError, match="replay"):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=now,
        )


# ---------------------------------------------------------------------------
# 8. Wrong CN
# ---------------------------------------------------------------------------


def test_wrong_cn_fails(api_client_cert, ca_hierarchy):
    replay = ReplayCache()
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    with pytest.raises(InvalidSignatureError):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "wrong-cn",  # cert CN is "honeyvault-api"
            replay,
            now=now,
        )


# ---------------------------------------------------------------------------
# 9. Cert without clientAuth EKU
# ---------------------------------------------------------------------------


def test_no_client_auth_eku_fails(user_cert_no_client_auth, ca_hierarchy):
    replay = ReplayCache()
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        user_cert_no_client_auth["cert_pem"],
        user_cert_no_client_auth["key_pem"],
        now=now,
    )
    with pytest.raises(InvalidSignatureError):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "no-client-auth-user",
            replay,
            now=now,
        )


# ---------------------------------------------------------------------------
# 10. ReplayCache TTL pruning
# ---------------------------------------------------------------------------


def test_replay_cache_ttl_prune():
    cache = ReplayCache(ttl_seconds=1)
    now = 1_000_000.0
    # Add nonce at t=now
    assert cache.seen_or_add("nonce-a", now=now) is False
    # Same nonce within TTL → replay
    assert cache.seen_or_add("nonce-a", now=now + 0.5) is True
    # After TTL expires, the nonce is pruned and can be added again
    assert cache.seen_or_add("nonce-a", now=now + 2.0) is False


# ---------------------------------------------------------------------------
# 11. httpx_client_kwargs modes
# ---------------------------------------------------------------------------


def test_httpx_kwargs_plain():
    assert httpx_client_kwargs("plain") == {}


def test_httpx_kwargs_signed():
    assert httpx_client_kwargs("signed") == {}


def test_httpx_kwargs_unknown_mode():
    with pytest.raises(ValueError, match="Unknown transport mode"):
        httpx_client_kwargs("ftp")


def test_httpx_kwargs_mtls_missing_paths():
    with pytest.raises(ValueError, match="mtls mode requires"):
        httpx_client_kwargs("mtls")


# ---------------------------------------------------------------------------
# 12. Missing header
# ---------------------------------------------------------------------------


def test_missing_header_fails(api_client_cert, ca_hierarchy, replay_cache):
    now = time.time()
    headers = sign_request(
        "POST",
        "/hc/check",
        b"body",
        api_client_cert["cert_pem"],
        api_client_cert["key_pem"],
        now=now,
    )
    # Remove one required header
    del headers["X-HV-Nonce"]
    with pytest.raises(InvalidSignatureError, match="Missing header"):
        verify_signed_request(
            "POST",
            "/hc/check",
            b"body",
            headers,
            ca_hierarchy["trusted_cas"],
            "honeyvault-api",
            replay_cache,
            now=now,
        )
