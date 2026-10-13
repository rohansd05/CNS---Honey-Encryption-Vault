"""Tests for identity provisioning, PKI integration, and /api/users/{username}/identity.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §9, §10, ADR-006).
"""

from __future__ import annotations

import base64
import secrets
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_honeycore
from app.models.core import User
from app.rate_limit import limiter
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.identity_service import (
    load_private_key,
    pki_configured,
    trusted_ca_pems,
)
from app.services.registration import register_user
from honeycore.pki import PKI, build_issuing_ca, build_root_ca


class FakeHoneycheckerClient(HoneycheckerClient):
    """In-memory honeychecker client store for integration testing."""

    def __init__(self, is_down: bool = False) -> None:
        self.indices: dict[str, int] = {}
        self.is_down = is_down

    def register(self, user_id: str, index: int) -> None:
        if self.is_down:
            raise HoneycheckerUnavailable("Fake honeychecker unavailable")
        self.indices[user_id] = index

    def check(self, user_id: str, index: int) -> bool:
        if self.is_down:
            raise HoneycheckerUnavailable("Fake honeychecker unavailable")
        real = self.indices.get(user_id)
        if real is None:
            return False
        return real == index

    def health(self) -> bool:
        if self.is_down:
            raise HoneycheckerUnavailable("Fake honeychecker unavailable")
        return True


@pytest.fixture
def fake_hc() -> FakeHoneycheckerClient:
    return FakeHoneycheckerClient()


@pytest.fixture(autouse=True)
def override_honeychecker(
    client: TestClient, fake_hc: FakeHoneycheckerClient
) -> Generator[None, None, None]:
    limiter.reset()
    client.app.dependency_overrides[get_honeychecker_client] = lambda: fake_hc
    yield
    client.app.dependency_overrides.pop(get_honeychecker_client, None)
    limiter.reset()


@pytest.fixture
def pki_test_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Generate in-test Root CA + Issuing CA and inject into Settings."""
    root_cert_pem, root_key_pem = build_root_ca(cn="HoneyVault Root CA", days=365)
    issuing_cert_pem, issuing_key_pem = build_issuing_ca(
        root_cert_pem=root_cert_pem,
        root_key_pem=root_key_pem,
        cn="HoneyVault Issuing CA",
        days=365,
    )
    raw_kek = secrets.token_bytes(32)
    key_wrap_b64 = base64.b64encode(raw_kek).decode("ascii")
    root_ca_b64 = base64.b64encode(root_cert_pem).decode("ascii")
    issuing_ca_cert_b64 = base64.b64encode(issuing_cert_pem).decode("ascii")
    issuing_ca_key_b64 = base64.b64encode(issuing_key_pem).decode("ascii")

    settings = get_settings()
    monkeypatch.setattr(settings, "key_wrap_secret", SecretStr(key_wrap_b64))
    monkeypatch.setattr(settings, "root_ca_cert_b64", root_ca_b64)
    monkeypatch.setattr(settings, "issuing_ca_cert_b64", issuing_ca_cert_b64)
    monkeypatch.setattr(settings, "issuing_ca_key_b64", SecretStr(issuing_ca_key_b64))

    return {
        "root_cert_pem": root_cert_pem,
        "root_key_pem": root_key_pem,
        "issuing_cert_pem": issuing_cert_pem,
        "issuing_key_pem": issuing_key_pem,
        "raw_kek": raw_kek,
    }


@pytest.fixture
def no_pki_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicitly clear PKI settings."""
    settings = get_settings()
    monkeypatch.setattr(settings, "key_wrap_secret", SecretStr(""))
    monkeypatch.setattr(settings, "root_ca_cert_b64", "")
    monkeypatch.setattr(settings, "issuing_ca_cert_b64", "")
    monkeypatch.setattr(settings, "issuing_ca_key_b64", SecretStr(""))


