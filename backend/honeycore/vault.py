"""HoneyVault: blob v1, per-entry nonce, unlock never raises (PROJECT-BRIEF.md §7.8).

Owner: T1 — Dhruv. Phase 1.

Key schedule: ``K = Argon2id(master, salt)``, ``enc_key, sigil_key = derive_subkeys(K)``.
Each entry stores ``ct = AES-256-CTR(enc_key, nonce) XOR EntryDTE.encode(username, password)``
under its own random nonce. There is no MAC, tag, padding, checksum or stored verifier of
anything derived from the master password, so every password decrypts every entry to *some*
seed and the total DTE turns it into a plausible credential (AGENTS.md §1.1–1.4).

Dependencies are injected per class: ``HoneyVault.bind(entry_dte, kdf, cipher)`` returns a
subclass whose ``new`` / ``from_dict`` build vaults using those components.
"""

from __future__ import annotations

import base64
import binascii
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, ClassVar

from honeycore.cipher import AESCTRCipher, new_nonce
from honeycore.interfaces import (
    CTR_NONCE_LEN,
    ENTRY_SEED_LEN,
    FORMAT_VERSION,
    KDF,
    KDF_PROFILES,
    MAX_FIELD_LEN,
    PRINTABLE_MAX,
    PRINTABLE_MIN,
    SALT_LEN,
    DecodedEntry,
    Entry,
    EntryDTE,
    EntryNotFoundError,
    HoneyCoreError,
    InvalidInputError,
    KDFParams,
    StreamCipher,
    UnlockResult,
)
from honeycore.kdf import Argon2KDF, derive_subkeys, new_salt
from honeycore.sigil import compute_sigil

FORMAT_NAME = "honeyvault"
SCHEME = "HE-PCFG-v1/AES-256-CTR/argon2id"
KDF_ALG = "argon2id"
MAX_SERVICE_LEN = 128  # docs/api-contract.md §0.5 (frozen)
DEFAULT_MODEL_IDS: dict[str, str] = {
    "password_model": "pcfg-password-v1",
    "username_model": "pcfg-username-v1",
}

TOP_KEYS = frozenset({"format", "version", "scheme", "kdf", "dte", "entries"})
KDF_KEYS = frozenset(
    {"alg", "profile", "salt", "time_cost", "memory_cost_kib", "parallelism", "hash_len"}
)
DTE_KEYS = frozenset({"password_model", "username_model", "entry_seed_len"})
ENTRY_KEYS = frozenset({"id", "service", "nonce", "ciphertext", "created_at", "updated_at"})

# Sanity bounds for KDF params read from a blob, so a corrupt blob fails in from_dict rather
# than inside unlock (and cannot request absurd memory).
_KDF_BOUNDS: dict[str, tuple[int, int]] = {
    "time_cost": (1, 64),
    "memory_cost_kib": (8, 4 * 1024 * 1024),
    "parallelism": (1, 64),
    "hash_len": (16, 64),
}


class VaultFormatError(InvalidInputError, ValueError):
    """Malformed vault blob. A ``ValueError`` and an ``InvalidInputError`` (HTTP 422)."""


@dataclass(slots=True)
class _StoredEntry:
    id: str
    service: str
    nonce: bytes
    ciphertext: bytes
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def _now() -> str:
    return datetime.now(UTC).isoformat()


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: Any, expected_len: int, what: str) -> bytes:
    if not isinstance(text, str):
        raise VaultFormatError(f"{what}: expected a base64 string")
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise VaultFormatError(f"{what}: invalid base64") from exc
    if len(raw) != expected_len:
        raise VaultFormatError(f"{what}: expected {expected_len} bytes, got {len(raw)}")
    return raw


def _validate_service(service: Any) -> None:
    """1..``MAX_SERVICE_LEN`` printable chars, not only whitespace (plaintext metadata)."""
    if not isinstance(service, str) or not 1 <= len(service) <= MAX_SERVICE_LEN:
        raise InvalidInputError(f"service must be 1-{MAX_SERVICE_LEN} characters")
    if not service.isprintable() or not service.strip():
        raise InvalidInputError("service must be printable and not blank")


