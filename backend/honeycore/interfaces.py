"""honeycore library contract — FROZEN (PROJECT-BRIEF.md §7.0).

Owner: T1 lead — Nidhi. Change only via a PR labelled ``contract-change`` approved by the
T1 lead and every affected track. Real implementations and ``stubs.py`` must satisfy these
Protocols and the invariants in AGENTS.md §1.
"""

from __future__ import annotations

from dataclasses import dataclass, field  # noqa: F401  (``field`` kept to match §7.0 verbatim)
from typing import Protocol, runtime_checkable

# ---- format constants (v1) ----
FORMAT_VERSION = 1
MAX_FIELD_LEN = 32  # max chars for username and password
PRINTABLE_MIN, PRINTABLE_MAX = 0x20, 0x7E
INT_BYTES = 4  # each DTE choice is one 32-bit big-endian int
PASSWORD_SEED_INTS = 66  # 2 + 2*MAX_FIELD_LEN
USERNAME_SEED_INTS = 67  # 1 (email-domain choice) + 66
ENTRY_SEED_INTS = PASSWORD_SEED_INTS + USERNAME_SEED_INTS  # 133
ENTRY_SEED_LEN = ENTRY_SEED_INTS * INT_BYTES  # 532 bytes
SALT_LEN = 16
CTR_NONCE_LEN = 16


@dataclass(frozen=True)
class KDFParams:
    """Argon2id cost parameters. ``hash_len`` is the derived key length in bytes."""

    time_cost: int
    memory_cost_kib: int
    parallelism: int
    hash_len: int = 32


KDF_PROFILES: dict[str, KDFParams] = {
    "default": KDFParams(time_cost=3, memory_cost_kib=65536, parallelism=4),
    "server_lite": KDFParams(time_cost=2, memory_cost_kib=19456, parallelism=1),
    "demo": KDFParams(time_cost=1, memory_cost_kib=8192, parallelism=1),
}


class HoneyCoreError(Exception):
    """Base class for every honeycore error."""


class InvalidInputError(HoneyCoreError):
    """Input validation only (e.g. field too long / non-printable). Maps to HTTP 422."""


class WrongPasswordError(HoneyCoreError):
    """ONLY raised by ConventionalVault (the baseline). A honey vault never raises this."""


class InvalidSignatureError(HoneyCoreError):
    """Sharing / PKI verification failures (bad signature, chain, expiry, EKU)."""


@dataclass(frozen=True)
class Entry:
    """Plaintext entry as supplied by the user. ``service`` is plaintext metadata (ADR-001)."""

    service: str
    username: str
    password: str


@dataclass(frozen=True)
class DecodedEntry:
    """An entry as returned by unlock — real or decoy, indistinguishable by construction."""

    id: str
    service: str
    username: str
    password: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class Sigil:
    """Key-derived fingerprint (PROJECT-BRIEF.md §7.9). Never stored."""

    emojis: tuple[str, str, str]
    color: str  # "#RRGGBB"


@dataclass(frozen=True)
class UnlockResult:
    """Result of ``HoneyVaultAPI.unlock``: always a full, well-formed vault plus its sigil."""

    entries: list[DecodedEntry]
    sigil: Sigil


@runtime_checkable
class KDF(Protocol):
    """Password-based key derivation (Argon2id in the real implementation)."""

    def derive(self, password: str, salt: bytes, params: KDFParams) -> bytes:
        """Return ``params.hash_len`` key bytes derived from ``password`` and ``salt``."""
        ...


@runtime_checkable
class StreamCipher(Protocol):
    """Unauthenticated stream cipher (AES-256-CTR). No MAC, tag or padding — ever."""

    def apply(self, key: bytes, nonce: bytes, data: bytes) -> bytes:
        """XOR ``data`` with the keystream for (key, nonce). encrypt == decrypt."""
        ...


@runtime_checkable
class FieldDTE(Protocol):
    """Distribution-transforming encoder for a single field (username or password)."""

    seed_len: int

    def encode(self, value: str) -> bytes:
        """Encode ``value`` to a uniformly random-looking seed of exactly ``seed_len`` bytes.

        Raises ``InvalidInputError`` for values outside §7.1 limits.
        """
        ...

    def decode(self, seed: bytes) -> str:
        """TOTAL: never raises for ``len(seed) == seed_len``; always returns a valid value."""
        ...

    def sample(self) -> str:
        """Return ``decode(random seed)`` — a sample from the model distribution."""
        ...


