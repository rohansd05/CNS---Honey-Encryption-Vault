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
import ssl
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status

from app.config import Settings, get_settings

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


def _validate_mtls_config(settings: Settings) -> tuple[Path, Path, Path]:
    """Validate mTLS certificates, private key, and CA trust store.

    Raises RuntimeError if any required file or certificate is missing or invalid.
    Returns (server_cert_path, server_key_path, ca_cert_path).
    """
    # 1. Trusted Service CA
    ca_path = Path(settings.hc_trusted_ca_cert_path)
    if not ca_path.is_file():
        raise RuntimeError(
            f"mTLS transport requires a Service CA certificate. "
            f"File not found: '{settings.hc_trusted_ca_cert_path}'"
        )
    try:
        from cryptography import x509 as _x509

        ca_data = ca_path.read_bytes()
        _x509.load_pem_x509_certificate(ca_data)
    except Exception as exc:
        raise RuntimeError(
            f"Invalid Service CA certificate PEM '{settings.hc_trusted_ca_cert_path}': {exc}"
        ) from exc

    # 2. Server Certificate
    cert_path = Path(settings.hc_server_cert_path)
    if not cert_path.is_file():
        raise RuntimeError(
            f"mTLS transport requires a server certificate. "
            f"File not found: '{settings.hc_server_cert_path}'"
        )
    try:
        cert_data = cert_path.read_bytes()
        _x509.load_pem_x509_certificate(cert_data)
    except Exception as exc:
        raise RuntimeError(
            f"Invalid server certificate PEM '{settings.hc_server_cert_path}': {exc}"
        ) from exc

    # 3. Server Private Key
    key_path = Path(settings.hc_server_key_path)
    if not key_path.is_file():
        raise RuntimeError(
            f"mTLS transport requires a server private key. "
            f"File not found: '{settings.hc_server_key_path}'"
        )
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key_data = key_path.read_bytes()
        priv = serialization.load_pem_private_key(key_data, password=None)
        if not isinstance(priv, ec.EllipticCurvePrivateKey):
            raise RuntimeError("Server private key must be an EC private key")
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Invalid server private key PEM '{settings.hc_server_key_path}': {exc}"
        ) from exc

    return cert_path, key_path, ca_path


def get_uvicorn_ssl_kwargs(settings: Settings | None = None) -> dict[str, Any]:
    """Return SSL keyword arguments for uvicorn matching HC_TRANSPORT.

    - ``mtls``: returns ssl kwargs (``ssl_certfile``, ``ssl_keyfile``, ``ssl_ca_certs``,
      ``ssl_cert_reqs``).
      Fails closed (raises RuntimeError) if certificates or keys are missing or invalid.
    - ``plain`` / ``signed``: returns ``{}``.
    """
    s = settings or get_settings()
    if s.hc_transport != "mtls":
        return {}

    cert_path, key_path, ca_path = _validate_mtls_config(s)
    return {
        "ssl_certfile": str(cert_path),
        "ssl_keyfile": str(key_path),
        "ssl_ca_certs": str(ca_path),
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    }


def validate_transport_config(settings: Settings | None = None) -> None:
    """Fail fast if the selected transport mode's credentials are absent or invalid."""
    s = settings or get_settings()
    if s.hc_transport == "signed":
        _load_trusted_ca_pems(s)
    elif s.hc_transport == "mtls":
        _validate_mtls_config(s)


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
        scope = request.scope
        # Verify request arrived over HTTPS. Plain HTTP requests are rejected.
        if scope.get("scheme") != "https":
            logger.warning(
                "verify_caller: mTLS transport requires HTTPS scheme, got %r",
                scope.get("scheme"),
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="unauthorized caller",
            )

        tls_ext = scope.get("extensions", {})
        peer_cert_der: bytes | None = None

        # uvicorn may expose the peer cert under scope["extensions"]["tls"]
        # as a dict with key "client_cert_der" or directly in scope.
        tls_info = tls_ext.get("tls", {})
        if isinstance(tls_info, dict):
            peer_cert_der = tls_info.get("client_cert_der")
        if peer_cert_der is None and "client_cert_der" in scope:
            peer_cert_der = scope["client_cert_der"]

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
