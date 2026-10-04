"""Global exception handlers for the HoneyVault API.

Owner: T2 — Tanuj (app core).

Security note (AGENTS.md §1.6, api-contract.md §0.1):
- The FastAPI default RequestValidationError handler echoes the submitted
  ``input`` (and ``ctx``) fields back to the caller — this can leak passwords.
  Our custom handler strips those fields before returning the 422 body.
- All error messages are generic; no passwords, keys or seeds are included.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 handler — strips ``input`` and ``ctx`` from every error to prevent
    submitted values (e.g. passwords) from appearing in responses or logs.
    """
    cleaned_errors = []
    for err in exc.errors():
        cleaned_errors.append(
            {
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            }
        )
    return JSONResponse(
        status_code=422,
        content={"detail": cleaned_errors},
    )


async def invalid_input_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map ``honeycore.InvalidInputError`` → 422 with a safe detail string."""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


async def entry_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    """Map ``EntryNotFoundError`` → 404 with a safe detail string."""
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )
