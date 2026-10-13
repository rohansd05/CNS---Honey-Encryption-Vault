"""``/api/attack``: DEMO_MODE-only attacker console endpoints.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §8 (frozen).
All endpoints exist only when settings.demo_mode (else 404), require no auth,
and are rate limited to 10/minute.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.config import Settings, get_settings
from app.deps import get_db, get_honeycore
from app.models.core import Alert
from app.rate_limit import limiter
from app.schemas.attack import (
    AttackAlarmResponse,
    DictionaryAttackRequest,
    DictionaryAttackResponse,
    StolenHoneywordsResponse,
    StolenVaultResponse,
)
from app.services import attack_service
from honeycore.factory import HoneyCore


def require_demo_mode(
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Ensure DEMO_MODE is enabled; otherwise return 404."""
    if not settings.demo_mode:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo mode disabled",
        )


router = APIRouter(
    prefix="/api/attack",
    tags=["attack"],
    dependencies=[Depends(require_demo_mode)],
)


@router.get("/stolen-vault", response_model=StolenVaultResponse)
@limiter.limit("10/minute")
def get_stolen_vault(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StolenVaultResponse:
    """Return the demo user's honey vault and conventional baseline vault blobs."""
    data = attack_service.get_stolen_vault(db=db, settings=settings)
    return StolenVaultResponse.model_validate(data)


@router.post("/dictionary", response_model=DictionaryAttackResponse)
@limiter.limit("10/minute")
async def run_dictionary_attack(
    request: Request,
    payload: DictionaryAttackRequest,
    db: Annotated[Session, Depends(get_db)],
    honeycore: Annotated[HoneyCore, Depends(get_honeycore)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DictionaryAttackResponse:
    """Run dictionary attack comparing honey vault decoys vs baseline oracle."""
    result = await run_in_threadpool(
        attack_service.execute_dictionary_attack,
        db=db,
        honeycore=honeycore,
        settings=settings,
        max_guesses=payload.max_guesses,
        custom_guesses=payload.custom_guesses,
    )
    return DictionaryAttackResponse.model_validate(result)


@router.get("/stolen-honeywords", response_model=StolenHoneywordsResponse)
@limiter.limit("10/minute")
def get_stolen_honeywords(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> StolenHoneywordsResponse:
    """Return the demo user's public honeywords and cracked sweetwords list."""
    data = attack_service.get_stolen_honeywords(db=db, settings=settings)
    return StolenHoneywordsResponse.model_validate(data)


@router.get("/alarms", response_model=list[AttackAlarmResponse])
@limiter.limit("10/minute")
def get_attack_alarms(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: Annotated[int, Query(ge=1, le=20, description="Max alarms to return")] = 20,
) -> list[Alert]:
    """Retrieve recent alerts for the demo user, newest first (up to limit)."""
    return attack_service.get_demo_alarms(db=db, settings=settings, limit=limit)
