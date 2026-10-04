"""``GET /api/health`` — liveness probe used by Render, CI smoke tests and the frontend.

Owner: T2 — Tanuj (app core).
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app import __version__
from app.config import get_settings
from app.services.honeychecker_client import (
    HoneycheckerClient,
    get_honeychecker_client,
)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health(
    request: Request,
    hc_client: Annotated[HoneycheckerClient, Depends(get_honeychecker_client)],
) -> dict[str, str]:
    """Report service status, version, honeycore implementation, and honeychecker connectivity."""
    settings = get_settings()
    hc_status = "unknown"

    # Check connectivity if HONEYCHECKER_URL is set in environment or overridden in tests.
    is_env_set = bool(os.environ.get("HONEYCHECKER_URL"))
    is_overridden = get_honeychecker_client in request.app.dependency_overrides

    if (is_env_set or is_overridden) and bool(settings.honeychecker_url):
        try:
            hc_status = "ok" if hc_client.health() else "down"
        except Exception:
            hc_status = "down"

    return {
        "status": "ok",
        "version": __version__,
        "honeycore_impl": settings.honeycore_impl,
        "honeychecker": hc_status,
    }
