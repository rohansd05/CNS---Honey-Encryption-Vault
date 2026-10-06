"""Tests for secure entry sharing endpoints and cryptographic invariants.

Owner: T2 — Rohan. Contract: docs/api-contract.md §5, PROJECT-BRIEF.md §9.
"""

from __future__ import annotations

import base64
import datetime
import secrets
import uuid
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.core import Share, User
from app.rate_limit import limiter
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.identity_service import pki_configured
from honeycore.pki import PKI, build_issuing_ca, build_root_ca
from honeycore.sharing import Sharing


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


def _register_and_login(client: TestClient, username: str, master_pw: str) -> dict[str, str]:
    login_pw = "ValidLoginPass123!"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": master_pw,
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "login_password": login_pw},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_share_alice_to_bob_round_trip(
    client: TestClient,
    pki_test_env: dict[str, Any],
) -> None:
    """Alice shares an entry with Bob; Bob opens and decrypts the exact entry."""
    alice_master = "AliceMasterPass123!"  # noqa: S105
    bob_master = "BobMasterPass456@"  # noqa: S105

    alice_headers = _register_and_login(client, "alice", alice_master)
    bob_headers = _register_and_login(client, "bob", bob_master)

    # Alice adds an entry to her vault
    add_resp = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "github.com",
            "username": "alice_gh",
            "password": "AliceSecretPassword123!",
        },
        headers=alice_headers,
    )
    assert add_resp.status_code == 201
    entry_id = add_resp.json()["id"]

    # Alice shares the entry with Bob
    share_resp = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": entry_id,
            "recipient_username": "bob",
        },
        headers=alice_headers,
    )
    assert share_resp.status_code == 201
    share_id = share_resp.json()["share_id"]

    # Verify Alice's sent shares
    sent_resp = client.get("/api/shares/sent", headers=alice_headers)
    assert sent_resp.status_code == 200
    sent_items = sent_resp.json()
    assert len(sent_items) == 1
    assert sent_items[0]["share_id"] == share_id
    assert sent_items[0]["recipient"] == "bob"
    assert sent_items[0]["service"] == "github.com"
    assert sent_items[0]["opened_at"] is None

    # Verify Bob's inbox
    inbox_resp = client.get("/api/shares/inbox", headers=bob_headers)
    assert inbox_resp.status_code == 200
    inbox_items = inbox_resp.json()
    assert len(inbox_items) == 1
    assert inbox_items[0]["share_id"] == share_id
    assert inbox_items[0]["sender"] == "alice"
    assert inbox_items[0]["service"] == "github.com"
    assert inbox_items[0]["opened_at"] is None

    # Bob opens the share
    open_resp = client.post(f"/api/shares/{share_id}/open", headers=bob_headers)
    assert open_resp.status_code == 200
    open_data = open_resp.json()
    assert open_data["service"] == "github.com"
    assert open_data["username"] == "alice_gh"
    assert open_data["password"] == "AliceSecretPassword123!"  # noqa: S105
    assert open_data["sender"] == "alice"
    assert open_data["signature_valid"] is True
    assert open_data["certificate_valid"] is True
    assert open_data["certificate_subject"] == "CN=alice"
    assert open_data["certificate_issuer"] == "CN=HoneyVault Issuing CA"

    # Verify opened_at is now populated in Bob's inbox
    inbox_resp2 = client.get("/api/shares/inbox", headers=bob_headers)
    assert inbox_resp2.status_code == 200
    assert inbox_resp2.json()[0]["opened_at"] is not None


