"""``/api/users``: user identity lookup (public key + X.509 certificate).

Owner: T2 — Rohan. Contract: docs/api-contract.md §4.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.core import User
from app.schemas.users import UserIdentityResponse
from app.security import get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get(
    "/{username}/identity",
    response_model=UserIdentityResponse,
)
def get_user_identity(
    username: str,
    db: Annotated[Session, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> UserIdentityResponse:
    """Retrieve public identity keys and certificate for a user."""
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.identity_public_pem or not user.identity_cert_pem:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User has no identity keys",
        )

    return UserIdentityResponse(
        username=user.username,
        public_key_pem=user.identity_public_pem,
        certificate_pem=user.identity_cert_pem,
    )
