"""Alerts service for recording and retrieving security alerts.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §8, api-contract.md §6).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Alert

logger = logging.getLogger(__name__)


def create_alert(
    db: Session,
    username: str,
    user_id: str | None = None,
    kind: str = "HONEYWORD_LOGIN",
    severity: str = "critical",
    sweetword_index: int | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
) -> Alert:
    """Record a security alert in the database."""
    alert = Alert(
        user_id=user_id,
        username=username,
        kind=kind,
        severity=severity,
        sweetword_index=sweetword_index,
        source_ip=source_ip,
        user_agent=user_agent,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    logger.warning(
        "Security alert created: kind=%s severity=%s user=%s sweetword_index=%s ip=%s",
        kind,
        severity,
        username,
        sweetword_index,
        source_ip,
    )
    return alert


def get_alerts(db: Session, limit: int = 50) -> list[Alert]:
    """Retrieve the most recent security alerts, newest first."""
    stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())
