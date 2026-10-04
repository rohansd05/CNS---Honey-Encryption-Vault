"""JWT helpers and FastAPI security dependencies.

Owner: T2 — Tanuj (app core).

Invariants (AGENTS.md §1):
- Tokens carry no master password, no seed, no derived key.
- Security errors are generic (no information leak).
"""

from __future__ import annotations

import datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db

_bearer = HTTPBearer(auto_error=False)


def create_access_token(user: object) -> str:
    """Return a signed HS256 JWT.

    Claims exactly as in docs/api-contract.md §0.3:
    ``sub`` (user id), ``username``, ``is_admin``, ``iat``, ``exp``.
    """
    settings = get_settings()
    now = datetime.datetime.now(datetime.UTC)
    exp = now + datetime.timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": user.id,  # type: ignore[attr-defined]
        "username": user.username,  # type: ignore[attr-defined]
        "is_admin": user.is_admin,  # type: ignore[attr-defined]
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.

    Raises HTTPException 401 on any failure (expired, invalid signature, etc.).
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> object:
    """FastAPI dependency — resolves to the authenticated User or raises 401."""
    from app.models.core import User

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub", "")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(
    current_user: Annotated[object, Depends(get_current_user)],
) -> object:
    """FastAPI dependency — requires ``is_admin=True``; raises 403 otherwise."""
    if not current_user.is_admin:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    return current_user
