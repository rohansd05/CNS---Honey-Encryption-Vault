"""Security headers middleware for HoneyVault API.

Owner: T5 — Aryan (security headers & evaluation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.types import ASGIApp, Message, Receive, Scope, Send

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.config import Settings

DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net data:; "
    "frame-ancestors 'none'"
)
API_CSP = "default-src 'none'; frame-ancestors 'none'"


class SecurityHeadersMiddleware:
    """Pure ASGI middleware adding defense-in-depth HTTP security headers."""

    def __init__(self, app: ASGIApp, enable_hsts: bool = False) -> None:
        self.app = app
        self.enable_hsts = enable_hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw_headers = list(message.get("headers", []))
                existing_names = {
                    k.lower() if isinstance(k, bytes) else k.encode("latin-1").lower()
                    for k, _ in raw_headers
                }

                headers_to_add: list[tuple[bytes, bytes]] = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer"),
                    (
                        b"permissions-policy",
                        b"camera=(), microphone=(), geolocation=()",
                    ),
                    (b"cross-origin-opener-policy", b"same-origin"),
                ]

                if path.startswith("/api/") or path == "/api":
                    headers_to_add.append((b"cache-control", b"no-store"))

                if path in DOCS_PATHS or path.startswith(("/docs/", "/redoc/")):
                    headers_to_add.append((b"content-security-policy", DOCS_CSP.encode("latin-1")))
                else:
                    headers_to_add.append((b"content-security-policy", API_CSP.encode("latin-1")))

                if self.enable_hsts:
                    headers_to_add.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )

                for name, val in headers_to_add:
                    if name not in existing_names:
                        raw_headers.append((name, val))
                        existing_names.add(name)

                message["headers"] = raw_headers

            await send(message)

        await self.app(scope, receive, send_wrapper)


def add_security_headers(app: FastAPI, settings: Settings) -> None:
    """Register SecurityHeadersMiddleware with HSTS enabled only in production."""
    enable_hsts = settings.app_env == "production"
    app.add_middleware(SecurityHeadersMiddleware, enable_hsts=enable_hsts)
