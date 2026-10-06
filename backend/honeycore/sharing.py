"""ECDH P-256 + HKDF-SHA256 + AES-256-GCM share envelopes, ECDSA signed (§9).

Owner: T4 — Parth. Phase 2.
Implements ``SharingAPI`` exactly per PROJECT-BRIEF.md §9 and ADR-006.

Allowed imports: stdlib, cryptography, honeycore.interfaces, honeycore.pki.
"""

from __future__ import annotations

import base64
import json
import secrets

from cryptography import x509 as _x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from honeycore.interfaces import IdentityKeys, InvalidSignatureError, SharingAPI
from honeycore.pki import PKI

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_HKDF_INFO = b"honeyvault-share-v1"
_AES_KEY_LEN = 32  # AES-256
_NONCE_LEN = 12  # AES-GCM standard
_SALT_LEN = 16
_WRAP_AAD = b"honeyvault-identity-v1"
_ENVELOPE_ALG = "ECIES-P256-HKDF-SHA256-AES256GCM+ECDSA-P256-SHA256"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _b64e(data: bytes) -> str:
    """Base64-encode bytes to an ASCII string."""
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str) -> bytes:
    """Base64-decode an ASCII string."""
    return base64.b64decode(text)


def _canonical_json(obj: dict) -> bytes:
    """Canonical JSON: sort_keys=True, compact separators, no ASCII escaping."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _spki_bytes(pub_key: ec.EllipticCurvePublicKey) -> bytes:
    """Encode a public key as DER SPKI."""
    return pub_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _ecdh_shared_secret(
    private_key: ec.EllipticCurvePrivateKey,
    peer_public_key: ec.EllipticCurvePublicKey,
) -> bytes:
    """Perform ECDH and return the raw shared secret bytes."""
    return private_key.exchange(ec.ECDH(), peer_public_key)


def _hkdf_derive(shared_secret: bytes, salt: bytes) -> bytes:
    """Derive a 256-bit AES key via HKDF-SHA256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_AES_KEY_LEN,
        salt=salt,
        info=_HKDF_INFO,
    )
    return hkdf.derive(shared_secret)


# ---------------------------------------------------------------------------
# ADR-006: symmetric private-key wrapping
# ---------------------------------------------------------------------------


def wrap_private_key(private_pem: bytes, kek: bytes) -> str:
    """Wrap a P-256 private key PEM with AES-256-GCM under *kek*.

    Returns a base64-encoded blob: ``nonce || ciphertext+tag`` (12 + len + 16 bytes).
    The kek must be exactly 32 bytes.
    """
    nonce = secrets.token_bytes(_NONCE_LEN)
    aesgcm = AESGCM(kek)
    ct = aesgcm.encrypt(nonce, private_pem, _WRAP_AAD)
    return _b64e(nonce + ct)


