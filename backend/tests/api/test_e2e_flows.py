"""End-to-end API tests for HoneyVault demo and convergence flows.

Owner: T2 / M5.
Contract: docs/api-contract.md, PROJECT-ROADMAP.md §8.

Flows covered:
1. Registration and vault lifecycle (reject identical passwords, add 5 entries,
   unlock real vault + sigil)
2. Wrong-master honey vault (200, decoy entries, distinct sigil, identical shape,
   no oracle error)
3. Decoy sweetword and intrusion alert (401 identical response, HONEYWORD_LOGIN alert
   recorded in admin)
4. Sharing and tamper detection (Alice shares with Bob, open verified;
   tampered envelope rejects signature)
5. Honeychecker unavailable (login fails closed with 503)
6. Evaluation summary (GET /api/eval/summary returns 200 with metrics schema)
"""

from __future__ import annotations

import base64
import json
import secrets
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_honeycore
from app.models.core import Alert, User
from app.rate_limit import limiter
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.honeywords import HoneywordRecord, generate_sweetwords, hash_sweetword
from honeycore.pki import build_issuing_ca, build_root_ca


class FakeHoneycheckerClient(HoneycheckerClient):
    """In-memory honeychecker client store for end-to-end flow tests."""

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
    """Fixture providing an isolated in-memory honeychecker client."""
    return FakeHoneycheckerClient()


@pytest.fixture(autouse=True)
def override_honeychecker(
    client: TestClient, fake_hc: FakeHoneycheckerClient
) -> Generator[None, None, None]:
    """Inject the fake honeychecker client and reset rate limits between tests."""
    limiter.reset()
    client.app.dependency_overrides[get_honeychecker_client] = lambda: fake_hc
    yield
    client.app.dependency_overrides.pop(get_honeychecker_client, None)
    limiter.reset()


