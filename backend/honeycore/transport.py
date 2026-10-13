"""Signed-request scheme for the API -> honeychecker channel (§10, X-HV-* headers).

Owner: T4 — Parth. Phase 3.

Transport modes (HONEYCHECKER_TRANSPORT / HC_TRANSPORT):
- plain  : local dev, no auth.
- mtls   : docker-compose, mutual TLS via ssl.SSLContext; httpx uses cert= + verify=.
- signed : Render (TLS terminated by proxy); ECDSA-P256-SHA256 signature over the
           canonical request, X-HV-* headers, ±60 s clock window, 5-min nonce replay.

Imports: stdlib + cryptography + honeycore.interfaces + honeycore.pki.
NO httpx / FastAPI imports at module level (they are imported lazily inside
httpx_client_kwargs only).
"""

from __future__ import annotations

import base64
import hashlib
import secrets
import ssl
import threading
import time
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from honeycore.interfaces import CertInfo, InvalidSignatureError
from honeycore.pki import PKI

if TYPE_CHECKING:
    pass  # kept for future type-only imports

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SIGNED_INFO = b"honeyvault-transport-v1"
_NONCE_BYTES = 16


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def _b64url_encode(data: bytes) -> str:
    """URL-safe base64 without padding (suitable for HTTP headers)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Decode a URL-safe base64 string that may lack padding."""
    # restore padding
    pad = (4 - len(s) % 4) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(s: str) -> bytes:
    return base64.b64decode(s)


# ---------------------------------------------------------------------------
# 1. canonical_request
# ---------------------------------------------------------------------------


def canonical_request(
    method: str,
    path_with_query: str,
    timestamp: str,
    nonce: str,
    body: bytes,
) -> bytes:
    """Return the bytes to be signed / verified.

    Format::

        METHOD\\n
        PATH_WITH_QUERY\\n
        TIMESTAMP\\n
        NONCE\\n
        SHA256HEX(body)
    """
    body_hash = _sha256hex(body)
    return f"{method.upper()}\n{path_with_query}\n{timestamp}\n{nonce}\n{body_hash}".encode()


# ---------------------------------------------------------------------------
# 2. sign_request
# ---------------------------------------------------------------------------


def sign_request(
    method: str,
    path: str,
    body: bytes,
    client_cert_pem: bytes,
    client_key_pem: bytes,
    *,
    now: float | None = None,
) -> dict[str, str]:
    """Sign an outgoing request and return the X-HV-* header dict.

    Headers produced:
    - ``X-HV-Cert``      — standard base64 of the PEM cert bytes
    - ``X-HV-Timestamp`` — Unix timestamp as a decimal string (integer seconds)
    - ``X-HV-Nonce``     — URL-safe base64 of 16 random bytes (no padding)
    - ``X-HV-Signature`` — standard base64 of the DER-encoded ECDSA signature

    The signature covers ``canonical_request(method, path, ts, nonce, body)``.
    """
    ts = str(int(now if now is not None else time.time()))
    nonce_bytes = secrets.token_bytes(_NONCE_BYTES)
    nonce = _b64url_encode(nonce_bytes)

    to_sign = canonical_request(method, path, ts, nonce, body)

    priv_key = serialization.load_pem_private_key(client_key_pem, password=None)
    if not isinstance(priv_key, ec.EllipticCurvePrivateKey):
        msg = "Client key must be an EC private key"
        raise ValueError(msg)

    der_sig = priv_key.sign(to_sign, ec.ECDSA(hashes.SHA256()))

    return {
        "X-HV-Cert": _b64_encode(client_cert_pem),
        "X-HV-Timestamp": ts,
        "X-HV-Nonce": nonce,
        "X-HV-Signature": _b64_encode(der_sig),
    }


# ---------------------------------------------------------------------------
# 3. ReplayCache
# ---------------------------------------------------------------------------


