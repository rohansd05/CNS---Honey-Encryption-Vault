"""``/api/shares``: secure entry sharing (seal, inbox, sent, open, tamper).

Owner: T2 — Rohan. Contract: docs/api-contract.md §5.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.deps import get_db, get_honeycore
from app.models.core import User
from app.schemas.shares import (
    OpenShareResponse,
    ShareCreateRequest,
    ShareCreateResponse,
    ShareInboxItem,
    ShareSentItem,
    TamperShareResponse,
)
from app.security import get_current_user
from app.services import share_service
from honeycore.factory import HoneyCore

router = APIRouter(prefix="/api/shares", tags=["shares"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ShareCreateResponse,
)
def create_share_endpoint(
    payload: ShareCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> ShareCreateResponse:
    """Seal a credential entry and create an encrypted share for a recipient."""
    share_id = share_service.create_share(
        db,
        current_user,
        honeycore,
        master_password=payload.master_password,
        entry_id=payload.entry_id,
        recipient_username=payload.recipient_username,
    )
    return ShareCreateResponse(share_id=share_id)


@router.get(
    "/inbox",
    response_model=list[ShareInboxItem],
)
def get_inbox_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ShareInboxItem]:
    """Retrieve all incoming shares received by the authenticated user."""
    return share_service.get_inbox_shares(db, current_user)


@router.get(
    "/sent",
    response_model=list[ShareSentItem],
)
def get_sent_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ShareSentItem]:
    """Retrieve all outgoing shares sent by the authenticated user."""
    return share_service.get_sent_shares(db, current_user)


@router.post(
    "/{id}/open",
    response_model=OpenShareResponse,
)
def open_share_endpoint(
    id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> OpenShareResponse:
    """Open, cryptographically verify, and decrypt a received share."""
    return share_service.open_share(db, current_user, honeycore, share_id=id)


@router.post(
    "/{id}/tamper",
    response_model=TamperShareResponse,
)
def tamper_share_endpoint(
    id: str,
    _current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> TamperShareResponse:
    """Flip one ciphertext byte of a stored share envelope (demo mode only)."""
    share_service.tamper_share(db, share_id=id)
    return TamperShareResponse(tampered=True)
