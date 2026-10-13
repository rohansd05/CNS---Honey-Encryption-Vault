"""slowapi rate-limiter configuration.

Owner: T2 — Tanuj (app core).
Rate limits per docs/api-contract.md §0.4.
"""

from __future__ import annotations

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Global limiter keyed by client IP.
limiter = Limiter(key_func=get_remote_address)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Return ``429 {"detail": "Rate limit exceeded"}`` with a ``Retry-After`` header.

    Replaces slowapi's default ``{"error": "..."}`` body (api-contract.md §0.4).
    """
    retry_after = getattr(exc, "retry_after", None) or 60
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded"},
        headers={"Retry-After": str(int(retry_after))},
    )
