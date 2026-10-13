"""FastAPI app for the honeychecker service.

Owner: T2 — Rohan. Run from ``honeychecker/``: ``uvicorn app.main:app --reload --port 8001``.
Internal API (docs/api-contract.md §Honeychecker):
* ``POST /hc/register``
* ``POST /hc/check``
* ``GET /hc/alarms``
* ``GET /hc/health``
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import __version__
from app.db import Base, engine, get_db
from app.models import Alarm, UserIndex
from app.schemas import (
    AlarmOut,
    CheckRequest,
    CheckResponse,
    HealthResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.security import verify_caller

logger = logging.getLogger(__name__)

DbSession = Annotated[Session, Depends(get_db)]

router = APIRouter(prefix="/hc", tags=["honeychecker"])


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    """Liveness probe (unauthenticated). Checks database connectivity."""
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database connectivity check failed during health probe")
        db_status = "down"

    return HealthResponse(
        status="ok",
        service="honeychecker",
        version=__version__,
        db=db_status,
    )


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
    dependencies=[Depends(verify_caller)],
)
def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    """Register a user's real sweetword index.

    Never returns or logs the real index.
    """
    existing = db.scalar(select(UserIndex).where(UserIndex.user_id == payload.user_id))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already registered",
        )

    user_index = UserIndex(user_id=payload.user_id, real_index=payload.index)
    db.add(user_index)
    db.commit()

    logger.info("Successfully registered sweetword index for user_id=%s", payload.user_id)
    return RegisterResponse(status="registered")


@router.post(
    "/check",
    response_model=CheckResponse,
    dependencies=[Depends(verify_caller)],
)
def check(payload: CheckRequest, db: DbSession) -> CheckResponse:
    """Check a submitted sweetword index against the stored real index.

    If the user is unknown or the index does not match, records an Alarm
    and returns match=False. Never returns or logs the real index.
    """
    user_index = db.scalar(select(UserIndex).where(UserIndex.user_id == payload.user_id))
    if user_index is None:
        alarm = Alarm(
            user_id=payload.user_id,
            claimed_index=payload.index,
            kind="UNKNOWN_USER",
        )
        db.add(alarm)
        db.commit()
        logger.warning(
            "Alarm recorded: check attempt for unknown user_id=%s with claimed_index=%d",
            payload.user_id,
            payload.index,
        )
        return CheckResponse(match=False)

    if user_index.real_index == payload.index:
        logger.info("Check succeeded for user_id=%s", payload.user_id)
        return CheckResponse(match=True)

    alarm = Alarm(
        user_id=payload.user_id,
        claimed_index=payload.index,
        kind="HONEYWORD_MISMATCH",
    )
    db.add(alarm)
    db.commit()
    logger.warning(
        "Alarm recorded: honeyword mismatch for user_id=%s with claimed_index=%d",
        payload.user_id,
        payload.index,
    )
    return CheckResponse(match=False)


@router.get(
    "/alarms",
    response_model=list[AlarmOut],
    dependencies=[Depends(verify_caller)],
)
def list_alarms(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=1000, description="Max number of alarms to return")] = 50,
) -> list[Alarm]:
    """Retrieve recorded alarms, ordered newest first."""
    stmt = select(Alarm).order_by(Alarm.created_at.desc()).limit(limit)
    alarms = list(db.scalars(stmt).all())
    return alarms


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan context. Creates database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Build the honeychecker app. No CORS: it is never called from a browser."""
    app = FastAPI(
        title="HoneyVault Honeychecker",
        version=__version__,
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
