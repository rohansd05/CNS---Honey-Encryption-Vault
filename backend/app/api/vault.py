"""``/api/vault``: unlock (ALWAYS 200), entry CRUD, export of the vault blob.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §3, §0.5.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.deps import get_db, get_honeycore
from app.models.core import User
from app.rate_limit import limiter
from app.schemas.vault import (
    DecodedEntryResponse,
    EntryCreateRequest,
    EntryMutationResponse,
    EntryUpdateRequest,
    SigilResponse,
    UnlockRequest,
    UnlockResponse,
)
from app.security import get_current_user
from app.services import vault_service
from honeycore.factory import HoneyCore
from honeycore.interfaces import Entry, EntryNotFoundError

router = APIRouter(prefix="/api/vault", tags=["vault"])


def _user_id_key_func(request: Request) -> str:
    """Extract user id from JWT Bearer token for per-user rate limiting."""
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        token = auth[7:].strip()
        try:
            from app.security import decode_token

            payload = decode_token(token)
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except Exception:  # noqa: S110
            # Token invalid/expired; fall back to client IP for rate limiting
            pass
    from slowapi.util import get_remote_address

    return get_remote_address(request)


@router.post("/unlock", response_model=UnlockResponse)
@limiter.limit(lambda: get_settings().rate_limit_unlock, key_func=_user_id_key_func)
def unlock_vault_endpoint(
    request: Request,
    payload: UnlockRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> UnlockResponse:
    """Unlock the user's vault.

    ALWAYS returns 200 with a well-formed vault and sigil for any password.
    Never logs the request body or password.
    """
    result = vault_service.unlock_vault(
        db=db,
        user=current_user,
        honeycore=honeycore,
        master_password=payload.master_password,
    )
    return UnlockResponse(
        entries=[
            DecodedEntryResponse(
                id=e.id,
                service=e.service,
                username=e.username,
                password=e.password,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in result.entries
        ],
        sigil=SigilResponse(
            emojis=list(result.sigil.emojis),
            color=result.sigil.color,
        ),
    )


@router.post(
    "/entries",
    response_model=EntryMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_entry_endpoint(
    payload: EntryCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> EntryMutationResponse:
    """Add a new entry to the user's vault."""
    entry = Entry(
        service=payload.service,
        username=payload.username,
        password=payload.password,
    )
    entry_id = vault_service.add_entry(
        db=db,
        user=current_user,
        honeycore=honeycore,
        master_password=payload.master_password,
        entry=entry,
    )
    return EntryMutationResponse(id=entry_id)


@router.put("/entries/{entry_id}", response_model=EntryMutationResponse)
def update_entry_endpoint(
    entry_id: str,
    payload: EntryUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> EntryMutationResponse:
    """Update an existing entry in the user's vault."""
    entry = Entry(
        service=payload.service,
        username=payload.username,
        password=payload.password,
    )
    try:
        updated_id = vault_service.update_entry(
            db=db,
            user=current_user,
            honeycore=honeycore,
            master_password=payload.master_password,
            entry_id=entry_id,
            entry=entry,
        )
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        ) from exc
    return EntryMutationResponse(id=updated_id)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry_endpoint(
    entry_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> Response:
    """Delete an entry from the user's vault."""
    try:
        vault_service.delete_entry(
            db=db,
            user=current_user,
            honeycore=honeycore,
            entry_id=entry_id,
        )
    except EntryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/export")
def export_vault_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
) -> dict[str, Any]:
    """Export the raw vault blob v1."""
    return vault_service.export_vault(
        db=db,
        user=current_user,
        honeycore=honeycore,
    )
