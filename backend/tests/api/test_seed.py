"""Tests for demo database seeding script.

Owner: T2 — Tanuj.
Covers:
- Running seed_demo twice is idempotent.
- Artifacts exist: baseline_vault, demo_sweetwords, eval_summary.
- Demo vault unlocks with master.
- Baseline vault opens with master and rejects wrong master password (WrongPasswordError).
- CLI flags --if-missing and --reset-demo behavior.
- Non-development refusal when passwords are unset or 'change-me'.
- Honeychecker unavailability handling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.deps import get_honeycore
from app.models.core import DemoArtifact, User, Vault
from app.services.honeychecker_client import HoneycheckerClient, HoneycheckerUnavailable
from honeycore.interfaces import WrongPasswordError
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


def test_seed_demo_success_and_artifacts(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """Seeding populates admin, demo, bob accounts, demo vault, and baseline artifacts."""
    honeycore = get_honeycore()
    settings = get_settings()

    res = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )

    assert res["status"] == "seeded"
    admin_user = res["admin_user"]
    demo_user = res["demo_user"]
    bob_user = res["bob_user"]
    demo_master = res["demo_master"]
    bob_master = res["bob_master"]

    # Verify Admin
    assert admin_user.is_admin is True
    assert admin_user.username == settings.admin_username
    assert res["admin_master"] is not None

    # Verify Demo HoneyVault
    demo_vault_rec = db_session.get(Vault, demo_user.id)
    assert demo_vault_rec is not None
    demo_vault = honeycore.vault_cls.from_dict(demo_vault_rec.blob)
    assert demo_vault.entry_count() == 8

    unlock_res = demo_vault.unlock(demo_master)
    assert len(unlock_res.entries) == 8
    services = {e.service for e in unlock_res.entries}
    expected_services = {
        "github.com",
        "gmail.com",
        "netflix.com",
        "amazon.in",
        "linkedin.com",
        "spotify.com",
        "instagram.com",
        "hdfcbank.com",
    }
    assert services == expected_services

    # Verify Bob HoneyVault
    bob_vault_rec = db_session.get(Vault, bob_user.id)
    assert bob_vault_rec is not None
    bob_vault = honeycore.vault_cls.from_dict(bob_vault_rec.blob)
    assert bob_vault.entry_count() == 2
    bob_unlock = bob_vault.unlock(bob_master)
    assert len(bob_unlock.entries) == 2

    # Verify baseline_vault artifact
    baseline_art = db_session.get(DemoArtifact, "baseline_vault")
    assert baseline_art is not None
    baseline_vault = honeycore.conventional_vault_cls.from_dict(baseline_art.payload)
    unlocked_entries = baseline_vault.unlock(demo_master)
    assert len(unlocked_entries) == 8

    # Baseline vault must reject wrong master password with WrongPasswordError
    with pytest.raises(WrongPasswordError):
        baseline_vault.unlock("wrong-password-1234")

    # Verify demo_sweetwords artifact
    if settings.demo_mode:
        sw_art = db_session.get(DemoArtifact, "demo_sweetwords")
        assert sw_art is not None
        assert "sweetwords" in sw_art.payload
        assert len(sw_art.payload["sweetwords"]) == settings.honeywords_k


def test_seed_demo_idempotency(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """Running seed_demo twice is idempotent and does not corrupt data."""
    honeycore = get_honeycore()
    settings = get_settings()

    res1 = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res1["status"] == "seeded"

    # Second run
    res2 = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res2["status"] == "seeded"

    # Vaults and artifacts still exist and unlock
    demo_user = db_session.get(User, res1["demo_user"].id)
    assert demo_user is not None
    demo_vault_rec = db_session.get(Vault, demo_user.id)
    assert demo_vault_rec is not None
    demo_vault = honeycore.vault_cls.from_dict(demo_vault_rec.blob)
    assert len(demo_vault.unlock(res1["demo_master"]).entries) == 8

    baseline_art = db_session.get(DemoArtifact, "baseline_vault")
    assert baseline_art is not None
    baseline_vault = honeycore.conventional_vault_cls.from_dict(baseline_art.payload)
    assert len(baseline_vault.unlock(res1["demo_master"])) == 8


def test_seed_demo_if_missing(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """--if-missing skips cleanly if demo user already exists."""
    honeycore = get_honeycore()
    settings = get_settings()

    res1 = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res1["status"] == "seeded"

    res2 = seed_demo(
        db=db_session,
        if_missing=True,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res2["status"] == "skipped"


def test_seed_demo_reset_demo(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """--reset-demo resets and reseeds demo accounts and artifacts."""
    honeycore = get_honeycore()
    settings = get_settings()

    res1 = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    first_demo_id = res1["demo_user"].id

    res2 = seed_demo(
        db=db_session,
        reset_demo=True,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res2["status"] == "seeded"
    # New user instance created
    second_demo_id = res2["demo_user"].id
    assert first_demo_id != second_demo_id

    # Artifacts exist and are fresh
    baseline_art = db_session.get(DemoArtifact, "baseline_vault")
    assert baseline_art is not None
    baseline_vault = honeycore.conventional_vault_cls.from_dict(baseline_art.payload)
    assert len(baseline_vault.unlock(res2["demo_master"])) == 8


def test_seed_demo_refuses_non_dev_with_change_me(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
) -> None:
    """Refuses to seed in non-development environment if required vars are 'change-me'."""
    honeycore = get_honeycore()
    staging_settings = Settings(
        app_env="staging",
        admin_login_password=SecretStr("change-me"),
        demo_login_password=SecretStr("real-login-pw"),
        demo_master_password=SecretStr("real-master-pw"),
        bob_login_password=SecretStr("real-bob-login"),
        bob_master_password=SecretStr("real-bob-master"),
        jwt_secret=SecretStr("super-long-valid-jwt-secret-string-at-least-32-bytes"),
    )

    with pytest.raises(RuntimeError, match="Refusing to seed in 'staging' environment"):
        seed_demo(
            db=db_session,
            honeycore=honeycore,
            honeychecker=fake_hc,
            settings=staging_settings,
        )


def test_seed_demo_honeychecker_unavailable(
    db_session: Session,
) -> None:
    """Honeychecker unavailable raises HoneycheckerUnavailable with clear error message."""
    honeycore = get_honeycore()
    settings = get_settings()
    down_hc = FakeHoneycheckerClient(is_down=True)

    with pytest.raises(HoneycheckerUnavailable, match="Honeychecker service is unreachable"):
        seed_demo(
            db=db_session,
            honeycore=honeycore,
            honeychecker=down_hc,
            settings=settings,
        )


def test_seed_demo_eval_summary_loaded(
    db_session: Session,
    fake_hc: FakeHoneycheckerClient,
    tmp_path: Path,
) -> None:
    """Loads eval_summary artifact if the results file exists."""
    honeycore = get_honeycore()
    eval_file = tmp_path / "latest.json"
    dummy_eval = {"chi_squared": 0.42, "classifier_accuracy": 0.51, "status": "ok"}
    eval_file.write_text(json.dumps(dummy_eval), encoding="utf-8")

    settings = Settings(
        eval_results_path=str(eval_file),
    )

    res = seed_demo(
        db=db_session,
        honeycore=honeycore,
        honeychecker=fake_hc,
        settings=settings,
    )
    assert res["status"] == "seeded"

    eval_art = db_session.get(DemoArtifact, "eval_summary")
    assert eval_art is not None
    assert eval_art.payload == dummy_eval
