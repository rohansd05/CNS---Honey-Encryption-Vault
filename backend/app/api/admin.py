"""Admin endpoints: security breach alerts and auditing.

Owner: T2 — Rohan. Contract: docs/api-contract.md §6.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.core import Alert, User
from app.schemas.auth import AlertResponse
from app.security import require_admin
from app.services import alerts

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/alerts", response_model=list[AlertResponse])
def get_admin_alerts(
    current_admin: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=1000, description="Max alerts to return")] = 50,
) -> list[Alert]:
    """Retrieve security breach alerts, newest first. Requires admin privileges."""
    return alerts.get_alerts(db, limit=limit)
