"""Seed demo database with admin, demo, and bob accounts.

Owner: T2 — Tanuj (scripts/seed_demo.py).
Contract: PROJECT-BRIEF.md §8 and §11, PROJECT-ROADMAP.md §2.

Creates idempotent demo accounts:
- admin: ADMIN_USERNAME / ADMIN_LOGIN_PASSWORD, is_admin=True,
  master = a random secret printed once, never stored.
- demo: DEMO_USERNAME / DEMO_LOGIN_PASSWORD / DEMO_MASTER_PASSWORD,
  vault with KDF profile "demo" and 8 realistic fictional entries;
  a ConventionalVault with the same entries and master ("demo" profile)
  stored as DemoArtifact "baseline_vault";
  the demo user's plaintext sweetwords stored as DemoArtifact "demo_sweetwords"
  (only when DEMO_MODE=true, never for any other user);
  eval summary metrics stored as DemoArtifact "eval_summary" if file exists.
- bob: BOB_* settings, standard vault with 2 entries (work email, personal bank)
  for sharing and attacker demos.

Refuses to run in non-development environments if required secrets are unset
or "change-me". Never prints passwords except the generated admin master.
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import secrets
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import SessionLocal
from app.deps import get_honeycore
from app.models.core import Alert, DemoArtifact, Share, User, Vault
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.registration import register_user
from honeycore.factory import HoneyCore
from honeycore.interfaces import Entry

logger = logging.getLogger(__name__)

# 8 realistic fictional entries for demo user (PROJECT-BRIEF.md §11)
DEMO_ENTRIES: list[Entry] = [
    Entry(service="github.com", username="alex.mercer", password="GitDev#2024!Safe"),  # noqa: S106
    Entry(service="gmail.com", username="alex.mercer@gmail.com", password="P@ssw0rdSecure48"),  # noqa: S106
    Entry(service="netflix.com", username="alex.mercer@gmail.com", password="SummerSunset!2024"),  # noqa: S106
    # Reused password between netflix and amazon:
    Entry(service="amazon.in", username="alex.mercer@gmail.com", password="SummerSunset!2024"),  # noqa: S106
    Entry(service="linkedin.com", username="alex-mercer-pro", password="WorkCareer$2025"),  # noqa: S106
    Entry(service="spotify.com", username="alex_beats", password="MusicGroove#8812"),  # noqa: S106
    Entry(service="instagram.com", username="alex.snaps", password="InstaPic%994"),  # noqa: S106
    Entry(service="hdfcbank.com", username="alex_hdfc_usr", password="Hdfc$NetBank!2024"),  # noqa: S106
]

# 2 realistic entries for bob (work email + personal bank)
BOB_ENTRIES: list[Entry] = [
    Entry(
        service="workmail.company.internal",
        username="bob.smith@corp.internal",
        password="WorkSecret99!Corp",  # noqa: S106
    ),
    Entry(
        service="hdfcbank.com",
        username="bob_hdfc_banking",
        password="BankSafe#2024Secure",  # noqa: S106
    ),
]


def check_environment(settings: Settings) -> None:
    """Validate settings before seeding.

    Refuse to run when APP_ENV != development and any required var is unset or 'change-me'.
    """
    if settings.app_env != "development":
        required: dict[str, str | None] = {
            "ADMIN_LOGIN_PASSWORD": settings.admin_login_password.get_secret_value(),
            "DEMO_LOGIN_PASSWORD": settings.demo_login_password.get_secret_value(),
            "DEMO_MASTER_PASSWORD": settings.demo_master_password.get_secret_value(),
            "BOB_LOGIN_PASSWORD": (
                settings.bob_login_password.get_secret_value()
                if settings.bob_login_password
                else None
            ),
            "BOB_MASTER_PASSWORD": (
                settings.bob_master_password.get_secret_value()
                if settings.bob_master_password
                else None
            ),
            "JWT_SECRET": settings.jwt_secret.get_secret_value(),
        }
        for name, val in required.items():
            if not val or val.strip() == "" or val.strip() == "change-me":
                raise RuntimeError(
                    f"Refusing to seed in '{settings.app_env}' environment: "
                    f"required setting {name} is unset or 'change-me'."
                )


def _print_summary(settings: Settings, admin_master: str | None) -> None:
    """Print clean summary with next steps and curl commands, redacting sensitive passwords."""
    print("=" * 72)
    print("HoneyVault Demo Seeding Complete!")
    print("=" * 72)
    if admin_master:
        print(f"\n[!] GENERATED ADMIN MASTER PASSWORD: {admin_master}")
        print("    (Printed once, never stored. Save this now for admin vault access.)")

    print("\nAccounts Seeded:")
    print(f"  - Admin:  username = {settings.admin_username}")
    print(f"  - Demo:   username = {settings.demo_username}")
    print("            login/master passwords configured in .env (DEMO_*)")
    print("            8 entries in vault + baseline conventional vault artifact")
    print(f"  - Bob:    username = {settings.bob_username}")
    print("            login/master passwords configured in .env (BOB_*)")
    print("            2 entries in vault (for sharing / attacker demos)")

    print("\nNext Steps & Testing:")
    print("  1. Frontend:")
    print("     Open http://localhost:5173")
    print("\n  2. API Health Check:")
    print("     curl http://localhost:8000/api/health")
    print("\n  3. Demo User Login:")
    print(
        "     curl -X POST http://localhost:8000/api/auth/login \\\n"
        '       -H "Content-Type: application/json" \\\n'
        f'       -d \'{{"username": "{settings.demo_username}", '
        '"password": "<DEMO_LOGIN_PASSWORD>"}\''
    )
    print("\n  4. Unlock Vault:")
    print(
        "     curl -X POST http://localhost:8000/api/vault/unlock \\\n"
        '       -H "Authorization: Bearer <TOKEN>" \\\n'
        '       -H "Content-Type: application/json" \\\n'
        '       -d \'{"master_password": "<DEMO_MASTER_PASSWORD>"}\''
    )
    print("=" * 72 + "\n")


def seed_demo(
    db: Session | None = None,
    *,
    if_missing: bool = False,
    reset_demo: bool = False,
    honeycore: HoneyCore | None = None,
    honeychecker: HoneycheckerClient | None = None,
    settings: Settings | None = None,
    admin_login_pw: str | None = None,
    demo_login_pw: str | None = None,
    demo_master_pw: str | None = None,
    bob_login_pw: str | None = None,
    bob_master_pw: str | None = None,
) -> dict[str, Any]:
    """Seed demo accounts, vaults, and artifacts.

    Idempotent by default.
    """
    cfg = settings or get_settings()
    check_environment(cfg)

    hc = honeychecker or get_honeychecker_client()
    hc_owned = honeychecker is None
    hc_unreachable = False

    try:
        if not hc.health():
            hc_unreachable = True
    except HoneycheckerUnavailable:
        hc_unreachable = True

    if hc_unreachable:
        if hc_owned:
            hc.close()
        raise HoneycheckerUnavailable(
            f"Honeychecker service is unreachable at {cfg.honeychecker_url}. "
            "Please ensure the honeychecker service is running."
        )

    hc_core = honeycore or get_honeycore()

    # Passwords resolution
    admin_pw = admin_login_pw or cfg.admin_login_password.get_secret_value()
    if cfg.app_env == "development" and (not admin_pw or admin_pw == "change-me"):
        admin_pw = "admin-login-dev-2026"  # noqa: S105
    generated_admin_master = secrets.token_urlsafe(24)

    d_login = demo_login_pw or cfg.demo_login_password.get_secret_value()
    if cfg.app_env == "development" and (not d_login or d_login == "change-me"):
        d_login = "demo-login-pass-2026"  # noqa: S105
    d_master = demo_master_pw or cfg.demo_master_password.get_secret_value()
    if cfg.app_env == "development" and (not d_master or d_master == "change-me"):
        d_master = "demo-master-vault-2026"  # noqa: S105

    if hmac.compare_digest(d_login, d_master):
        raise ValueError("Demo login password and master password must differ")

    b_login = bob_login_pw or (
        cfg.bob_login_password.get_secret_value() if cfg.bob_login_password else ""
    )
    if cfg.app_env == "development" and (not b_login or b_login == "change-me"):
        b_login = "bob-login-pass-2026"  # noqa: S105
    b_master = bob_master_pw or (
        cfg.bob_master_password.get_secret_value() if cfg.bob_master_password else ""
    )
    if cfg.app_env == "development" and (not b_master or b_master == "change-me"):
        b_master = "bob-master-vault-2026"  # noqa: S105

    if hmac.compare_digest(b_login, b_master):
        raise ValueError("Bob login password and master password must differ")

    session = db or SessionLocal()
    session_owned = db is None

    try:
        # Check --if-missing
        existing_demo = session.scalar(select(User).where(User.username == cfg.demo_username))
        if if_missing and existing_demo is not None:
            logger.info("Demo user '%s' exists; skipping (--if-missing).", cfg.demo_username)
            return {
                "status": "skipped",
                "message": f"Demo user '{cfg.demo_username}' already exists.",
            }

        # Check --reset-demo
        if reset_demo:
            logger.info("Resetting demo users and artifacts...")
            session.execute(
                delete(DemoArtifact).where(
                    DemoArtifact.key.in_(["baseline_vault", "demo_sweetwords", "eval_summary"])
                )
            )
            usernames = [cfg.admin_username, cfg.demo_username, cfg.bob_username]
            existing_users = session.scalars(select(User).where(User.username.in_(usernames))).all()
            for u in existing_users:
                session.execute(
                    delete(Share).where((Share.sender_id == u.id) | (Share.recipient_id == u.id))
                )
                session.execute(delete(Alert).where(Alert.user_id == u.id))
                session.execute(delete(Vault).where(Vault.user_id == u.id))
                session.delete(u)
            session.commit()

        # 1. Admin account
        admin_user = session.scalar(select(User).where(User.username == cfg.admin_username))
        printed_admin_master: str | None = None
        if admin_user is None:
            admin_res = register_user(
                session,
                honeycore=hc_core,
                honeychecker=hc,
                username=cfg.admin_username,
                login_password=admin_pw,
                master_password=generated_admin_master,
                capture_sweetwords=False,
            )
            admin_user = admin_res.user
            admin_user.is_admin = True
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            printed_admin_master = generated_admin_master

        # 2. Demo account
        demo_user = session.scalar(select(User).where(User.username == cfg.demo_username))
        captured_sweetwords = None
        if demo_user is None:
            demo_res = register_user(
                session,
                honeycore=hc_core,
                honeychecker=hc,
                username=cfg.demo_username,
                login_password=d_login,
                master_password=d_master,
                vault_kdf_profile="demo",
                capture_sweetwords=True,
            )
            demo_user = demo_res.user
            captured_sweetwords = demo_res.sweetwords

        # Populate demo vault entries if empty
        demo_vault_rec = session.get(Vault, demo_user.id)
        if demo_vault_rec is not None:
            demo_vault = hc_core.vault_cls.from_dict(demo_vault_rec.blob)
            if demo_vault.entry_count() == 0:
                for entry in DEMO_ENTRIES:
                    demo_vault.add_entry(d_master, entry)
                demo_vault_rec.blob = demo_vault.to_dict()
                session.commit()

        # Baseline ConventionalVault artifact
        baseline_art = session.get(DemoArtifact, "baseline_vault")
        if baseline_art is None or reset_demo:
            conv_vault = hc_core.conventional_vault_cls.new(d_master, kdf_profile="demo")
            for entry in DEMO_ENTRIES:
                conv_vault.add_entry(d_master, entry)
            session.merge(DemoArtifact(key="baseline_vault", payload=conv_vault.to_dict()))
            session.commit()

        # Demo sweetwords artifact (only when DEMO_MODE=true, never for other users)
        if cfg.demo_mode and captured_sweetwords:
            session.merge(
                DemoArtifact(
                    key="demo_sweetwords",
                    payload={"sweetwords": captured_sweetwords},
                )
            )
            session.commit()

        # Eval summary artifact (if file exists)
        eval_paths = [
            Path(cfg.eval_results_path),
            Path("eval/results/latest.json"),
            Path("../eval/results/latest.json"),
        ]
        for p in eval_paths:
            if p.is_file():
                try:
                    eval_data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(eval_data, dict):
                        session.merge(DemoArtifact(key="eval_summary", payload=eval_data))
                        session.commit()
                        break
                except (OSError, json.JSONDecodeError):
                    pass

        # 3. Bob account
        bob_user = session.scalar(select(User).where(User.username == cfg.bob_username))
        if bob_user is None:
            bob_res = register_user(
                session,
                honeycore=hc_core,
                honeychecker=hc,
                username=cfg.bob_username,
                login_password=b_login,
                master_password=b_master,
                vault_kdf_profile=cfg.vault_kdf_profile,
                capture_sweetwords=False,
            )
            bob_user = bob_res.user

        bob_vault_rec = session.get(Vault, bob_user.id)
        if bob_vault_rec is not None:
            bob_vault = hc_core.vault_cls.from_dict(bob_vault_rec.blob)
            if bob_vault.entry_count() == 0:
                for entry in BOB_ENTRIES:
                    bob_vault.add_entry(b_master, entry)
                bob_vault_rec.blob = bob_vault.to_dict()
                session.commit()

        _print_summary(cfg, printed_admin_master)
        return {
            "status": "seeded",
            "admin_user": admin_user,
            "demo_user": demo_user,
            "bob_user": bob_user,
            "admin_master": printed_admin_master,
            "demo_master": d_master,
            "demo_login": d_login,
            "bob_master": b_master,
            "bob_login": b_login,
        }
    finally:
        if session_owned:
            session.close()
        if hc_owned:
            hc.close()


def main() -> None:
    """CLI entrypoint for seeding demo data."""
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="Seed demo accounts (admin, demo, bob) and baseline vault."
    )
    parser.add_argument(
        "--if-missing",
        action="store_true",
        help="Only seed if demo user is missing; exit cleanly if already present.",
    )
    parser.add_argument(
        "--reset-demo",
        action="store_true",
        help="Reset existing demo accounts and artifacts before seeding.",
    )
    args = parser.parse_args()

    try:
        seed_demo(if_missing=args.if_missing, reset_demo=args.reset_demo)
    except HoneycheckerUnavailable as exc:
        sys.stderr.write(f"\n[ERROR] Honeychecker unavailable: {exc}\n")
        sys.exit(1)
    except RuntimeError as exc:
        sys.stderr.write(f"\n[ERROR] Seeding refused: {exc}\n")
        sys.exit(1)
    except Exception as exc:
        sys.stderr.write(f"\n[ERROR] Seeding failed: {exc}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