def test_sender_cannot_open_share_returns_404(
    client: TestClient,
    pki_test_env: dict[str, Any],
) -> None:
    """Only the intended recipient can open a share; sender or third party gets 404."""
    alice_master = "AliceMasterPass123!"  # noqa: S105
    bob_master = "BobMasterPass456@"  # noqa: S105
    charlie_master = "CharlieMasterPass789#"  # noqa: S105

    alice_headers = _register_and_login(client, "alice2", alice_master)
    _register_and_login(client, "bob2", bob_master)
    charlie_headers = _register_and_login(client, "charlie2", charlie_master)

    add_resp = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "gitlab.com",
            "username": "alice_gl",
            "password": "GlPassword123!",
        },
        headers=alice_headers,
    )
    entry_id = add_resp.json()["id"]

    share_resp = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": entry_id,
            "recipient_username": "bob2",
        },
        headers=alice_headers,
    )
    share_id = share_resp.json()["share_id"]

    # Alice (sender) tries to open
    resp_alice = client.post(f"/api/shares/{share_id}/open", headers=alice_headers)
    assert resp_alice.status_code == 404
    assert resp_alice.json()["detail"] == "Share not found"

    # Charlie (third party) tries to open
    resp_charlie = client.post(f"/api/shares/{share_id}/open", headers=charlie_headers)
    assert resp_charlie.status_code == 404
    assert resp_charlie.json()["detail"] == "Share not found"


def test_tampered_share_envelope_signature_valid_false(
    client: TestClient,
    pki_test_env: dict[str, Any],
) -> None:
    """Tampering with the stored share ciphertext results in signature_valid false."""
    alice_master = "AliceMasterPass123!"  # noqa: S105
    bob_master = "BobMasterPass456@"  # noqa: S105

    alice_headers = _register_and_login(client, "alice3", alice_master)
    bob_headers = _register_and_login(client, "bob3", bob_master)

    add_resp = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "aws.amazon.com",
            "username": "alice_aws",
            "password": "AwsPassword123!",
        },
        headers=alice_headers,
    )
    entry_id = add_resp.json()["id"]

    share_resp = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": entry_id,
            "recipient_username": "bob3",
        },
        headers=alice_headers,
    )
    share_id = share_resp.json()["share_id"]

    # Tamper with the share envelope ciphertext via demo endpoint
    tamper_resp = client.post(f"/api/shares/{share_id}/tamper", headers=alice_headers)
    assert tamper_resp.status_code == 200
    assert tamper_resp.json() == {"tampered": True}

    # Bob opens the tampered share
    open_resp = client.post(f"/api/shares/{share_id}/open", headers=bob_headers)
    assert open_resp.status_code == 200
    open_data = open_resp.json()
    assert open_data["signature_valid"] is False
    assert open_data["certificate_valid"] is True
    assert open_data["username"] is None
    assert open_data["password"] is None
    assert open_data["service"] == "aws.amazon.com"
    assert open_data["sender"] == "alice3"


def test_sender_cert_from_another_ca_certificate_valid_false(
    client: TestClient,
    db_session: Session,
    pki_test_env: dict[str, Any],
) -> None:
    """When a share is signed by a certificate from an untrusted CA, certificate_valid is false."""
    alice_master = "AliceMasterPass123!"  # noqa: S105
    bob_master = "BobMasterPass456@"  # noqa: S105

    _register_and_login(client, "alice4", alice_master)
    bob_headers = _register_and_login(client, "bob4", bob_master)

    alice_user = db_session.query(User).filter(User.username == "alice4").one()
    bob_user = db_session.query(User).filter(User.username == "bob4").one()

    # Generate an independent untrusted CA hierarchy
    rogue_root_cert, rogue_root_key = build_root_ca(cn="Rogue Root CA", days=365)
    rogue_issuing_cert, rogue_issuing_key = build_issuing_ca(
        rogue_root_cert, rogue_root_key, cn="Rogue Issuing CA", days=365
    )

    sharing = Sharing()
    pki = PKI()
    rogue_keys = sharing.generate_identity()
    rogue_cert = pki.issue_user_certificate(
        username="alice4",
        public_pem=rogue_keys.public_pem,
        issuer_cert_pem=rogue_issuing_cert,
        issuer_key_pem=rogue_issuing_key,
        days=365,
    )

    share_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.UTC)
    aad = {
        "sender": "alice4",
        "recipient": "bob4",
        "service": "rogue-service.com",
        "share_id": share_id,
        "created_at": now.isoformat(),
    }
    dummy_seed = secrets.token_bytes(532)

    envelope = sharing.seal_share(
        seed=dummy_seed,
        aad=aad,
        recipient_public_pem=bob_user.identity_public_pem.encode("utf-8"),
        sender_private_pem=rogue_keys.private_pem,
        sender_cert_pem=rogue_cert,
    )

    rogue_share = Share(
        id=share_id,
        sender_id=alice_user.id,
        recipient_id=bob_user.id,
        service="rogue-service.com",
        envelope=envelope,
        created_at=now,
    )
    db_session.add(rogue_share)
    db_session.commit()

    open_resp = client.post(f"/api/shares/{share_id}/open", headers=bob_headers)
    assert open_resp.status_code == 200
    open_data = open_resp.json()
    assert open_data["certificate_valid"] is False
    assert open_data["signature_valid"] is True
    assert open_data["username"] is None
    assert open_data["password"] is None
    assert open_data["certificate_issuer"] == "CN=Rogue Issuing CA"