def test_registration_with_pki_stores_identity(
    client: TestClient,
    db_session: Session,
    pki_test_env: dict[str, Any],
) -> None:
    """When PKI is configured, registration provisions keys and a verified cert."""
    assert pki_configured() is True
    username = f"pki_user_{uuid.uuid4().hex[:8]}"
    login_pw = "ValidLoginPass123!"
    master_pw = "ValidMasterPass456@"

    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": master_pw,
        },
    )
    assert resp.status_code == 201

    user = db_session.scalar(select(User).where(User.username == username))
    assert user is not None
    assert user.identity_public_pem is not None
    assert user.identity_private_wrapped is not None
    assert user.identity_cert_pem is not None

    # Cert verifies against the CAs with CN=username
    pki = PKI()
    cas = trusted_ca_pems()
    cert_info = pki.verify_certificate(
        user.identity_cert_pem.encode("utf-8"),
        cas,
        expected_cn=username,
    )
    assert cert_info.subject_cn == username
    assert cert_info.issuer_cn == "HoneyVault Issuing CA"

    # The unwrapped private key matches the public key
    unwrapped_pem = load_private_key(user)
    priv_key = serialization.load_pem_private_key(unwrapped_pem, password=None)
    pub_pem = (
        priv_key.public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    assert pub_pem == user.identity_public_pem


def test_get_identity_endpoint_success(
    client: TestClient,
    db_session: Session,
    pki_test_env: dict[str, Any],
    auth_headers: Any,
) -> None:
    """GET /api/users/{username}/identity returns 200 with public key and cert."""
    username = f"alice_{uuid.uuid4().hex[:8]}"
    login_pw = "ValidLoginPass123!"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": "ValidMasterPass456@",
        },
    )

    user = db_session.scalar(select(User).where(User.username == username))
    assert user is not None
    headers = auth_headers(user)

    resp = client.get(f"/api/users/{username}/identity", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == username
    assert "-----BEGIN PUBLIC KEY-----" in data["public_key_pem"]
    assert "-----BEGIN CERTIFICATE-----" in data["certificate_pem"]


def test_registration_without_pki_works_and_identity_returns_409(
    client: TestClient,
    db_session: Session,
    no_pki_env: None,
    auth_headers: Any,
) -> None:
    """Without PKI config, registration succeeds but identity endpoint returns 409."""
    assert pki_configured() is False
    username = f"bob_{uuid.uuid4().hex[:8]}"
    login_pw = "ValidLoginPass123!"

    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": "ValidMasterPass456@",
        },
    )
    assert resp.status_code == 201

    user = db_session.scalar(select(User).where(User.username == username))
    assert user is not None
    assert user.identity_public_pem is None
    assert user.identity_private_wrapped is None
    assert user.identity_cert_pem is None

    headers = auth_headers(user)

    id_resp = client.get(f"/api/users/{username}/identity", headers=headers)
    assert id_resp.status_code == 409
    assert id_resp.json()["detail"] == "User has no identity keys"


def test_get_identity_unknown_user_returns_404(
    client: TestClient,
    make_user: Any,
    auth_headers: Any,
    pki_test_env: dict[str, Any],
) -> None:
    """GET /api/users/{username}/identity for non-existent user returns 404."""
    caller = make_user("caller")
    headers = auth_headers(caller)

    resp = client.get("/api/users/unknown_user_xyz/identity", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "User not found"


def test_get_identity_requires_auth(client: TestClient) -> None:
    """GET /api/users/{username}/identity without auth returns 401."""
    resp = client.get("/api/users/any_user/identity")
    assert resp.status_code == 401


def test_capture_sweetwords_returns_k_sweetwords(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """capture_sweetwords=True returns k distinct sweetwords containing real password."""
    honeycore = get_honeycore()
    login_pw = "RealPassword123!"
    username = f"sw_{uuid.uuid4().hex[:8]}"

    # With capture_sweetwords=True
    result = register_user(
        db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        username=username,
        login_password=login_pw,
        master_password="MasterSecretPassword123!",  # noqa: S106
        capture_sweetwords=True,
    )
    assert result.user is not None
    assert result.sweetwords is not None
    assert len(result.sweetwords) == get_settings().honeywords_k
    assert login_pw in result.sweetwords
    assert len(set(result.sweetwords)) == len(result.sweetwords)

    # With capture_sweetwords=False
    username_nocap = f"sw_nocap_{uuid.uuid4().hex[:8]}"
    result_nocap = register_user(
        db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        username=username_nocap,
        login_password=login_pw,
        master_password="MasterSecretPassword123!",  # noqa: S106
        capture_sweetwords=False,
    )
    assert result_nocap.user is not None
    assert result_nocap.sweetwords is None


def test_identity_service_helpers_without_config(no_pki_env: None) -> None:
    """Helper errors when PKI is not configured or user has no wrapped key."""
    assert pki_configured() is False

    dummy_user = User(username="dummy", hw_salt="s", hw_hashes=[], hw_kdf_profile="demo")
    with pytest.raises(ValueError, match="User has no identity private key"):
        load_private_key(dummy_user)

    with pytest.raises(ValueError, match="not configured"):
        trusted_ca_pems()
