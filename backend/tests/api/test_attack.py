"""Tests for /api/attack endpoints.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §8 (frozen).
Covers:
- demo_mode disabled returns 404 for all endpoints.
- GET /api/attack/stolen-vault shape (honey_blob, baseline_blob, owner).
- POST /api/attack/dictionary with max_guesses=50 cracks baseline at reveal.real_guess_index,
  reports honey guesses_tried=50.
- GET /api/attack/stolen-honeywords returns k entries, salt, hashes, cracked_sweetwords.
- Logging in as demo with a non-real sweetword triggers an alert in GET /api/attack/alarms.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
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
from scripts.seed_demo import seed_demo


class FakeHoneycheckerClient(HoneycheckerClient):
    """In-memory honeychecker client for testing."""

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
    client: TestClient,
    fake_hc: FakeHoneycheckerClient,
) -> Generator[None, None, None]:
    """Inject in-memory fake honeychecker into FastAPI dependency overrides."""
    limiter.reset()
    client.app.dependency_overrides[get_honeychecker_client] = lambda: fake_hc
    yield
    client.app.dependency_overrides.pop(get_honeychecker_client, None)
    limiter.reset()


@pytest.fixture
def seeded_demo(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> dict:
    """Fixture that seeds demo database with admin, demo, and bob accounts."""
    honeycore = get_honeycore()
    settings = get_settings()
    return seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )


def test_demo_mode_disabled_returns_404(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All /api/attack endpoints return 404 when demo_mode is False."""
    orig_settings = get_settings()
    monkeypatch.setattr(orig_settings, "demo_mode", False)

    endpoints = [
        ("GET", "/api/attack/stolen-vault", None),
        ("POST", "/api/attack/dictionary", {"max_guesses": 50}),
        ("GET", "/api/attack/stolen-honeywords", None),
        ("GET", "/api/attack/alarms", None),
    ]

    for method, path, json_data in endpoints:
        if method == "GET":
            resp = client.get(path)
        else:
            resp = client.post(path, json=json_data)
        assert resp.status_code == 404, f"{path} did not return 404 when demo_mode=False"
        assert resp.json()["detail"] == "Demo mode disabled"


def test_stolen_vault_shape(
    client: TestClient,
    seeded_demo: dict,
) -> None:
    """GET /api/attack/stolen-vault returns honey_blob, baseline_blob, and owner."""
    resp = client.get("/api/attack/stolen-vault")
    assert resp.status_code == 200

    data = resp.json()
    assert data["owner"] == "demo"

    honey_blob = data["honey_blob"]
    assert honey_blob["format"] == "honeyvault"
    assert "entries" in honey_blob
    assert len(honey_blob["entries"]) == 8

    baseline_blob = data["baseline_blob"]
    assert "entries" in baseline_blob or "ciphertext" in baseline_blob or "kdf" in baseline_blob


def test_dictionary_attack_max_guesses_50(
    client: TestClient,
    seeded_demo: dict,
) -> None:
    """POST /api/attack/dictionary with max_guesses=50 cracks baseline at reveal index."""
    resp = client.post("/api/attack/dictionary", json={"max_guesses": 50})
    assert resp.status_code == 200

    data = resp.json()

    # Baseline oracle result
    baseline = data["baseline"]
    assert baseline["cracked"] is True
    assert baseline["guess_index"] is not None
    assert 1 <= baseline["guess_index"] <= 50
    assert len(baseline["recovered_entries"]) == 8
    assert baseline["elapsed_ms"] >= 0

    # Honey encryption result
    honey = data["honey"]
    assert honey["guesses_tried"] == 50
    assert honey["distinct_vaults"] >= 1
    assert len(honey["samples"]) <= 25
    assert len(honey["samples"]) > 0

    # Reveal index matches baseline cracked index
    reveal = data["reveal"]
    assert reveal["real_guess_index"] == baseline["guess_index"]


def test_dictionary_attack_custom_guesses(
    client: TestClient,
    seeded_demo: dict,
) -> None:
    """POST /api/attack/dictionary with custom_guesses evaluates candidate list."""
    custom = ["password123", "admin123", "secret2026"]
    resp = client.post(
        "/api/attack/dictionary",
        json={"max_guesses": 10, "custom_guesses": custom},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["baseline"]["cracked"] is True
    assert data["honey"]["guesses_tried"] == 4  # 3 custom + real master


def test_dictionary_attack_validation_errors(
    client: TestClient,
    seeded_demo: dict,
) -> None:
    """POST /api/attack/dictionary validates max_guesses range and custom_guesses."""
    # max_guesses < 1 -> 422
    resp = client.post("/api/attack/dictionary", json={"max_guesses": 0})
    assert resp.status_code == 422

    # max_guesses > 2000 -> 422
    resp = client.post("/api/attack/dictionary", json={"max_guesses": 2001})
    assert resp.status_code == 422

    # custom guess > 32 chars -> 422
    resp = client.post(
        "/api/attack/dictionary",
        json={"custom_guesses": ["a" * 33]},
    )
    assert resp.status_code == 422


def test_stolen_honeywords_k_entries(
    client: TestClient,
    seeded_demo: dict,
) -> None:
    """GET /api/attack/stolen-honeywords returns k hashes and cracked sweetwords."""
    resp = client.get("/api/attack/stolen-honeywords")
    assert resp.status_code == 200

    data = resp.json()
    assert data["username"] == "demo"
    assert data["k"] == 10
    assert bool(data["salt"]) is True
    assert len(data["hashes"]) == 10
    assert len(data["cracked_sweetwords"]) == 10


def test_decoy_sweetword_login_shows_alert_in_alarms(
    client: TestClient,
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
    seeded_demo: dict,
) -> None:
    """Logging in as demo with a non-real sweetword triggers an alert in GET /api/attack/alarms."""
    # 1. Fetch stolen honeywords to find candidates
    hw_resp = client.get("/api/attack/stolen-honeywords")
    assert hw_resp.status_code == 200
    sweetwords = hw_resp.json()["cracked_sweetwords"]

    # 2. Identify a decoy sweetword (index != real registered index)
    demo_user = db_session.scalar(select(User).where(User.username == "demo"))
    assert demo_user is not None
    demo_user_id = demo_user.id
    real_idx = fake_hc.indices.get(demo_user_id, 0)
    decoy_idx = (real_idx + 1) % len(sweetwords)
    decoy_pw = sweetwords[decoy_idx]

    # 3. Attempt login with the decoy sweetword -> 401
    login_resp = client.post(
        "/api/auth/login",
        json={"username": "demo", "login_password": decoy_pw},
        headers={"User-Agent": "AttackerConsole/1.0"},
    )
    assert login_resp.status_code == 401
    assert login_resp.json()["detail"] == "Invalid credentials"

    # 4. GET /api/attack/alarms shows the recorded alert
    alarms_resp = client.get("/api/attack/alarms")
    assert alarms_resp.status_code == 200

    alarms = alarms_resp.json()
    assert len(alarms) >= 1
    recent = alarms[0]
    assert recent["username"] == "demo"
    assert recent["kind"] == "HONEYWORD_LOGIN"
    assert recent["severity"] == "critical"
    assert recent["sweetword_index"] == decoy_idx