def unwrap_private_key(wrapped: str, kek: bytes) -> bytes:
    """Unwrap a key produced by :func:`wrap_private_key`.

    Raises :class:`~honeycore.interfaces.InvalidSignatureError` on any
    decryption or authentication failure.
    """
    try:
        raw = _b64d(wrapped)
        nonce, ct = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
        aesgcm = AESGCM(kek)
        return aesgcm.decrypt(nonce, ct, _WRAP_AAD)
    except Exception as exc:
        raise InvalidSignatureError(f"Key unwrap failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------


class Sharing(SharingAPI):
    """ECIES envelope sharing with ECDSA sender-cert authentication (§9)."""

    # ------------------------------------------------------------------
    # SharingAPI.generate_identity
    # ------------------------------------------------------------------

    def generate_identity(self) -> IdentityKeys:
        """Generate a fresh P-256 keypair and return PEM-encoded bytes."""
        priv = ec.generate_private_key(ec.SECP256R1())
        priv_pem = priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        pub_pem = priv.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return IdentityKeys(private_pem=priv_pem, public_pem=pub_pem)

    # ------------------------------------------------------------------
    # SharingAPI.seal_share
    # ------------------------------------------------------------------

    def seal_share(
        self,
        seed: bytes,
        aad: dict,
        recipient_public_pem: bytes,
        sender_private_pem: bytes,
        sender_cert_pem: bytes,
    ) -> dict:
        """Seal *seed* for the recipient and sign with sender's private key.

        Returns the v1 envelope dict per PROJECT-BRIEF.md §9.
        """
        # 1. Parse keys
        recipient_pub = serialization.load_pem_public_key(recipient_public_pem)
        if not isinstance(recipient_pub, ec.EllipticCurvePublicKey):
            raise ValueError("Recipient key must be EC P-256")

        sender_priv = serialization.load_pem_private_key(sender_private_pem, password=None)
        if not isinstance(sender_priv, ec.EllipticCurvePrivateKey):
            raise ValueError("Sender key must be EC P-256")

        # 2. Ephemeral ECDH
        eph_priv = ec.generate_private_key(ec.SECP256R1())
        eph_pub = eph_priv.public_key()
        shared_secret = _ecdh_shared_secret(eph_priv, recipient_pub)

        # 3. HKDF → AES-256 key
        salt = secrets.token_bytes(_SALT_LEN)
        aes_key = _hkdf_derive(shared_secret, salt)

        # 4. AES-256-GCM encrypt seed; associated_data = canonical JSON of aad
        nonce = secrets.token_bytes(_NONCE_LEN)
        aesgcm = AESGCM(aes_key)
        aad_bytes = _canonical_json(aad)
        ciphertext = aesgcm.encrypt(nonce, seed, aad_bytes)

        # 5. Build envelope (without signature field)
        eph_pub_der = _spki_bytes(eph_pub)
        envelope: dict = {
            "v": 1,
            "alg": _ENVELOPE_ALG,
            "eph_pub": _b64e(eph_pub_der),
            "salt": _b64e(salt),
            "nonce": _b64e(nonce),
            "ciphertext": _b64e(ciphertext),
            "aad": aad,
            "sender_cert": sender_cert_pem.decode("ascii"),
        }

        # 6. ECDSA-P256-SHA256 signature over canonical JSON of envelope (no "signature" field)
        envelope_bytes = _canonical_json(envelope)
        der_sig = sender_priv.sign(envelope_bytes, ec.ECDSA(hashes.SHA256()))
        envelope["signature"] = _b64e(der_sig)

        return envelope

    # ------------------------------------------------------------------
    # SharingAPI.open_share
    # ------------------------------------------------------------------

    def open_share(
        self,
        envelope: dict,
        recipient_private_pem: bytes,
        trusted_ca_pems: list[bytes],
    ) -> tuple[bytes, dict]:
        """Verify chain, signature, decrypt; returns ``(seed, aad)``.

        Raises :class:`~honeycore.interfaces.InvalidSignatureError` on ANY failure.
        """
        try:
            return self._open_share_inner(envelope, recipient_private_pem, trusted_ca_pems)
        except InvalidSignatureError:
            raise
        except Exception as exc:
            raise InvalidSignatureError(f"open_share failed: {exc}") from exc

    def _open_share_inner(
        self,
        envelope: dict,
        recipient_private_pem: bytes,
        trusted_ca_pems: list[bytes],
    ) -> tuple[bytes, dict]:
        # --- 1. Extract fields ---
        try:
            sender_cert_pem: bytes = envelope["sender_cert"].encode("ascii")
            sig_b64: str = envelope["signature"]
            aad: dict = envelope["aad"]
        except KeyError as exc:
            raise InvalidSignatureError(f"Envelope missing field: {exc}") from exc

        # --- 2. Verify sender cert chain via PKI ---
        pki = PKI()
        sender_cn: str = aad.get("sender", "")
        # verify_certificate raises InvalidSignatureError on any failure
        pki.verify_certificate(
            sender_cert_pem,
            trusted_ca_pems,
            expected_cn=sender_cn if sender_cn else None,
        )

        # --- 3. Verify ECDSA signature over canonical envelope (minus "signature") ---
        envelope_without_sig = {k: v for k, v in envelope.items() if k != "signature"}
        envelope_bytes = _canonical_json(envelope_without_sig)

        # Extract sender's public key from the cert
        sender_cert = _x509.load_pem_x509_certificate(sender_cert_pem)
        sender_pub = sender_cert.public_key()
        if not isinstance(sender_pub, ec.EllipticCurvePublicKey):
            raise InvalidSignatureError("Sender cert key is not EC")

        der_sig = _b64d(sig_b64)
        try:
            sender_pub.verify(der_sig, envelope_bytes, ec.ECDSA(hashes.SHA256()))
        except Exception as exc:
            raise InvalidSignatureError(f"Signature verification failed: {exc}") from exc

        # --- 4. ECDH decrypt ---
        recipient_priv = serialization.load_pem_private_key(recipient_private_pem, password=None)
        if not isinstance(recipient_priv, ec.EllipticCurvePrivateKey):
            raise InvalidSignatureError("Recipient key must be EC P-256")

        eph_pub_der = _b64d(envelope["eph_pub"])
        eph_pub = serialization.load_der_public_key(eph_pub_der)
        if not isinstance(eph_pub, ec.EllipticCurvePublicKey):
            raise InvalidSignatureError("Ephemeral key must be EC P-256")

        shared_secret = _ecdh_shared_secret(recipient_priv, eph_pub)
        salt = _b64d(envelope["salt"])
        aes_key = _hkdf_derive(shared_secret, salt)

        nonce = _b64d(envelope["nonce"])
        ciphertext = _b64d(envelope["ciphertext"])
        aad_bytes = _canonical_json(aad)

        aesgcm = AESGCM(aes_key)
        try:
            seed = aesgcm.decrypt(nonce, ciphertext, aad_bytes)
        except Exception as exc:
            raise InvalidSignatureError(f"AES-GCM decryption failed: {exc}") from exc

        return seed, aad
