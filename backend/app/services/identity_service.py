"""Identity and PKI management service for HoneyVault users.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §9, §10, ADR-006).
Provisions P-256 identity keypairs, wraps private keys with the server KEK,
and issues X.509 certificates signed by the issuing CA.
"""

from __future__ import annotations

import base64
import logging
from typing import TYPE_CHECKING

from app.config import Settings, get_settings
from honeycore.pki import PKI
from honeycore.sharing import Sharing, unwrap_private_key, wrap_private_key

if TYPE_CHECKING:
    from app.models.core import User

logger = logging.getLogger(__name__)


def _decode_pem(val: str | bytes) -> bytes:
    """Decode a PEM certificate or key from base64 or raw bytes."""
    raw = val.encode("utf-8") if isinstance(val, str) else val
    raw = raw.strip()
    if b"-----BEGIN" in raw:
        return raw
    return base64.b64decode(raw)


def _get_kek(secret: str | bytes) -> bytes:
    """Extract a 32-byte key-encryption key from raw string, base64, or hex."""
    raw = secret.encode("utf-8") if isinstance(secret, str) else secret
    raw = raw.strip()
    try:
        b64 = base64.b64decode(raw)
        if len(b64) == 32:
            return b64
    except Exception:  # noqa: S110
        pass
    if len(raw) == 32:
        return raw
    try:
        hx = bytes.fromhex(raw.decode("utf-8"))
        if len(hx) == 32:
            return hx
    except Exception:  # noqa: S110
        pass
    raise ValueError("KEY_WRAP_SECRET must decode to exactly 32 bytes")


def pki_configured(settings: Settings | None = None) -> bool:
    """Return True if all PKI environment settings are configured."""
    s = settings or get_settings()
    return bool(
        s.key_wrap_secret.get_secret_value().strip()
        and s.root_ca_cert_b64.strip()
        and s.issuing_ca_cert_b64.strip()
        and s.issuing_ca_key_b64.get_secret_value().strip()
    )


def provision_identity(user: User, settings: Settings | None = None) -> None:
    """Generate identity keys and X.509 certificate for a user if PKI is configured.

    Stores identity_public_pem, identity_private_wrapped, and identity_cert_pem on the User.
    If PKI is not configured, logs a single warning and leaves identity fields as None.
    """
    s = settings or get_settings()
    if not pki_configured(s):
        logger.warning(
            "PKI is not configured; skipping identity key generation for user %s",
            user.username,
        )
        return

    sharing = Sharing()
    identity_keys = sharing.generate_identity()

    kek = _get_kek(s.key_wrap_secret.get_secret_value())
    wrapped_priv = wrap_private_key(identity_keys.private_pem, kek)

    pki = PKI()
    issuing_cert_pem = _decode_pem(s.issuing_ca_cert_b64)
    issuing_key_pem = _decode_pem(s.issuing_ca_key_b64.get_secret_value())

    cert_pem = pki.issue_user_certificate(
        username=user.username,
        public_pem=identity_keys.public_pem,
        issuer_cert_pem=issuing_cert_pem,
        issuer_key_pem=issuing_key_pem,
        days=365,
    )

    user.identity_public_pem = identity_keys.public_pem.decode("utf-8")
    user.identity_private_wrapped = wrapped_priv
    user.identity_cert_pem = cert_pem.decode("utf-8")


def load_private_key(user: User, settings: Settings | None = None) -> bytes:
    """Unwrap and return the user's private key PEM bytes using KEY_WRAP_SECRET."""
    if not user.identity_private_wrapped:
        raise ValueError("User has no identity private key")
    s = settings or get_settings()
    kek = _get_kek(s.key_wrap_secret.get_secret_value())
    return unwrap_private_key(user.identity_private_wrapped, kek)


def trusted_ca_pems(settings: Settings | None = None) -> list[bytes]:
    """Return [root_ca_pem, issuing_ca_pem] as a list of PEM bytes."""
    s = settings or get_settings()
    if not (s.root_ca_cert_b64 and s.issuing_ca_cert_b64):
        raise ValueError("Root and issuing CA certificates are not configured")
    root_pem = _decode_pem(s.root_ca_cert_b64)
    issuing_pem = _decode_pem(s.issuing_ca_cert_b64)
    return [root_pem, issuing_pem]
