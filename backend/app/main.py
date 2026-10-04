"""FastAPI application factory for ``honeyvault-api``.

Owner: T2 — Tanuj (app core). Run from ``backend/``: ``uvicorn app.main:app --reload --port 8000``.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.api import admin, attack, auth, eval, health, shares, users, vault
from app.config import get_settings
from app.errors import (
    entry_not_found_handler,
    invalid_input_error_handler,
    validation_error_handler,
)
from app.rate_limit import limiter, rate_limit_handler

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build the FastAPI app: CORS from settings, all routers, handlers, limiter."""
    settings = get_settings()
    app = FastAPI(
        title="HoneyVault API",
        version=__version__,
        description="Honey Encryption password vault — see docs/api-contract.md.",
    )

    # ---- Rate limiter ----
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Error handlers ----
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Map honeycore errors (imported lazily so the app starts without honeycore).
    try:
        from honeycore.interfaces import InvalidInputError

        app.add_exception_handler(InvalidInputError, invalid_input_error_handler)
    except ImportError:
        logger.warning(
            "honeycore.interfaces not available; InvalidInputError handler not registered"
        )

    try:
        from app.services.errors import EntryNotFoundError  # defined by T2 in services

        app.add_exception_handler(EntryNotFoundError, entry_not_found_handler)
    except ImportError:
        logger.debug("app.services.errors not present yet; EntryNotFoundError handler deferred")

    # ---- Routers ----
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