def test_no_pki_configured_sharing_returns_503(
    client: TestClient,
    no_pki_env: None,
) -> None:
    """When PKI is not configured, POST /api/shares returns 503."""
    assert pki_configured() is False
    alice_master = "AliceMasterPass123!"  # noqa: S105
    alice_headers = _register_and_login(client, "alice_nopki", alice_master)

    resp = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": str(uuid.uuid4()),
            "recipient_username": "bob_nopki",
        },
        headers=alice_headers,
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Sharing unavailable: PKI not configured"


def test_wrong_master_password_shares_plausible_decoy_honey_encryption_property(
    client: TestClient,
    pki_test_env: dict[str, Any],
) -> None:
    """A wrong master password on share produces a valid share of a decoy entry (HE property)."""
    alice_master = "RealAliceMasterPass123!"  # noqa: S105
    wrong_master = "WrongMasterPass999!"  # noqa: S105
    bob_master = "BobMasterPass456@"  # noqa: S105

    alice_headers = _register_and_login(client, "alice_he", alice_master)
    bob_headers = _register_and_login(client, "bob_he", bob_master)

    # Alice adds real entry
    add_resp = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "protonmail.com",
            "username": "real_alice_user",
            "password": "RealSecretPassword456!",
        },
        headers=alice_headers,
    )
    entry_id = add_resp.json()["id"]

    # Alice shares using a WRONG master password -> 201 created, no error
    share_resp = client.post(
        "/api/shares",
        json={
            "master_password": wrong_master,
            "entry_id": entry_id,
            "recipient_username": "bob_he",
        },
        headers=alice_headers,
    )
    assert share_resp.status_code == 201
    share_id = share_resp.json()["share_id"]

    # Bob opens the share -> successfully decrypts and decodes, but gets decoy credentials
    open_resp = client.post(f"/api/shares/{share_id}/open", headers=bob_headers)
    assert open_resp.status_code == 200
    open_data = open_resp.json()
    assert open_data["signature_valid"] is True
    assert open_data["certificate_valid"] is True
    assert open_data["service"] == "protonmail.com"
    # Decoded decoy password differs from the real secret password
    assert open_data["password"] != "RealSecretPassword456!"  # noqa: S105
    assert open_data["username"] is not None
    assert len(open_data["username"]) > 0


def test_share_validation_errors(
    client: TestClient,
    pki_test_env: dict[str, Any],
) -> None:
    """Validation errors: cannot share with self, unknown recipient, unknown entry."""
    alice_master = "AliceMasterPass123!"  # noqa: S105
    alice_headers = _register_and_login(client, "alice_err", alice_master)

    # 1. Share with self -> 422
    resp_self = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": str(uuid.uuid4()),
            "recipient_username": "alice_err",
        },
        headers=alice_headers,
    )
    assert resp_self.status_code == 422
    assert resp_self.json()["detail"] == "Cannot share with yourself"

    # 2. Unknown recipient -> 404
    resp_unk_user = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": str(uuid.uuid4()),
            "recipient_username": "non_existent_recipient",
        },
        headers=alice_headers,
    )
    assert resp_unk_user.status_code == 404
    assert resp_unk_user.json()["detail"] == "User not found"

    # 3. Known recipient but unknown entry -> 404
    bob_master = "BobMasterPass456@"  # noqa: S105
    _register_and_login(client, "bob_err", bob_master)
    resp_unk_entry = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": str(uuid.uuid4()),
            "recipient_username": "bob_err",
        },
        headers=alice_headers,
    )
    assert resp_unk_entry.status_code == 404
    assert resp_unk_entry.json()["detail"] == "Entry not found"
