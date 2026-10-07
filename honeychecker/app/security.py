"""Caller authentication for the honeychecker (PROJECT-BRIEF.md §10, ADR-005).

Owner: T4 — Parth. Phase 4 (feat/t4-hc-security).

Transport modes (HC_TRANSPORT / HONEYCHECKER_TRANSPORT):
- ``plain``  — local development only; all callers are allowed.
- ``signed`` — Render (TLS terminated at proxy).  Every protected request must carry
               X-HV-* headers signed by the api-client cert.  The cert is verified
               against the Service CA only (HC_TRUSTED_CA_CERT_B64 or
               HC_TRUSTED_CA_CERT_PATH), so a user identity cert (Root → Issuing CA
               → username) is always rejected.
- ``mtls``   — docker-compose.  TLS (--ssl-cert-reqs 2) is enforced by uvicorn; the
               peer cert CN is checked when ASGI exposes it.  Because the Service CA
               only ever issues the api-client cert, all valid mTLS peers are already
               the API — the CN check is defence-in-depth.

``/hc/health`` is always open (no ``Depends(verify_caller)`` on that route).
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status

from app.config import get_settings

if TYPE_CHECKING:
    pass  # kept for future type-only imports

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singleton replay cache — shared across all requests in a process.
# ---------------------------------------------------------------------------

# Import lazily inside _get_replay_cache() so tests can monkeypatch transport.
_replay_cache: object | None = None


def _get_replay_cache():  # type: ignore[return]
    """Return (creating on first call) the process-wide ReplayCache."""
    global _replay_cache  # noqa: PLW0603
    if _replay_cache is None:
        from honeycore.transport import ReplayCache

        _replay_cache = ReplayCache(ttl_seconds=300)
    return _replay_cache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_trusted_ca_pems(settings) -> list[bytes]:  # type: ignore[return]
    """Return the list of PEM bytes to use as the Service CA trust store.

    Priority:
    1. ``HC_TRUSTED_CA_CERT_B64`` env var (base64-encoded PEM) — used on Render.
    2. ``HC_TRUSTED_CA_CERT_PATH`` env var / default path — used locally / compose.

    Raises ``RuntimeError`` if neither source yields a certificate.
    This is intentional: a missing trust config is a hard startup error, not a
    runtime 401 — the server should refuse to start rather than silently allow all.
    """
    if settings.hc_trusted_ca_cert_b64:
        try:
            pem = base64.b64decode(settings.hc_trusted_ca_cert_b64)
            if pem:
                return [pem]
        except Exception as exc:
            raise RuntimeError(f"HC_TRUSTED_CA_CERT_B64 is not valid base64: {exc}") from exc

    path = Path(settings.hc_trusted_ca_cert_path)
    if path.is_file():
        return [path.read_bytes()]

    raise RuntimeError(
        "Signed transport requires a Service CA certificate. "
        "Set HC_TRUSTED_CA_CERT_B64 (base64 PEM) or ensure "
        f"HC_TRUSTED_CA_CERT_PATH ({path}) exists."
    )


# ---------------------------------------------------------------------------
# Startup validation — called once at import time when transport != plain
# ---------------------------------------------------------------------------


def _validate_signed_config() -> None:
    """Fail fast at process startup if the signed-mode trust config is missing."""
    settings = get_settings()
    if settings.hc_transport == "signed":
        _load_trusted_ca_pems(settings)  # raises RuntimeError if config absent


# ---------------------------------------------------------------------------
# verify_caller — FastAPI dependency
# ---------------------------------------------------------------------------


async def verify_caller(request: Request) -> None:
    """Async FastAPI dependency: authenticate the caller based on HC_TRANSPORT.

    - ``plain``: allow unconditionally (local dev only).
    - ``signed``: verify X-HV-* ECDSA signed request against the Service CA.
      Any verification failure → 401 ``{"detail": "unauthorized caller"}``
      (no detail leak to the caller; full detail is logged server-side).
    - ``mtls``:  TLS is enforced by uvicorn (``--ssl-cert-reqs 2``,
      ``--ssl-ca-certs`` = Service CA).  If the ASGI scope exposes the peer
      cert, the CN is checked; otherwise we allow (the uvicorn layer already
      enforced a valid Service-CA chain).

    ``/hc/health`` is intentionally not protected — it has no ``Depends(verify_caller)``.
    """
    settings = get_settings()
    transport = settings.hc_transport

    # ------------------------------------------------------------------
    # plain — local dev, no auth.
    # ------------------------------------------------------------------
    if transport == "plain":
        return

    # ------------------------------------------------------------------
    # signed — ECDSA signed request (Render / any TLS-terminated proxy).
    # ------------------------------------------------------------------
    if transport == "signed":
        from honeycore.interfaces import InvalidSignatureError
        from honeycore.transport import verify_signed_request

        try:
            trusted_ca_pems = _load_trusted_ca_pems(settings)
        except RuntimeError as exc:
            # Trust config absent — this should have been caught at startup.
            logger.critical("verify_caller: trust config missing: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized caller",
            ) from exc

        body = await request.body()

        # Reconstruct path + query string for the canonical request.
        path = request.url.path
        query = request.url.query
        path_with_query = f"{path}?{query}" if query else path

        # FastAPI lowercases headers. Map them back so verify_signed_request finds them.
        headers: dict[str, str] = {}
        for k, v in request.headers.items():
            k_lower = k.lower()
            if k_lower == "x-hv-cert":
                headers["X-HV-Cert"] = v
            elif k_lower == "x-hv-timestamp":
                headers["X-HV-Timestamp"] = v
            elif k_lower == "x-hv-nonce":
                headers["X-HV-Nonce"] = v
            elif k_lower == "x-hv-signature":
                headers["X-HV-Signature"] = v
            else:
                headers[k] = v

        try:
            verify_signed_request(
                method=request.method,
                path=path_with_query,
                body=body,
                headers=headers,
                trusted_ca_pems=trusted_ca_pems,
                allowed_cn=settings.hc_allowed_client_cn,
                replay_cache=_get_replay_cache(),
            )
        except InvalidSignatureError as exc:
            # Log the real reason server-side; return a generic error to the caller.
            logger.warning("verify_caller: signed request rejected: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized caller",
            ) from exc
        return

    # ------------------------------------------------------------------
    # mtls — docker-compose; uvicorn enforces the TLS handshake.
    # ------------------------------------------------------------------
    if transport == "mtls":
        # Uvicorn with --ssl-cert-reqs 2 (CERT_REQUIRED) and
        # --ssl-ca-certs = service-ca.crt has already verified the chain at
        # the TLS layer before this coroutine runs.  We add a CN check when
        # the ASGI scope exposes the peer certificate.
        #
        # NOTE: Starlette / uvicorn do not standardise how TLS peer certs
        # appear in the ASGI scope.  If the field is absent we trust that the
        # TLS handshake was the gatekeeper.  The Service CA only ever issues
        # the api-client cert, so any valid mTLS peer is already the API.
        scope = request.scope
        tls_ext = scope.get("extensions", {})
        peer_cert_der: bytes | None = None

        # uvicorn may expose the peer cert under scope["extensions"]["tls"]
        # as a dict with key "client_cert_der" or similar.
        tls_info = tls_ext.get("tls", {})
        if isinstance(tls_info, dict):
            peer_cert_der = tls_info.get("client_cert_der")

        if peer_cert_der is not None:
            # Parse the DER cert and check the CN.
            from cryptography import x509 as _x509
            from cryptography.x509.oid import NameOID
            from honeycore.interfaces import InvalidSignatureError

            try:
                cert = _x509.load_der_x509_certificate(peer_cert_der)
                attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                cn = attrs[0].value if attrs else ""
                if cn != settings.hc_allowed_client_cn:
                    raise InvalidSignatureError(
                        f"mTLS peer CN {cn!r} != {settings.hc_allowed_client_cn!r}"
                    )
            except InvalidSignatureError as exc:
                logger.warning("verify_caller: mTLS CN check failed: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="unauthorized caller",
                ) from exc
            except Exception as exc:
                logger.warning("verify_caller: mTLS cert parse error: %s", exc)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="unauthorized caller",
                ) from exc
        else:
            # Peer cert not exposed by the ASGI extension — trust the TLS layer.
            logger.debug(
                "verify_caller: mTLS peer cert not in ASGI scope; "
                "trusting uvicorn TLS enforcement (Service CA only issues api-client)."
            )
        return

    # Unknown transport value — should never happen because Settings validates the Literal.
    logger.error("verify_caller: unknown transport %r — denying request", transport)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="unauthorized caller",
    )