@pytest.fixture
def pki_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Provision ephemeral in-memory Root and Issuing CA credentials for sharing tests."""
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


def _register_user(client: TestClient, username: str, login_pw: str, master_pw: str) -> str:
    """Register a user and return the assigned user_id."""
    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": master_pw,
        },
    )
    assert resp.status_code == 201, f"Registration failed: {resp.text}"
    return resp.json()["id"]


def _login_user(client: TestClient, username: str, login_pw: str) -> str:
    """Log in and return the JWT bearer access token."""
    resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "login_password": login_pw,
        },
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


def test_registration_and_vault_lifecycle(client: TestClient) -> None:
    """Flow 1: Registration and vault lifecycle.

    - Rejects equal login and master passwords with HTTP 422.
    - Registers a user, logs in, creates 5 vault entries.
    - Unlocks with the correct master password and validates entries + visual sigil.
    """
    username = f"flow1_{uuid.uuid4().hex[:8]}"
    identical_pw = "SamePassword123!"

    # 1. Registration with identical login and master passwords returns HTTP 422
    rej_resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": identical_pw,
            "master_password": identical_pw,
        },
    )
    assert rej_resp.status_code == 422
    assert rej_resp.json()["detail"] == "Login password and master password must differ"

    # 2. Register with distinct credentials
    login_pw = "LoginSecret123!"
    master_pw = "CorrectHorseBatteryStaple456@"
    user_id = _register_user(client, username, login_pw, master_pw)
    assert user_id is not None

    # 3. Log in and get access token
    token = _login_user(client, username, login_pw)
    auth_header = {"Authorization": f"Bearer {token}"}

    # 4. Create 5 distinct vault entries
    sample_entries = [
        {"service": f"service-{i}.com", "username": f"user_{i}", "password": f"Pass_{i}_Secret!"}
        for i in range(1, 6)
    ]
    created_ids: list[str] = []
    for item in sample_entries:
        res = client.post(
            "/api/vault/entries",
            headers=auth_header,
            json={"master_password": master_pw, **item},
        )
        assert res.status_code == 201, f"Failed adding entry {item['service']}: {res.text}"
        created_ids.append(res.json()["id"])
    assert len(created_ids) == 5

    # Check /api/auth/me reports entry_count == 5
    me_resp = client.get("/api/auth/me", headers=auth_header)
    assert me_resp.status_code == 200
    assert me_resp.json()["entry_count"] == 5

    # 5. Unlock with correct master password
    unlock_resp = client.post(
        "/api/vault/unlock",
        headers=auth_header,
        json={"master_password": master_pw},
    )
    assert unlock_resp.status_code == 200
    vault_payload = unlock_resp.json()

    assert "entries" in vault_payload
    assert "sigil" in vault_payload
    assert len(vault_payload["entries"]) == 5

    # Assert returned entries match the inserted real entries in order
    for idx, orig in enumerate(sample_entries):
        entry = vault_payload["entries"][idx]
        assert entry["id"] == created_ids[idx]
        assert entry["service"] == orig["service"]
        assert entry["username"] == orig["username"]
        assert entry["password"] == orig["password"]

    # Assert sigil format
    sigil = vault_payload["sigil"]
    assert isinstance(sigil.get("emojis"), list)
    assert len(sigil["emojis"]) == 3
    assert isinstance(sigil.get("color"), str)
    assert sigil["color"].startswith("#")


def test_wrong_master_honey_vault(client: TestClient) -> None:
    """Flow 2: Wrong-master honey vault indistinguishability.

    - Unlock with an incorrect master password.
    - Assert HTTP 200, identical response schema, 5 plausible decoy entries, distinct sigil.
    - Assert no error indicator or oracle leak.
    """
    username = f"flow2_{uuid.uuid4().hex[:8]}"
    login_pw = "LoginSecret123!"
    correct_master = "RealMasterPassword123!"
    wrong_master = "IncorrectMasterGuess456!"

    _register_user(client, username, login_pw, correct_master)
    token = _login_user(client, username, login_pw)
    auth_header = {"Authorization": f"Bearer {token}"}

    sample_entries = [
        {"service": f"site-{i}.org", "username": f"user_real_{i}", "password": f"RealPass_{i}!"}
        for i in range(1, 6)
    ]
    for item in sample_entries:
        res = client.post(
            "/api/vault/entries",
            headers=auth_header,
            json={"master_password": correct_master, **item},
        )
        assert res.status_code == 201

    # First unlock with correct master password to capture baseline
    correct_resp = client.post(
        "/api/vault/unlock",
        headers=auth_header,
        json={"master_password": correct_master},
    )
    assert correct_resp.status_code == 200
    real_data = correct_resp.json()

    # Now unlock with wrong master password
    wrong_resp = client.post(
        "/api/vault/unlock",
        headers=auth_header,
        json={"master_password": wrong_master},
    )
    # Crypto invariant: Wrong password must return 200 without error indication
    assert wrong_resp.status_code == 200
    decoy_data = wrong_resp.json()

    # Response shape matches exactly
    assert set(decoy_data.keys()) == {"entries", "sigil"}
    assert "error" not in decoy_data
    assert "detail" not in decoy_data

    decoy_entries = decoy_data["entries"]
    assert len(decoy_entries) == 5

    for idx, decoy in enumerate(decoy_entries):
        # Entry keys must match
        assert set(decoy.keys()) == {
            "id",
            "service",
            "username",
            "password",
            "created_at",
            "updated_at",
        }
        # Service is public metadata (ADR-001) so it matches
        assert decoy["service"] == sample_entries[idx]["service"]
        # Decrypted contents must differ from the real entries (plausible decoy)
        assert decoy["username"] != sample_entries[idx]["username"]
        assert decoy["password"] != sample_entries[idx]["password"]
        # Decoy fields must be non-empty printable strings
        assert isinstance(decoy["username"], str) and len(decoy["username"]) > 0
        assert isinstance(decoy["password"], str) and len(decoy["password"]) > 0

    # Decoy visual sigil must differ from the correct sigil
    assert decoy_data["sigil"] != real_data["sigil"]
    assert len(decoy_data["sigil"]["emojis"]) == 3
    assert decoy_data["sigil"]["color"].startswith("#")


def test_decoy_sweetword_and_intrusion_alert(
    client: TestClient, db_session: Session, fake_hc: FakeHoneycheckerClient
) -> None:
    """Flow 3: Decoy sweetword login and intrusion alert.

    - Attempt login with a generated decoy sweetword.
    - Assert HTTP 401 and identical response body to regular invalid login.
    - Query /api/admin/alerts with an admin token and verify the HONEYWORD_LOGIN alert is recorded.
    """
    honeycore = get_honeycore()
    real_login_pw = "RealUserLoginPass123!"
    salt = secrets.token_bytes(16)
    k = 10
    sweetwords, real_index = generate_sweetwords(real_login_pw, k, honeycore.password_model)

    # Pick a decoy index != real_index
    decoy_index = (real_index + 1) % len(sweetwords)
    decoy_login_pw = sweetwords[decoy_index]
    assert decoy_login_pw != real_login_pw

    hashes = [hash_sweetword(sw, salt, "demo") for sw in sweetwords]
    salt_b64 = base64.b64encode(salt).decode("ascii")
    record = HoneywordRecord(salt_b64=salt_b64, hashes=hashes, kdf_profile="demo")

    victim_username = f"victim_{uuid.uuid4().hex[:8]}"
    victim_user = User(
        username=victim_username,
        is_admin=False,
        hw_salt=record.salt_b64,
        hw_hashes=record.hashes,
        hw_kdf_profile=record.kdf_profile,
    )
    db_session.add(victim_user)
    db_session.flush()

    # Register the real index in the honeychecker
    fake_hc.indices[victim_user.id] = real_index

    # 1. Attempt login with the decoy sweetword
    decoy_login_resp = client.post(
        "/api/auth/login",
        json={
            "username": victim_username,
            "login_password": decoy_login_pw,
        },
        headers={"User-Agent": "AttackerConsole/1.0"},
    )
    assert decoy_login_resp.status_code == 401
    assert decoy_login_resp.json() == {"detail": "Invalid credentials"}

    # Compare with standard wrong password login on an ordinary user
    regular_username = f"regular_{uuid.uuid4().hex[:8]}"
    _register_user(client, regular_username, "NormalLogin123!", "NormalMaster456@")
    wrong_login_resp = client.post(
        "/api/auth/login",
        json={
            "username": regular_username,
            "login_password": "CompletelyRandomWrongPass999!",
        },
    )
    assert wrong_login_resp.status_code == 401
    assert wrong_login_resp.json() == decoy_login_resp.json()

    # 2. Verify alert directly in database
    alert_rows = list(
        db_session.scalars(select(Alert).where(Alert.username == victim_username)).all()
    )
    assert len(alert_rows) == 1
    alert = alert_rows[0]
    assert alert.kind == "HONEYWORD_LOGIN"
    assert alert.severity == "critical"
    assert alert.sweetword_index == decoy_index

    # 3. Create an admin user, login, and verify alert is visible via GET /api/admin/alerts
    admin_username = f"admin_{uuid.uuid4().hex[:8]}"
    admin_pw = "AdminLoginPassword123!"
    admin_salt = secrets.token_bytes(16)
    admin_sweetwords, admin_real_idx = generate_sweetwords(admin_pw, k, honeycore.password_model)
    admin_hashes = [hash_sweetword(sw, admin_salt, "demo") for sw in admin_sweetwords]
    admin_user = User(
        username=admin_username,
        is_admin=True,
        hw_salt=base64.b64encode(admin_salt).decode("ascii"),
        hw_hashes=admin_hashes,
        hw_kdf_profile="demo",
    )
    db_session.add(admin_user)
    db_session.flush()
    fake_hc.indices[admin_user.id] = admin_real_idx

    admin_token = _login_user(client, admin_username, admin_pw)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    alerts_resp = client.get("/api/admin/alerts", headers=admin_headers)
    assert alerts_resp.status_code == 200
    alert_items = alerts_resp.json()
    matching = [
        item
        for item in alert_items
        if item.get("username") == victim_username and item.get("kind") == "HONEYWORD_LOGIN"
    ]
    assert len(matching) == 1
    assert matching[0]["sweetword_index"] == decoy_index
    assert matching[0]["severity"] == "critical"


def test_sharing_and_tamper_detection_in_demo_mode(
    client: TestClient,
    pki_env: dict[str, Any],
) -> None:
    """Flow 4: Sharing and tamper detection in DEMO_MODE.

    - Register Alice and Bob.
    - Alice shares a vault entry with Bob.
    - Bob opens it: signature_valid and certificate_valid are True, decrypted payload matches.
    - In DEMO_MODE, Alice shares another entry, tampers with the envelope
      via POST /api/shares/{id}/tamper.
    - Bob opens tampered share: signature_valid becomes False, username & password are None.
    """
    settings = get_settings()
    assert settings.demo_mode is True, "DEMO_MODE must be enabled for tamper endpoint"

    alice_user = f"alice_{uuid.uuid4().hex[:8]}"
    bob_user = f"bob_{uuid.uuid4().hex[:8]}"
    alice_master = "AliceMasterPassword123!"
    bob_master = "BobMasterPassword456@"

    _register_user(client, alice_user, "AliceLogin123!", alice_master)
    _register_user(client, bob_user, "BobLogin456@", bob_master)

    alice_token = _login_user(client, alice_user, "AliceLogin123!")
    bob_token = _login_user(client, bob_user, "BobLogin456@")

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Alice creates entry 1
    add_resp = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "cloud.provider.com",
            "username": "alice_cloud",
            "password": "CloudSecretPassword123!",
        },
        headers=alice_headers,
    )
    assert add_resp.status_code == 201
    entry_id = add_resp.json()["id"]

    # Alice shares entry 1 with Bob
    share_resp = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": entry_id,
            "recipient_username": bob_user,
        },
        headers=alice_headers,
    )
    assert share_resp.status_code == 201
    share_id = share_resp.json()["share_id"]

    # Bob retrieves and opens share 1
    open_resp = client.post(f"/api/shares/{share_id}/open", headers=bob_headers)
    assert open_resp.status_code == 200
    open_data = open_resp.json()
    assert open_data["service"] == "cloud.provider.com"
    assert open_data["username"] == "alice_cloud"
    assert open_data["password"] == "CloudSecretPassword123!"  # noqa: S105
    assert open_data["sender"] == alice_user
    assert open_data["signature_valid"] is True
    assert open_data["certificate_valid"] is True
    assert open_data["certificate_subject"] == f"CN={alice_user}"

    # Alice creates entry 2 to demonstrate tampering
    add_resp2 = client.post(
        "/api/vault/entries",
        json={
            "master_password": alice_master,
            "service": "banking.service.net",
            "username": "alice_bank",
            "password": "BankSecretPassword789!",
        },
        headers=alice_headers,
    )
    assert add_resp2.status_code == 201
    entry_id2 = add_resp2.json()["id"]

    share_resp2 = client.post(
        "/api/shares",
        json={
            "master_password": alice_master,
            "entry_id": entry_id2,
            "recipient_username": bob_user,
        },
        headers=alice_headers,
    )
    assert share_resp2.status_code == 201
    share_id2 = share_resp2.json()["share_id"]

    # Tamper with share 2 via DEMO_MODE endpoint
    tamper_resp = client.post(f"/api/shares/{share_id2}/tamper", headers=alice_headers)
    assert tamper_resp.status_code == 200
    assert tamper_resp.json() == {"tampered": True}

    # Bob opens tampered share 2: signature check must fail
    open_tampered_resp = client.post(f"/api/shares/{share_id2}/open", headers=bob_headers)
    assert open_tampered_resp.status_code == 200
    tampered_data = open_tampered_resp.json()

    assert tampered_data["signature_valid"] is False
    assert tampered_data["certificate_valid"] is True
    assert tampered_data["username"] is None
    assert tampered_data["password"] is None
    assert tampered_data["service"] == "banking.service.net"
    assert tampered_data["sender"] == alice_user


def test_honeychecker_unavailable_fails_closed_503(
    client: TestClient, fake_hc: FakeHoneycheckerClient
) -> None:
    """Flow 5: Honeychecker unavailable fails closed.

    - Register a user while honeychecker is active.
    - Simulate Honeychecker outage.
    - Assert login fails closed with HTTP 503 and 'Service temporarily unavailable'.
    """
    username = f"hc_down_{uuid.uuid4().hex[:8]}"
    login_pw = "ValidLoginPass123!"
    master_pw = "ValidMasterPass456@"

    _register_user(client, username, login_pw, master_pw)

    # Simulate honeychecker service unavailability
    fake_hc.is_down = True

    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "login_password": login_pw,
        },
    )
    assert login_resp.status_code == 503
    assert login_resp.json()["detail"] == "Service temporarily unavailable"


def test_evaluation_summary_returns_200_and_metrics_schema(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flow 6: Evaluation summary endpoint health.

    - Query GET /api/eval/summary.
    - Point EVAL_RESULTS_PATH to the committed eval/results/latest.json artifact.
    - Assert HTTP 200 and expected schema fields (timestamp, version, dataset, round_trip).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    committed_eval_file = repo_root / "eval" / "results" / "latest.json"
    assert committed_eval_file.is_file(), f"Missing committed artifact {committed_eval_file}"

    monkeypatch.setenv("EVAL_RESULTS_PATH", str(committed_eval_file))
    settings = get_settings()
    monkeypatch.setattr(settings, "eval_results_path", str(committed_eval_file))

    resp = client.get("/api/eval/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Verify against committed JSON content
    with open(committed_eval_file, encoding="utf-8") as f:
        expected_json = json.load(f)

    assert data == expected_json

    # Validate structural fields in the summary schema
    assert "timestamp" in data
    assert "version" in data
    assert "dataset" in data
    assert "round_trip" in data
    assert "success_rate" in data["round_trip"]
    assert data["round_trip"]["success_rate"] == 1.0
