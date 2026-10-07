"""Attack service logic for DEMO_MODE attacker console endpoints.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §8 (frozen).
Logs only counts and timings; never logs credentials, guesses, or keys.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models.core import Alert, DemoArtifact, User, Vault
from attack import simulator
from honeycore.factory import HoneyCore

logger = logging.getLogger(__name__)


def get_demo_master_password(settings: Settings) -> str:
    """Retrieve the demo user's master password, using development fallback if unset."""
    pw = settings.demo_master_password.get_secret_value()
    if settings.app_env == "development" and (not pw or pw == "change-me"):
        return "demo-master-vault-2026"
    return pw


def get_stolen_vault(db: Session, settings: Settings) -> dict[str, Any]:
    """Return the demo user's honey vault and conventional baseline vault blobs."""
    demo_user = db.scalar(select(User).where(User.username == settings.demo_username))
    if demo_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo user not found. Please seed the demo account first.",
        )

    vault_rec = db.get(Vault, demo_user.id)
    if vault_rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo vault not found. Please seed the demo account first.",
        )

    baseline_art = db.get(DemoArtifact, "baseline_vault")
    if baseline_art is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline vault artifact not found. Please seed the demo account first.",
        )

    honey_blob = vault_rec.blob
    entries_count = len(honey_blob.get("entries", []))
    logger.info("Stolen vault fetched: %d entries in honey vault", entries_count)

    return {
        "honey_blob": honey_blob,
        "baseline_blob": baseline_art.payload,
        "owner": demo_user.username,
    }


def get_stolen_honeywords(db: Session, settings: Settings) -> dict[str, Any]:
    """Return the demo user's public honeywords and cracked sweetwords list."""
    demo_user = db.scalar(select(User).where(User.username == settings.demo_username))
    if demo_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo user not found. Please seed the demo account first.",
        )

    sw_art = db.get(DemoArtifact, "demo_sweetwords")
    if sw_art is None or "sweetwords" not in sw_art.payload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo sweetwords artifact not found. Please seed the demo account first.",
        )

    sweetwords = sw_art.payload["sweetwords"]
    logger.info("Stolen honeywords fetched: %d sweetwords returned", len(sweetwords))

    return {
        "username": demo_user.username,
        "k": len(demo_user.hw_hashes),
        "salt": demo_user.hw_salt,
        "hashes": demo_user.hw_hashes,
        "cracked_sweetwords": sweetwords,
    }


def get_demo_alarms(db: Session, settings: Settings, limit: int = 20) -> list[Alert]:
    """Retrieve recent alerts for the demo user, newest first (up to limit)."""
    fetch_limit = min(max(1, limit), 20)
    stmt = (
        select(Alert)
        .where(Alert.username == settings.demo_username)
        .order_by(Alert.created_at.desc())
        .limit(fetch_limit)
    )
    alarms = list(db.scalars(stmt).all())
    logger.info("Demo alarms fetched: %d alerts returned", len(alarms))
    return alarms


def execute_dictionary_attack(
    db: Session,
    honeycore: HoneyCore,
    settings: Settings,
    max_guesses: int = 300,
    custom_guesses: list[str] | None = None,
) -> dict[str, Any]:
    """Run dictionary attack comparing honey vault decoys vs baseline oracle."""
    demo_user = db.scalar(select(User).where(User.username == settings.demo_username))
    if demo_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo user not found. Please seed the demo account first.",
        )

    vault_rec = db.get(Vault, demo_user.id)
    if vault_rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo vault not found. Please seed the demo account first.",
        )

    baseline_art = db.get(DemoArtifact, "baseline_vault")
    if baseline_art is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline vault artifact not found. Please seed the demo account first.",
        )

    honey_vault = honeycore.vault_cls.from_dict(vault_rec.blob)
    baseline_vault = honeycore.conventional_vault_cls.from_dict(baseline_art.payload)

    demo_master = get_demo_master_password(settings)

    if custom_guesses:
        wordlist = custom_guesses
    else:
        wordlist = simulator.load_wordlist()

    guesses, real_index = simulator.build_guess_list(
        real_password=demo_master,
        max_guesses=max_guesses,
        wordlist=wordlist,
    )

    report = simulator.run_dictionary_attack(
        honey_vault=honey_vault,
        baseline_vault=baseline_vault,
        guesses=guesses,
        real_guess_index=real_index,
    )

    logger.info(
        "Dictionary attack completed: %d guesses evaluated (honey elapsed: %d ms, "
        "baseline elapsed: %d ms, distinct vaults: %d)",
        report.honey.guesses_tried,
        report.honey.elapsed_ms,
        report.baseline.elapsed_ms,
        report.honey.distinct_vaults,
    )

    return report.to_dict()
