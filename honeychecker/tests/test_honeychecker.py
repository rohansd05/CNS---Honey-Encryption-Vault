"""Comprehensive integration tests for honeychecker service with in-memory SQLite.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import time
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.config as app_config
import app.security as app_security
from app.db import Base, get_db
from app.main import create_app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory SQLite session for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with the in-memory DB override."""
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_register_and_check_match(client: TestClient) -> None:
    """Registering a real index and checking the matching index succeeds without alarm."""
    reg_resp = client.post("/hc/register", json={"user_id": "user-1", "index": 4})
    assert reg_resp.status_code == 201
    assert reg_resp.json() == {"status": "registered"}

    check_resp = client.post("/hc/check", json={"user_id": "user-1", "index": 4})
    assert check_resp.status_code == 200
    assert check_resp.json() == {"match": True}

    alarms_resp = client.get("/hc/alarms")
    assert alarms_resp.status_code == 200
    assert len(alarms_resp.json()) == 0


def test_register_duplicate_returns_409(client: TestClient) -> None:
    """Registering an already registered user ID returns 409 Conflict."""
    reg_resp = client.post("/hc/register", json={"user_id": "user-dup", "index": 2})
    assert reg_resp.status_code == 201

    dup_resp = client.post("/hc/register", json={"user_id": "user-dup", "index": 5})
    assert dup_resp.status_code == 409
    assert dup_resp.json() == {"detail": "Already registered"}


def test_register_invalid_index(client: TestClient) -> None:
    """Registering a negative index triggers validation error 422."""
    resp = client.post("/hc/register", json={"user_id": "user-neg", "index": -1})
    assert resp.status_code == 422


def test_check_mismatch_creates_alarm(client: TestClient) -> None:
    """Mismatching sweetword index returns match=False and writes a HONEYWORD_MISMATCH alarm."""
    client.post("/hc/register", json={"user_id": "user-mismatch", "index": 3})

    check_resp = client.post("/hc/check", json={"user_id": "user-mismatch", "index": 7})
    assert check_resp.status_code == 200
    assert check_resp.json() == {"match": False}

    alarms_resp = client.get("/hc/alarms")
    assert alarms_resp.status_code == 200
    alarms = alarms_resp.json()
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm["user_id"] == "user-mismatch"
    assert alarm["claimed_index"] == 7
    assert alarm["submitted_index"] == 7
    assert alarm["kind"] == "HONEYWORD_MISMATCH"
    assert "created_at" in alarm
    assert "real_index" not in alarm
    assert 3 not in alarm.values()  # Real index value is never leaked


def test_check_unknown_user_creates_alarm(client: TestClient) -> None:
    """Checking an unregistered user returns match=False and writes an UNKNOWN_USER alarm."""
    check_resp = client.post("/hc/check", json={"user_id": "unknown-user", "index": 1})
    assert check_resp.status_code == 200
    assert check_resp.json() == {"match": False}

    alarms_resp = client.get("/hc/alarms")
    assert alarms_resp.status_code == 200
    alarms = alarms_resp.json()
    assert len(alarms) == 1

    alarm = alarms[0]
    assert alarm["user_id"] == "unknown-user"
    assert alarm["claimed_index"] == 1
    assert alarm["kind"] == "UNKNOWN_USER"


def test_alarms_listing_newest_first_and_limit(client: TestClient) -> None:
    """GET /hc/alarms orders newest first and honors limit query parameter."""
    client.post("/hc/check", json={"user_id": "u-first", "index": 1})
    time.sleep(0.02)
    client.post("/hc/check", json={"user_id": "u-second", "index": 2})
    time.sleep(0.02)
    client.post("/hc/check", json={"user_id": "u-third", "index": 3})

    all_alarms = client.get("/hc/alarms").json()
    assert len(all_alarms) == 3
    assert all_alarms[0]["user_id"] == "u-third"
    assert all_alarms[1]["user_id"] == "u-second"
    assert all_alarms[2]["user_id"] == "u-first"

    limited_alarms = client.get("/hc/alarms?limit=2").json()
    assert len(limited_alarms) == 2
    assert limited_alarms[0]["user_id"] == "u-third"
    assert limited_alarms[1]["user_id"] == "u-second"


def test_health_ok_and_down(client: TestClient) -> None:
    """GET /hc/health reports status ok, db ok, or db down on failure."""
    resp = client.get("/hc/health")
    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "service": "honeychecker",
        "version": "0.1.0",
        "db": "ok",
    }

    # Simulate DB failure during health check
    mock_db = MagicMock()
    mock_db.execute.side_effect = RuntimeError("DB connection failure")

    app = create_app()

    def override_broken_db() -> Generator[MagicMock, None, None]:
        yield mock_db

    app.dependency_overrides[get_db] = override_broken_db
    with TestClient(app) as broken_client:
        down_resp = broken_client.get("/hc/health")
    assert down_resp.status_code == 200
    assert down_resp.json()["db"] == "down"


def OFF_test_security_verify_caller_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    """verify_caller allows plain transport and raises HTTP 501 for mtls or signed."""
    test_settings = app_config.Settings(hc_transport="signed")
    monkeypatch.setattr(app_security, "get_settings", lambda: test_settings)
    monkeypatch.setattr(app_config, "get_settings", lambda: test_settings)

    app = create_app()
    with TestClient(app) as unauth_client:
        # Protected endpoints must raise 501
        resp_reg = unauth_client.post("/hc/register", json={"user_id": "u", "index": 0})
        assert resp_reg.status_code == 501
        assert resp_reg.json() == {
            "detail": "transport not implemented yet (T4-Parth, Phase 2)",
        }

        resp_chk = unauth_client.post("/hc/check", json={"user_id": "u", "index": 0})
        assert resp_chk.status_code == 501

        resp_alm = unauth_client.get("/hc/alarms")
        assert resp_alm.status_code == 501

        # Health endpoint must NOT be protected and should still succeed (200)
        resp_hlt = unauth_client.get("/hc/health")
        assert resp_hlt.status_code == 200
