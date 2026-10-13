"""Tests for /api/auth endpoints: register, login (honeywords), and profile.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import base64
import secrets
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_honeycore
from app.models.core import Alert, User, Vault
from app.rate_limit import limiter
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.honeywords import HoneywordRecord, generate_sweetwords, hash_sweetword


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


def test_register_and_login_success(
    client: TestClient, db_session: Session, fake_hc: FakeHoneycheckerClient
) -> None:
    """Register creates user, vault, registers with honeychecker, and allows successful login."""
    unique_user = f"user_{uuid.uuid4().hex[:8]}"
    login_pw = "ValidLoginPass123!"
    master_pw = "ValidMasterPass456@"

    # 1. Register
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "username": unique_user,
            "login_password": login_pw,
            "master_password": master_pw,
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()
    assert user_data["username"] == unique_user
    user_id = user_data["id"]

    # Verify honeychecker received the real index
    assert user_id in fake_hc.indices
    assert isinstance(fake_hc.indices[user_id], int)

    # Verify vault was initialized
    vault = db_session.get(Vault, user_id)
    assert vault is not None
    assert isinstance(vault.blob, dict)

    # 2. Login
    login_resp = client.post(
        "/api/auth/login",
        json={
            "username": unique_user,
            "login_password": login_pw,
        },
    )
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"  # noqa: S105
    assert login_data["user"]["id"] == user_id
    assert login_data["user"]["username"] == unique_user

    # 3. GET /api/auth/me
    token = login_data["access_token"]
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["id"] == user_id
    assert me_data["username"] == unique_user
    assert me_data["entry_count"] == 0
    assert "created_at" in me_data


def test_register_login_equals_master_returns_422(client: TestClient) -> None:
    """Registration rejects equal login and master passwords with HTTP 422."""
    pw = "IdenticalPass123!"
    resp = client.post(
        "/api/auth/register",
        json={
            "username": f"user_{uuid.uuid4().hex[:8]}",
            "login_password": pw,
            "master_password": pw,
        },
    )
    assert resp.status_code == 422
    assert resp.json()["detail"] == "Login password and master password must differ"


def test_register_duplicate_username_returns_409(client: TestClient) -> None:
    """Registration returns 409 Conflict if username already exists."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": "Password123!",
            "master_password": "MasterPassword123!",
        },
    )

    dup_resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": "OtherPassword123!",
            "master_password": "OtherMasterPassword123!",
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["detail"] == "Username already taken"


def test_register_honeychecker_unavailable_returns_503(
    client: TestClient, db_session: Session, fake_hc: FakeHoneycheckerClient
) -> None:
    """When honeychecker is down during registration, transaction rolls back and returns 503."""
    fake_hc.is_down = True
    username = f"user_{uuid.uuid4().hex[:8]}"

    resp = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": "Password123!",
            "master_password": "MasterPassword123!",
        },
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Honeychecker unavailable"

    # User must not exist in DB
    user = db_session.scalar(select(User).where(User.username == username))
    assert user is None


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    """Login with completely wrong password returns 401 without recording an alert."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": "CorrectPassword123!",
            "master_password": "MasterPassword123!",
        },
    )

    resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "login_password": "CompletelyWrongPassword999!",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_unknown_user_returns_401(client: TestClient) -> None:
    """Login with unknown username returns 401 (timing protected)."""
    resp = client.post(
        "/api/auth/login",
        json={
            "username": "non_existent_user_999",
            "login_password": "SomePassword123!",
        },
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_decoy_sweetword_records_alert_and_returns_401(
    client: TestClient, db_session: Session, fake_hc: FakeHoneycheckerClient
) -> None:
    """Logging in with a decoy sweetword returns 401 and records a HONEYWORD_LOGIN Alert row."""
    honeycore = get_honeycore()
    real_pw = "RealPassword123!"
    salt = secrets.token_bytes(16)
    sweetwords, real_index = generate_sweetwords(real_pw, 10, honeycore.password_model)

    # Pick a decoy sweetword (index != real_index)
    decoy_index = (real_index + 1) % len(sweetwords)
    decoy_pw = sweetwords[decoy_index]
    assert decoy_pw != real_pw

    hashes = [hash_sweetword(sw, salt, "demo") for sw in sweetwords]
    salt_b64 = base64.b64encode(salt).decode("ascii")
    record = HoneywordRecord(salt_b64=salt_b64, hashes=hashes, kdf_profile="demo")

    username = f"decoy_test_{uuid.uuid4().hex[:8]}"
    user = User(
        username=username,
        is_admin=False,
        hw_salt=record.salt_b64,
        hw_hashes=record.hashes,
        hw_kdf_profile=record.kdf_profile,
    )
    db_session.add(user)
    db_session.flush()

    # Register the real index with the fake honeychecker
    fake_hc.indices[user.id] = real_index

    # Attempt login with the decoy sweetword
    resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "login_password": decoy_pw,
        },
        headers={"User-Agent": "HoneyAttacker/1.0"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"

    # Verify an Alert row was created in DB
    alert_rows = list(db_session.scalars(select(Alert).where(Alert.username == username)).all())
    assert len(alert_rows) == 1
    alert = alert_rows[0]
    assert alert.kind == "HONEYWORD_LOGIN"
    assert alert.severity == "critical"
    assert alert.sweetword_index == decoy_index
    assert alert.user_agent == "HoneyAttacker/1.0"


def test_login_honeychecker_down_returns_503(
    client: TestClient, fake_hc: FakeHoneycheckerClient
) -> None:
    """When honeychecker is down during login, login fails closed with 503."""
    username = f"user_{uuid.uuid4().hex[:8]}"
    login_pw = "Password123!"
    client.post(
        "/api/auth/register",
        json={
            "username": username,
            "login_password": login_pw,
            "master_password": "MasterPassword123!",
        },
    )

    # Simulate honeychecker outage
    fake_hc.is_down = True

    resp = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "login_password": login_pw,
        },
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Service temporarily unavailable"
