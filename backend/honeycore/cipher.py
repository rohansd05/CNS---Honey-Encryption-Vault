"""AES-256-CTR stream cipher, NO MAC/tag/padding (PROJECT-BRIEF.md §7.7).

Owner: T1 — Dhruv. Phase 1.

``ct = seed XOR AES-256-CTR keystream(key, nonce)``, with a fresh random 16-byte nonce per
entry used as the initial counter block. Ciphertext length always equals plaintext length and
there is nothing to check on decryption, so a wrong key silently yields a different (uniformly
random-looking) seed — exactly what honey encryption needs (invariant §1.1).
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from honeycore.interfaces import CTR_NONCE_LEN, InvalidInputError

KEY_LEN = 32  # AES-256


class AESCTRCipher:
    """``StreamCipher`` implementation: AES-256 in CTR mode. encrypt == decrypt."""

    def apply(self, key: bytes, nonce: bytes, data: bytes) -> bytes:
        """XOR ``data`` with the AES-256-CTR keystream for (``key``, ``nonce``).

        Raises ``InvalidInputError`` unless ``key`` is 32 bytes and ``nonce`` is
        ``CTR_NONCE_LEN`` bytes. Never authenticates: any key decrypts any ciphertext.
        """
        if len(key) != KEY_LEN:
            raise InvalidInputError(f"key must be {KEY_LEN} bytes, got {len(key)}")
        if len(nonce) != CTR_NONCE_LEN:
            raise InvalidInputError(f"nonce must be {CTR_NONCE_LEN} bytes, got {len(nonce)}")
        ctx = Cipher(algorithms.AES(bytes(key)), modes.CTR(bytes(nonce))).encryptor()
        return ctx.update(bytes(data)) + ctx.finalize()


def new_nonce() -> bytes:
    """Return a fresh random ``CTR_NONCE_LEN``-byte nonce from ``os.urandom``."""
    return os.urandom(CTR_NONCE_LEN)