@runtime_checkable
class PasswordModel(FieldDTE, Protocol):
    """Password DTE plus model queries used by honeywords and evaluation."""

    def sample_like(self, password: str) -> str:
        """Same template, fresh segments (used to generate honeywords)."""
        ...

    def probability(self, password: str) -> float:
        """Model probability of ``password`` (evaluation / strength)."""
        ...


@runtime_checkable
class EntryDTE(Protocol):
    """Encodes a (username, password) pair into one fixed-length seed."""

    seed_len: int  # == ENTRY_SEED_LEN

    def encode(self, username: str, password: str) -> bytes:
        """Return ``username_seed || password_seed`` (exactly ``ENTRY_SEED_LEN`` bytes)."""
        ...

    def decode(self, seed: bytes) -> tuple[str, str]:
        """TOTAL inverse of ``encode``: any ``ENTRY_SEED_LEN`` bytes -> (username, password)."""
        ...


@runtime_checkable
class HoneyVaultAPI(Protocol):
    """Honey-encrypted vault (blob v1, PROJECT-BRIEF.md §7.8)."""

    @classmethod
    def new(cls, kdf_profile: str = "default") -> HoneyVaultAPI:
        """Create an empty vault with a fresh random salt."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> HoneyVaultAPI:
        """Load a vault from its blob v1 dict (as stored in the DB / exported)."""
        ...

    def to_dict(self) -> dict:
        """Serialise to the blob v1 dict."""
        ...

    def entry_count(self) -> int:
        """Number of entries (public: ciphertext count reveals it anyway)."""
        ...

    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Encrypt and append ONE entry; returns its id. Never touches other entries."""
        ...

    def update_entry(self, master_password: str, entry_id: str, entry: Entry) -> None:
        """Re-encrypt only ``entry_id`` under ``master_password``."""
        ...

    def delete_entry(self, entry_id: str) -> None:
        """Remove an entry (no password needed: deleting reveals nothing)."""
        ...

    def unlock(self, master_password: str) -> UnlockResult:
        """NEVER raises: any password yields a full, plausible vault and a sigil."""
        ...

    def export_entry_seed(self, master_password: str, entry_id: str) -> bytes:
        """Return the decrypted DTE seed of one entry (for sharing). Never raises on wrong pw."""
        ...


@runtime_checkable
class ConventionalVaultAPI(Protocol):
    """Baseline KDF -> AES-GCM vault used only for the attack comparison (§7.10)."""

    @classmethod
    def new(cls, master_password: str, kdf_profile: str = "default") -> ConventionalVaultAPI:
        """Create an empty, encrypted vault."""
        ...

    @classmethod
    def from_dict(cls, data: dict) -> ConventionalVaultAPI:
        """Load from its serialised dict."""
        ...

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        ...

    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Decrypt, append, re-encrypt; returns the new id. Raises ``WrongPasswordError``."""
        ...

    def unlock(self, master_password: str) -> list[DecodedEntry]:
        """Return entries; raises ``WrongPasswordError`` — this IS the oracle HE removes."""
        ...


@dataclass(frozen=True)
class IdentityKeys:
    """A user's P-256 identity keypair (PEM-encoded)."""

    private_pem: bytes
    public_pem: bytes


@runtime_checkable
class SharingAPI(Protocol):
    """ECIES-style entry sharing with ECDSA signatures (PROJECT-BRIEF.md §9)."""

    def generate_identity(self) -> IdentityKeys:
        """Generate a fresh P-256 identity keypair."""
        ...

    def seal_share(
        self,
        seed: bytes,
        aad: dict,
        recipient_public_pem: bytes,
        sender_private_pem: bytes,
        sender_cert_pem: bytes,
    ) -> dict:
        """Encrypt ``seed`` to the recipient and sign; returns the envelope dict (§9)."""
        ...

    def open_share(
        self, envelope: dict, recipient_private_pem: bytes, trusted_ca_pems: list[bytes]
    ) -> tuple[bytes, dict]:
        """Verify chain + signature, then decrypt. Returns (seed, aad).

        Raises ``InvalidSignatureError`` on any verification failure.
        """
        ...
