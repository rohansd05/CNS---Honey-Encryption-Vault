"""Conventional Argon2id + AES-256-GCM vault for the attack comparison (§7.10).

Owner: T1 — Dhruv. Phase 1.

This is the vault honey encryption improves on, and it is deliberately ordinary:
``K = Argon2id(master, salt)`` (same profiles as the honey vault), ``enc_key`` from the same
HMAC key schedule, then AES-256-GCM over the canonical JSON ``{"entries": [...]}`` with a random
12-byte nonce. The GCM tag IS a password oracle — a wrong password raises
``WrongPasswordError`` — which is exactly what the attack simulator demonstrates (§11).
Never use this for real user data.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import uuid
from collections.abc import Mapping
from typing import Any, ClassVar

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from honeycore.interfaces import (
    FORMAT_VERSION,
    KDF,
    KDF_PROFILES,
    SALT_LEN,
    DecodedEntry,
    Entry,
    InvalidInputError,
    KDFParams,
    WrongPasswordError,
)
from honeycore.kdf import Argon2KDF, derive_subkeys, new_salt
from honeycore.vault import (
    KDF_ALG,
    KDF_KEYS,
    VaultFormatError,
    _b64d,
    _b64e,
    _bounded_int,
    _kdf_password,
    _now,
    _require_keys,
    _validate_entry,
)

FORMAT_NAME = "conventional"
GCM_NONCE_LEN = 12
GCM_TAG_LEN = 16
AAD = b"honeyvault-conventional-v1"
TOP_KEYS = frozenset({"format", "version", "kdf", "nonce", "ciphertext"})
_ENTRY_FIELDS = ("id", "service", "username", "password", "created_at", "updated_at")


def _canonical(entries: list[dict[str, str]]) -> bytes:
    """Canonical JSON body: sorted keys, no whitespace, UTF-8."""
    return json.dumps(
        {"entries": entries}, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class ConventionalVault:
    """``ConventionalVaultAPI``: one AES-256-GCM ciphertext over the whole entry list."""

    _kdf: ClassVar[KDF] = Argon2KDF()

    def __init__(
        self,
        kdf_profile: str,
        kdf_params: KDFParams,
        salt: bytes,
        nonce: bytes,
        ciphertext: bytes,
    ) -> None:
        self.kdf_profile = kdf_profile
        self.kdf_params = kdf_params
        self.salt = salt
        self.nonce = nonce
        self.ciphertext = ciphertext

    # ---- crypto ----
    def _key(self, master_password: str) -> bytes:
        """``enc_key`` from ``Argon2id(master, salt)`` via the shared HMAC key schedule."""
        k = self._kdf.derive(_kdf_password(master_password), self.salt, self.kdf_params)
        return derive_subkeys(k)[0]

    def _load(self, key: bytes) -> list[dict[str, str]]:
        """Decrypt + parse. Raises ``WrongPasswordError`` if the GCM tag does not verify."""
        try:
            body = AESGCM(key).decrypt(self.nonce, self.ciphertext, AAD)
        except InvalidTag:
            raise WrongPasswordError("wrong master password") from None
        try:
            entries = json.loads(body)["entries"]
        except (ValueError, KeyError, TypeError) as exc:
            raise VaultFormatError("conventional vault: malformed plaintext") from exc
        if not isinstance(entries, list):
            raise VaultFormatError("conventional vault: malformed plaintext")
        return entries

    def _store(self, key: bytes, entries: list[dict[str, str]]) -> None:
        """Re-encrypt the whole list under a fresh random nonce."""
        self.nonce = os.urandom(GCM_NONCE_LEN)
        self.ciphertext = AESGCM(key).encrypt(self.nonce, _canonical(entries), AAD)

    # ---- construction / serialisation ----
    @classmethod
    def new(cls, master_password: str, kdf_profile: str = "default") -> ConventionalVault:
        """Create a vault holding an empty entry list, encrypted under ``master_password``."""
        if kdf_profile not in KDF_PROFILES:
            raise InvalidInputError(f"unknown kdf profile: {kdf_profile}")
        vault = cls(kdf_profile, KDF_PROFILES[kdf_profile], new_salt(), b"", b"")
        vault._store(vault._key(master_password), [])
        return vault

    @classmethod
    def from_dict(cls, data: dict) -> ConventionalVault:
        """Parse a ``to_dict`` blob. Raises ``VaultFormatError`` (a ``ValueError``)."""
        top = _require_keys(data, TOP_KEYS, "conventional vault")
        if top["format"] != FORMAT_NAME:
            raise VaultFormatError("conventional vault: unsupported format")
        if isinstance(top["version"], bool) or top["version"] != FORMAT_VERSION:
            raise VaultFormatError("conventional vault: unsupported version")
        kdf: Mapping[str, Any] = _require_keys(top["kdf"], KDF_KEYS, "kdf")
        if kdf["alg"] != KDF_ALG:
            raise VaultFormatError("kdf.alg: unsupported")
        if not isinstance(kdf["profile"], str) or not kdf["profile"]:
            raise VaultFormatError("kdf.profile: expected a non-empty string")
        params = KDFParams(
            time_cost=_bounded_int(kdf["time_cost"], "time_cost"),
            memory_cost_kib=_bounded_int(kdf["memory_cost_kib"], "memory_cost_kib"),
            parallelism=_bounded_int(kdf["parallelism"], "parallelism"),
            hash_len=_bounded_int(kdf["hash_len"], "hash_len"),
        )
        if params.memory_cost_kib < 8 * params.parallelism:
            raise VaultFormatError("kdf.memory_cost_kib: must be >= 8 * parallelism")
        salt = _b64d(kdf["salt"], SALT_LEN, "kdf.salt")
        nonce = _b64d(top["nonce"], GCM_NONCE_LEN, "nonce")
        if not isinstance(top["ciphertext"], str):
            raise VaultFormatError("ciphertext: expected a base64 string")
        try:
            ciphertext = base64.b64decode(top["ciphertext"], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise VaultFormatError("ciphertext: invalid base64") from exc
        if len(ciphertext) < GCM_TAG_LEN:
            raise VaultFormatError("ciphertext: shorter than the GCM tag")
        return cls(kdf["profile"], params, salt, nonce, ciphertext)

    def to_dict(self) -> dict:
        """``{"format":"conventional","version":1,"kdf":{...},"nonce":b64,"ciphertext":b64}``."""
        p = self.kdf_params
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "kdf": {
                "alg": KDF_ALG,
                "profile": self.kdf_profile,
                "salt": _b64e(self.salt),
                "time_cost": p.time_cost,
                "memory_cost_kib": p.memory_cost_kib,
                "parallelism": p.parallelism,
                "hash_len": p.hash_len,
            },
            "nonce": _b64e(self.nonce),
            "ciphertext": _b64e(self.ciphertext),
        }

    # ---- ConventionalVaultAPI ----
    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Decrypt, append, re-encrypt under a new nonce; returns the new uuid4 id.

        Raises ``InvalidInputError`` for an invalid entry and ``WrongPasswordError`` for a wrong
        password (the vault is left unchanged in both cases).
        """
        _validate_entry(entry)
        key = self._key(master_password)
        entries = self._load(key)
        now = _now()
        entry_id = str(uuid.uuid4())
        entries.append(
            {
                "id": entry_id,
                "service": entry.service,
                "username": entry.username,
                "password": entry.password,
                "created_at": now,
                "updated_at": now,
            }
        )
        self._store(key, entries)
        return entry_id

    def unlock(self, master_password: str) -> list[DecodedEntry]:
        """Return the entries; raises ``WrongPasswordError`` — the oracle HE removes."""
        entries = self._load(self._key(master_password))
        try:
            return [DecodedEntry(**{f: str(e[f]) for f in _ENTRY_FIELDS}) for e in entries]
        except (KeyError, TypeError) as exc:
            raise VaultFormatError("conventional vault: malformed entry") from exc

    def try_password(self, master_password: str) -> bool:
        """Attack-simulator helper: ``True`` iff ``master_password`` verifies (GCM tag OK)."""
        try:
            self._load(self._key(master_password))
        except WrongPasswordError:
            return False
        return True