class ReplayCache:
    """Thread-safe nonce replay cache with TTL-based pruning.

    Args:
        ttl_seconds: How long a nonce is considered valid (default 300 s = 5 min).
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = ttl_seconds
        # Maps nonce -> expiry_timestamp
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        """Remove expired entries. MUST be called with self._lock held."""
        expired = [n for n, exp in self._seen.items() if exp <= now]
        for n in expired:
            del self._seen[n]

    def seen_or_add(self, nonce: str, *, now: float | None = None) -> bool:
        """Return *True* if *nonce* was already seen (replay); add it otherwise.

        Thread-safe. Prunes stale entries on every call.
        """
        t = now if now is not None else time.time()
        with self._lock:
            self._prune(t)
            if nonce in self._seen:
                return True  # replay detected
            self._seen[nonce] = t + self._ttl
            return False


# ---------------------------------------------------------------------------
# 4. verify_signed_request
# ---------------------------------------------------------------------------


def verify_signed_request(
    method: str,
    path: str,
    body: bytes,
    headers: dict[str, str],
    trusted_ca_pems: list[bytes],
    allowed_cn: str,
    replay_cache: ReplayCache,
    *,
    max_skew: int = 60,
    now: float | None = None,
) -> CertInfo:
    """Verify an incoming signed request; return the sender's CertInfo on success.

    Checks (any failure → InvalidSignatureError):
    1. Required headers present.
    2. Cert chain valid, EKU includes clientAuth, CN == allowed_cn.
    3. |now - timestamp| ≤ max_skew seconds.
    4. Nonce not replayed.
    5. ECDSA signature over canonical_request matches.

    Args:
        method: HTTP method (e.g. "POST").
        path: Path + query string (e.g. "/hc/check").
        body: Raw request body bytes.
        headers: Dict of request headers (case-sensitive X-HV-* keys).
        trusted_ca_pems: List of trusted CA certificate PEM bytes (root + issuing).
        allowed_cn: Expected CN of the client cert.
        replay_cache: A shared ReplayCache instance.
        max_skew: Maximum allowed clock skew in seconds (default 60).
        now: Override current time (float Unix timestamp); uses time.time() if None.
    """
    t = now if now is not None else time.time()

    # --- 1. Extract required headers ---
    try:
        cert_b64 = headers["X-HV-Cert"]
        ts_str = headers["X-HV-Timestamp"]
        nonce = headers["X-HV-Nonce"]
        sig_b64 = headers["X-HV-Signature"]
    except KeyError as exc:
        raise InvalidSignatureError(f"Missing header: {exc}") from exc

    # Decode cert PEM (base64-wrapped)
    try:
        cert_pem = _b64_decode(cert_b64)
    except Exception as exc:
        raise InvalidSignatureError(f"X-HV-Cert decode failed: {exc}") from exc

    # --- 2. Verify cert chain (clientAuth required, CN must match) ---
    pki = PKI()
    cert_info = pki.verify_certificate(
        cert_pem,
        trusted_ca_pems,
        expected_cn=allowed_cn,
        require_client_auth=True,
    )

    # --- 3. Timestamp window ---
    try:
        ts = int(ts_str)
    except ValueError as exc:
        raise InvalidSignatureError(f"X-HV-Timestamp not an integer: {exc}") from exc

    if abs(t - ts) > max_skew:
        raise InvalidSignatureError(
            f"Timestamp out of window: skew={abs(t - ts):.1f}s > {max_skew}s"
        )

    # --- 4. Replay check ---
    if replay_cache.seen_or_add(nonce, now=t):
        raise InvalidSignatureError(f"Nonce replay detected: {nonce!r}")

    # --- 5. Signature ---
    try:
        der_sig = _b64_decode(sig_b64)
    except Exception as exc:
        raise InvalidSignatureError(f"X-HV-Signature decode failed: {exc}") from exc

    to_verify = canonical_request(method, path, ts_str, nonce, body)

    from cryptography import x509 as _x509

    sender_cert = _x509.load_pem_x509_certificate(cert_pem)
    pub_key = sender_cert.public_key()
    if not isinstance(pub_key, ec.EllipticCurvePublicKey):
        raise InvalidSignatureError("Client cert key is not an EC key")

    try:
        pub_key.verify(der_sig, to_verify, ec.ECDSA(hashes.SHA256()))
    except Exception as exc:
        raise InvalidSignatureError(f"Signature verification failed: {exc}") from exc

    return cert_info


# ---------------------------------------------------------------------------
# 5. httpx_client_kwargs
# ---------------------------------------------------------------------------


def httpx_client_kwargs(
    mode: str,
    *,
    client_cert_path: str | None = None,
    client_key_path: str | None = None,
    ca_cert_path: str | None = None,
) -> dict:
    """Return keyword arguments for ``httpx.Client(...)`` matching *mode*.

    Modes:
    - ``plain``  — returns ``{}`` (no TLS config; for local dev only).
    - ``mtls``   — returns ``{"cert": (client_cert_path, client_key_path),
                              "verify": ssl.SSLContext}`` trusting *ca_cert_path*.
    - ``signed`` — returns ``{}``; signing is done per-request via :func:`sign_request`.

    Raises ``ValueError`` for an unknown mode or missing paths in mtls mode.
    """
    if mode == "plain":
        return {}

    if mode == "signed":
        return {}

    if mode == "mtls":
        if not client_cert_path or not client_key_path or not ca_cert_path:
            msg = "mtls mode requires client_cert_path, client_key_path, and ca_cert_path"
            raise ValueError(msg)

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.load_verify_locations(ca_cert_path)
        ctx.load_cert_chain(certfile=client_cert_path, keyfile=client_key_path)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = False  # hostname is "honeychecker" (internal)

        return {
            "cert": (client_cert_path, client_key_path),
            "verify": ctx,
        }

    msg = f"Unknown transport mode: {mode!r}. Choose from: plain, mtls, signed."
    raise ValueError(msg)
