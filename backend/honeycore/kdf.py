"""Argon2id KDF with named profiles (PROJECT-BRIEF.md §7.6).

Owner: T1 — Dhruv. Phase 1.

``K = Argon2id(master, salt)`` with the cost parameters of a ``KDF_PROFILES`` entry (the profile
is stored in the vault blob). Subkeys are split off ``K`` with HMAC-SHA256 under fixed labels so
the cipher key and the sigil key are independent. Nothing here is stored or verifiable: there is
no password hash, no key check value, and ``derive`` never rejects a password (any string,
including the empty one, yields a key — invariant §1.2).
"""

from __future__ import annotations

import hashlib
import hmac
import os

from argon2.low_level import Type, hash_secret_raw

from honeycore.interfaces import SALT_LEN, InvalidInputError, KDFParams

ENC_KEY_LABEL = b"honeyvault-enc-v1"
SIGIL_KEY_LABEL = b"honeyvault-sigil-v1"


class Argon2KDF:
    """``KDF`` implementation: Argon2id via ``argon2.low_level.hash_secret_raw``."""

    def derive(self, password: str, salt: bytes, params: KDFParams) -> bytes:
        """Return ``params.hash_len`` bytes of ``Argon2id(password UTF-8, salt)``.

        Raises ``InvalidInputError`` if ``salt`` is not exactly ``SALT_LEN`` bytes. The password
        itself is never validated or rejected.
        """
        if len(salt) != SALT_LEN:
            raise InvalidInputError(f"salt must be {SALT_LEN} bytes, got {len(salt)}")
        return hash_secret_raw(
            secret=password.encode("utf-8"),
            salt=bytes(salt),
            time_cost=params.time_cost,
            memory_cost=params.memory_cost_kib,
            parallelism=params.parallelism,
            hash_len=params.hash_len,
            type=Type.ID,
        )


def derive_subkeys(master_key: bytes) -> tuple[bytes, bytes]:
    """Split ``K`` into ``(enc_key, sigil_key)``, each 32 bytes.

    ``enc_key = HMAC-SHA256(K, b"honeyvault-enc-v1")``,
    ``sigil_key = HMAC-SHA256(K, b"honeyvault-sigil-v1")``.
    """
    if not master_key:
        raise InvalidInputError("master key must be non-empty")
    enc_key = hmac.new(master_key, ENC_KEY_LABEL, hashlib.sha256).digest()
    sigil_key = hmac.new(master_key, SIGIL_KEY_LABEL, hashlib.sha256).digest()
    return enc_key, sigil_key


def new_salt() -> bytes:
    """Return a fresh random ``SALT_LEN``-byte salt from ``os.urandom``."""
    return os.urandom(SALT_LEN)