def _validate_field(value: Any, what: str) -> None:
    """§7.1: 1..32 printable ASCII chars. Error messages never echo the value."""
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_FIELD_LEN:
        raise InvalidInputError(f"{what} must be 1-{MAX_FIELD_LEN} characters")
    if any(not PRINTABLE_MIN <= ord(ch) <= PRINTABLE_MAX for ch in value):
        raise InvalidInputError(f"{what} must be printable ASCII")


def _validate_entry(entry: Entry) -> None:
    _validate_service(entry.service)
    _validate_field(entry.username, "username")
    _validate_field(entry.password, "password")


def _kdf_password(master_password: str) -> str:
    """Make any ``str`` safe for the KDF's strict UTF-8 encode, so unlock can never raise.

    Ordinary strings are returned unchanged. A string with lone surrogates (possible from JSON
    ``"\\ud800"``) is mapped deterministically to its ``surrogatepass`` bytes read as latin-1.
    """
    try:
        master_password.encode("utf-8")
    except UnicodeEncodeError:
        return master_password.encode("utf-8", "surrogatepass").decode("latin-1")
    return master_password


def _iso_utc(value: Any, what: str) -> str:
    if not isinstance(value, str):
        raise VaultFormatError(f"{what}: expected an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise VaultFormatError(f"{what}: not ISO-8601") from exc
    if parsed.utcoffset() is None:
        raise VaultFormatError(f"{what}: missing UTC offset")
    return value


def _require_keys(obj: Any, keys: frozenset[str], what: str) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise VaultFormatError(f"{what}: expected an object")
    if set(obj) != keys:
        raise VaultFormatError(f"{what}: unexpected or missing keys")
    return obj


def _bounded_int(value: Any, name: str) -> int:
    lo, hi = _KDF_BOUNDS[name]
    if isinstance(value, bool) or not isinstance(value, int) or not lo <= value <= hi:
        raise VaultFormatError(f"kdf.{name}: expected an integer in [{lo}, {hi}]")
    return value


def _model_ids(entry_dte: EntryDTE) -> dict[str, str]:
    """``dte`` block ids: ``entry_dte.model_ids``, else sub-model ``model_id``, else default."""
    ids = dict(DEFAULT_MODEL_IDS)
    declared = getattr(entry_dte, "model_ids", None)
    for key in ids:
        if isinstance(declared, Mapping) and isinstance(declared.get(key), str):
            ids[key] = declared[key]
            continue
        sub = getattr(entry_dte, key, None)
        sub_id = getattr(sub, "model_id", None)
        if isinstance(sub_id, str) and sub_id:
            ids[key] = sub_id
    return ids


# ---------------------------------------------------------------------------------------------
# HoneyVault
# ---------------------------------------------------------------------------------------------
class HoneyVault:
    """``HoneyVaultAPI`` implementation (blob v1). ``unlock`` never raises for any password."""

    _entry_dte: ClassVar[EntryDTE | None] = None
    _kdf: ClassVar[KDF] = Argon2KDF()
    _cipher: ClassVar[StreamCipher] = AESCTRCipher()

    def __init__(
        self,
        kdf_profile: str,
        kdf_params: KDFParams,
        salt: bytes,
        model_ids: dict[str, str],
        entries: list[_StoredEntry] | None = None,
    ) -> None:
        self.kdf_profile = kdf_profile
        self.kdf_params = kdf_params
        self.salt = salt
        self.model_ids = model_ids
        self._entries: list[_StoredEntry] = entries if entries is not None else []

    # ---- dependency injection ----
    @classmethod
    def bind(
        cls,
        entry_dte: EntryDTE,
        kdf: KDF | None = None,
        cipher: StreamCipher | None = None,
    ) -> type[HoneyVault]:
        """Return a subclass that uses ``entry_dte`` (and optionally ``kdf`` / ``cipher``).

        Raises ``ValueError`` if ``entry_dte.seed_len != ENTRY_SEED_LEN``.
        """
        if getattr(entry_dte, "seed_len", None) != ENTRY_SEED_LEN:
            raise ValueError(f"entry_dte.seed_len must be {ENTRY_SEED_LEN}")
        attrs = {
            "_entry_dte": entry_dte,
            "_kdf": kdf if kdf is not None else cls._kdf,
            "_cipher": cipher if cipher is not None else cls._cipher,
        }
        return type(f"{cls.__name__}Bound", (cls,), attrs)

    @classmethod
    def _dte(cls) -> EntryDTE:
        """The bound entry DTE, defaulting to the real PCFG one once it exists."""
        if cls._entry_dte is None:
            try:
                from honeycore.dte.entry_dte import PCFGEntryDTE
            except ImportError as exc:
                raise NotImplementedError(
                    "no EntryDTE bound: use HoneyVault.bind(entry_dte) until PCFGEntryDTE lands"
                ) from exc
            cls._entry_dte = PCFGEntryDTE()
        return cls._entry_dte

    # ---- construction / serialisation ----
    @classmethod
    def new(cls, kdf_profile: str = "default") -> HoneyVault:
        """Empty vault with a fresh ``SALT_LEN``-byte salt and the named KDF profile."""
        if kdf_profile not in KDF_PROFILES:
            raise InvalidInputError(f"unknown kdf profile: {kdf_profile}")
        return cls(kdf_profile, KDF_PROFILES[kdf_profile], new_salt(), _model_ids(cls._dte()))

    @classmethod
    def from_dict(cls, data: dict) -> HoneyVault:
        """Parse a blob v1 dict. Raises ``VaultFormatError`` (a ``ValueError``) if malformed.

        Validation depends only on the blob, never on any password.
        """
        top = _require_keys(data, TOP_KEYS, "vault")
        if top["format"] != FORMAT_NAME:
            raise VaultFormatError("vault: unsupported format")
        if isinstance(top["version"], bool) or top["version"] != FORMAT_VERSION:
            raise VaultFormatError("vault: unsupported version")
        if top["scheme"] != SCHEME:
            raise VaultFormatError("vault: unsupported scheme")

        kdf = _require_keys(top["kdf"], KDF_KEYS, "kdf")
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

        dte = _require_keys(top["dte"], DTE_KEYS, "dte")
        if isinstance(dte["entry_seed_len"], bool) or dte["entry_seed_len"] != ENTRY_SEED_LEN:
            raise VaultFormatError(f"dte.entry_seed_len: expected {ENTRY_SEED_LEN}")
        model_ids: dict[str, str] = {}
        for key in DEFAULT_MODEL_IDS:
            if not isinstance(dte[key], str) or not dte[key]:
                raise VaultFormatError(f"dte.{key}: expected a non-empty string")
            model_ids[key] = dte[key]

        if not isinstance(top["entries"], list):
            raise VaultFormatError("entries: expected a list")
        entries: list[_StoredEntry] = []
        seen: set[str] = set()
        for raw in top["entries"]:
            e = _require_keys(raw, ENTRY_KEYS, "entry")
            if not isinstance(e["id"], str) or not e["id"] or e["id"] in seen:
                raise VaultFormatError("entry.id: expected a unique non-empty string")
            seen.add(e["id"])
            try:
                _validate_service(e["service"])
            except InvalidInputError as exc:
                raise VaultFormatError(f"entry.service: {exc}") from exc
            entries.append(
                _StoredEntry(
                    id=e["id"],
                    service=e["service"],
                    nonce=_b64d(e["nonce"], CTR_NONCE_LEN, "entry.nonce"),
                    ciphertext=_b64d(e["ciphertext"], ENTRY_SEED_LEN, "entry.ciphertext"),
                    created_at=_iso_utc(e["created_at"], "entry.created_at"),
                    updated_at=_iso_utc(e["updated_at"], "entry.updated_at"),
                )
            )
        return cls(kdf["profile"], params, salt, model_ids, entries)

    def to_dict(self) -> dict:
        """Serialise to blob v1 (§7.8). Contains no MAC, checksum, key hash or verifier."""
        p = self.kdf_params
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "scheme": SCHEME,
            "kdf": {
                "alg": KDF_ALG,
                "profile": self.kdf_profile,
                "salt": _b64e(self.salt),
                "time_cost": p.time_cost,
                "memory_cost_kib": p.memory_cost_kib,
                "parallelism": p.parallelism,
                "hash_len": p.hash_len,
            },
            "dte": {
                "password_model": self.model_ids["password_model"],
                "username_model": self.model_ids["username_model"],
                "entry_seed_len": ENTRY_SEED_LEN,
            },
            "entries": [
                {
                    "id": e.id,
                    "service": e.service,
                    "nonce": _b64e(e.nonce),
                    "ciphertext": _b64e(e.ciphertext),
                    "created_at": e.created_at,
                    "updated_at": e.updated_at,
                }
                for e in self._entries
            ],
        }

    # ---- internals ----
    def _keys(self, master_password: str) -> tuple[bytes, bytes]:
        """One KDF call -> ``(enc_key, sigil_key)``. Never raises for any ``str`` password."""
        k = self._kdf.derive(_kdf_password(master_password), self.salt, self.kdf_params)
        return derive_subkeys(k)

    def _find(self, entry_id: str) -> _StoredEntry:
        for e in self._entries:
            if e.id == entry_id:
                return e
        raise EntryNotFoundError("unknown entry id")

    def _seal(self, enc_key: bytes, entry: Entry) -> tuple[bytes, bytes]:
        """Encode + encrypt one entry under a fresh nonce -> ``(nonce, ciphertext)``."""
        seed = self._dte().encode(entry.username, entry.password)
        if len(seed) != ENTRY_SEED_LEN:
            raise HoneyCoreError("entry DTE returned a seed of the wrong length")
        nonce = new_nonce()
        return nonce, self._cipher.apply(enc_key, nonce, seed)

    # ---- HoneyVaultAPI ----
    def entry_count(self) -> int:
        """Number of stored entries (public: the ciphertext count reveals it anyway)."""
        return len(self._entries)

    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Encrypt ONE entry under ``master_password`` and append it; returns its uuid4 id.

        Raises ``InvalidInputError`` for an invalid service/username/password. Other entries are
        never touched, so a mistyped password damages at most this entry.
        """
        _validate_entry(entry)
        enc_key, _ = self._keys(master_password)
        nonce, ct = self._seal(enc_key, entry)
        now = _now()
        entry_id = str(uuid.uuid4())
        self._entries.append(_StoredEntry(entry_id, entry.service, nonce, ct, now, now))
        return entry_id

    def update_entry(self, master_password: str, entry_id: str, entry: Entry) -> None:
        """Re-encrypt only ``entry_id`` (fresh nonce). ``EntryNotFoundError`` if unknown."""
        target = self._find(entry_id)
        _validate_entry(entry)
        enc_key, _ = self._keys(master_password)
        target.nonce, target.ciphertext = self._seal(enc_key, entry)
        target.service = entry.service
        target.updated_at = _now()

    def delete_entry(self, entry_id: str) -> None:
        """Remove ``entry_id`` (no password needed). ``EntryNotFoundError`` if unknown."""
        self._entries.remove(self._find(entry_id))

    def unlock(self, master_password: str) -> UnlockResult:
        """NEVER raises: derive the key once, then decrypt + total-decode every entry."""
        enc_key, sigil_key = self._keys(master_password)
        dte = self._dte()
        entries: list[DecodedEntry] = []
        for e in self._entries:
            username, password = dte.decode(self._cipher.apply(enc_key, e.nonce, e.ciphertext))
            entries.append(
                DecodedEntry(
                    id=e.id,
                    service=e.service,
                    username=username,
                    password=password,
                    created_at=e.created_at,
                    updated_at=e.updated_at,
                )
            )
        return UnlockResult(entries=entries, sigil=compute_sigil(sigil_key))

    def export_entry_seed(self, master_password: str, entry_id: str) -> bytes:
        """Decrypted DTE seed of one entry (a decoy seed for a wrong password, never an error).

        Raises ``EntryNotFoundError`` only if ``entry_id`` is unknown.
        """
        target = self._find(entry_id)
        enc_key, _ = self._keys(master_password)
        return self._cipher.apply(enc_key, target.nonce, target.ciphertext)
