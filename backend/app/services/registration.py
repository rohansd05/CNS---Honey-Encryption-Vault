"""User registration service encapsulating honeywords, vault init, and identity provisioning.

Owner: T2 — Rohan. Contract: docs/api-contract.md §2, PROJECT-BRIEF.md §8, §9.
"""

from __future__ import annotations

import base64
import hmac
import logging
import secrets
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.core import User, Vault
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
)
from app.services.honeywords import (
    HoneywordRecord,
    generate_sweetwords,
    hash_sweetword,
)
from app.services.identity_service import provision_identity
from honeycore.interfaces import SALT_LEN

if TYPE_CHECKING:
    from honeycore.factory import HoneyCore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RegistrationResult:
    """Result of registering a new user."""

    user: User
    sweetwords: list[str] | None = None


def register_user(
    db: Session,
    *,
    honeycore: HoneyCore,
    honeychecker: HoneycheckerClient,
    username: str,
    login_password: str,
    master_password: str,
    vault_kdf_profile: str | None = None,
    capture_sweetwords: bool = False,
) -> RegistrationResult:
    """Register a new user account with sweetwords, vault, and PKI identity."""
    if hmac.compare_digest(login_password, master_password):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Login password and master password must differ",
        )

    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    settings = get_settings()

    salt = secrets.token_bytes(SALT_LEN)
    sweetwords_list, real_index = generate_sweetwords(
        real=login_password,
        k=settings.honeywords_k,
        password_model=honeycore.password_model,
    )
    hashes = [hash_sweetword(sw, salt, settings.honeywords_kdf_profile) for sw in sweetwords_list]
    salt_b64 = base64.b64encode(salt).decode("ascii")

    record = HoneywordRecord(
        salt_b64=salt_b64,
        hashes=hashes,
        kdf_profile=settings.honeywords_kdf_profile,
    )

    new_user = User(
        username=username,
        is_admin=False,
        hw_salt=record.salt_b64,
        hw_hashes=record.hashes,
        hw_kdf_profile=record.kdf_profile,
    )

    provision_identity(new_user, settings=settings)

    db.add(new_user)
    db.flush()

    # Initialize empty honey vault
    profile = vault_kdf_profile or settings.vault_kdf_profile
    vault_obj = honeycore.vault_cls.new(profile)
    vault_record = Vault(user_id=new_user.id, blob=vault_obj.to_dict())
    db.add(vault_record)

    try:
        honeychecker.register(user_id=new_user.id, index=real_index)
    except HoneycheckerUnavailable as exc:
        db.rollback()
        logger.error("Failed to register sweetword with honeychecker: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Honeychecker unavailable",
        ) from exc

    db.commit()
    db.refresh(new_user)

    logger.info("User registered successfully: username=%s id=%s", new_user.username, new_user.id)
    captured = sweetwords_list if capture_sweetwords else None
    return RegistrationResult(user=new_user, sweetwords=captured)
