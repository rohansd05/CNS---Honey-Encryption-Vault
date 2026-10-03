"""``GET /api/health`` — liveness probe used by Render, CI smoke tests and the frontend.

Owner: T2 — Tanuj (app core).
"""

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Report service status, version and which honeycore implementation is loaded."""
    return {
        "status": "ok",
        "version": __version__,
        "honeycore_impl": get_settings().honeycore_impl,
        # TODO(T2 — Rohan): ping the honeychecker and report "ok" | "down".
        "honeychecker": "unknown",
    }
