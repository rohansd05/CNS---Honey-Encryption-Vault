"""Authentication endpoints: register, login (honeywords protected), and profile.

Owner: T2 — Rohan. Contract: docs/api-contract.md §2, §0.5.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_db, get_honeycore
from app.models.core import User, Vault
from app.rate_limit import limiter
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UserMeResponse,
    UserSummary,
)
from app.security import create_access_token, get_current_user
from app.services import alerts
from app.services.honeychecker_client import (
    HoneycheckerClient,
    HoneycheckerUnavailable,
    get_honeychecker_client,
)
from app.services.honeywords import (
    HoneywordRecord,
    find_index,
    hash_sweetword,
)
from app.services.registration import register_user
from honeycore.factory import HoneyCore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
)
def register(
    payload: RegisterRequest,
    db: Annotated[Session, Depends(get_db)],
    hc_client: Annotated[HoneycheckerClient, Depends(get_honeychecker_client)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> RegisterResponse:
    """Register a new user account with sweetwords honeychecker registration."""
    result = register_user(
        db,
        honeycore=honeycore,
        honeychecker=hc_client,
        username=payload.username,
        login_password=payload.login_password,
        master_password=payload.master_password,
    )
    return RegisterResponse(id=result.user.id, username=result.user.username)


@router.post(
    "/login",
    response_model=LoginResponse,
)
@limiter.limit(lambda: get_settings().rate_limit_login)
def login(
    request: Request,
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
    hc_client: Annotated[HoneycheckerClient, Depends(get_honeychecker_client)],
) -> LoginResponse:
    """Authenticate a user using their login password against stored sweetword hashes."""
    settings = get_settings()
    user = db.scalar(select(User).where(User.username == payload.username))

    # Timing attack protection for unknown users: compute one hash on dummy salt
    if user is None:
        dummy_salt = b"0123456789abcdef"
        hash_sweetword(payload.login_password, dummy_salt, settings.honeywords_kdf_profile)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    record = HoneywordRecord(
        salt_b64=user.hw_salt,
        hashes=user.hw_hashes,
        kdf_profile=user.hw_kdf_profile,
    )

    index = find_index(record, payload.login_password)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    try:
        is_match = hc_client.check(user_id=user.id, index=index)
    except HoneycheckerUnavailable as exc:
        logger.error("Honeychecker check unavailable during login for user %s: %s", user.id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        ) from exc

    if not is_match:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        alerts.create_alert(
            db=db,
            username=user.username,
            user_id=user.id,
            kind="HONEYWORD_LOGIN",
            severity="critical",
            sweetword_index=index,
            source_ip=client_ip,
            user_agent=user_agent,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(user)
    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106
        user=UserSummary(
            id=user.id,
            username=user.username,
            is_admin=user.is_admin,
        ),
    )


@router.get(
    "/me",
    response_model=UserMeResponse,
)
def me(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserMeResponse:
    """Retrieve current authenticated user profile and entry count."""
    vault = db.get(Vault, current_user.id)
    entry_count = 0
    if vault is not None and isinstance(vault.blob, dict):
        entries = vault.blob.get("entries")
        if isinstance(entries, list):
            entry_count = len(entries)

    return UserMeResponse(
        id=current_user.id,
        username=current_user.username,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        entry_count=entry_count,
    )
