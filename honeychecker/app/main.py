"""FastAPI app for the honeychecker service.

Owner: T2 — Rohan. Run from ``honeychecker/``: ``uvicorn app.main:app --reload --port 8001``.
Internal API (docs/api-contract.md §Honeychecker): ``/hc/register``, ``/hc/check``,
``/hc/alarms`` (TODO T2 — Rohan) and ``/hc/health``.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app import __version__

router = APIRouter(prefix="/hc", tags=["honeychecker"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness probe (unauthenticated)."""
    return {"status": "ok", "service": "honeychecker", "version": __version__}


# TODO(T2 — Rohan): POST /hc/register, POST /hc/check, GET /hc/alarms
# (protected by the app.security dependency from T4 — Parth).


def create_app() -> FastAPI:
    """Build the honeychecker app. No CORS: it is never called from a browser."""
    app = FastAPI(title="HoneyVault Honeychecker", version=__version__)
    app.include_router(router)
    return app


app = create_app()
