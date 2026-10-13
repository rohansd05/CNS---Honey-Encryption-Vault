"""Alerts service for recording and retrieving security alerts.

Owner: T2 — Rohan / Tanuj. Phase 1 (PROJECT-BRIEF.md §8, api-contract.md §6).
"""

from __future__ import annotations

import datetime
import logging
import threading

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import Alert

logger = logging.getLogger(__name__)

_last_alert_time: datetime.datetime | None = None
_alert_time_lock = threading.Lock()


def _monotonic_utc_now() -> datetime.datetime:
    """Return a strictly monotonic UTC datetime to prevent timestamp collisions."""
    global _last_alert_time
    with _alert_time_lock:
        now = datetime.datetime.now(datetime.UTC)
        if _last_alert_time is not None and now <= _last_alert_time:
            now = _last_alert_time + datetime.timedelta(microseconds=1)
        _last_alert_time = now
        return now


def create_alert(
    db: Session,
    username: str,
    user_id: str | None = None,
    kind: str = "HONEYWORD_LOGIN",
    severity: str = "critical",
    sweetword_index: int | None = None,
    source_ip: str | None = None,
    user_agent: str | None = None,
    created_at: datetime.datetime | None = None,
) -> Alert:
    """Record a security alert in the database with monotonic timestamp."""
    alert_time = created_at or _monotonic_utc_now()
    alert = Alert(
        user_id=user_id,
        username=username,
        kind=kind,
        severity=severity,
        sweetword_index=sweetword_index,
        source_ip=source_ip,
        user_agent=user_agent,
        created_at=alert_time,
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
    """Retrieve the most recent security alerts, newest first with deterministic tie-breaker."""
    stmt = select(Alert).order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit)
    return list(db.scalars(stmt).all())
