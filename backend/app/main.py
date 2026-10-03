"""FastAPI application factory for ``honeyvault-api``.

Owner: T2 — Tanuj (app core). Run from ``backend/``: ``uvicorn app.main:app --reload --port 8000``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import admin, attack, auth, eval, health, shares, users, vault
from app.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build the FastAPI app: CORS from settings, all routers, optional T5 utils router."""
    settings = get_settings()
    app = FastAPI(
        title="HoneyVault API",
        version=__version__,
        description="Honey Encryption password vault — see docs/api-contract.md.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (health, auth, vault, users, shares, attack, admin, eval):
        app.include_router(module.router)

    # T5 (Aryan) utilities are optional: the app must start without them.
    try:
        from app.api import utils
    except ImportError:
        logger.info("app.api.utils not present; /api/utils/* disabled")
    else:
        app.include_router(utils.router)

    return app


app = create_app()
