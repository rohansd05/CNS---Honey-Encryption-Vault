"""Caller authentication for the honeychecker (PROJECT-BRIEF.md §10).

Owner: T4 — Parth. Placeholder.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.config import get_settings


def verify_caller(request: Request) -> None:
    """Owned by Parth, replaced in Phase 2."""
    settings = get_settings()
    if settings.hc_transport == "plain":
        return None
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="transport not implemented yet (T4-Parth, Phase 2)",
    )
