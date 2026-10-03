"""Stub implementations of every honeycore contract (``HONEYCORE_IMPL=stub``).

Owner: T1 lead — Nidhi. Lets T2/T3/T4/T5 build against the frozen interfaces before the real
crypto lands. NOT secure: SHA-256 stands in for Argon2id/AES-CTR, and the DTEs are a trivial
byte-to-char mapping with no password model. They DO preserve the contract invariants:

* ``HoneyVault.unlock`` never raises — every password yields a full vault + sigil;
* every ``decode`` is total over seeds of the right length;
* seeds are fixed-length (``ENTRY_SEED_LEN``) regardless of content;
* the vault blob has the exact v1 shape (PROJECT-BRIEF.md §7.8) with no MAC / checksum.

Randomness comes only from ``secrets`` (AGENTS.md §1.5).
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from honeycore.interfaces import (
    CTR_NONCE_LEN,
    ENTRY_SEED_LEN,
    FORMAT_VERSION,
    INT_BYTES,
    KDF_PROFILES,
    MAX_FIELD_LEN,
    PASSWORD_SEED_INTS,
    PRINTABLE_MAX,
    PRINTABLE_MIN,
    SALT_LEN,
    USERNAME_SEED_INTS,
    CertInfo,
    DecodedEntry,
    Entry,
    EntryNotFoundError,
    IdentityKeys,
    InvalidInputError,
    InvalidSignatureError,
    KDFParams,
    Sigil,
    UnlockResult,
    WrongPasswordError,
)

_PRINTABLE_COUNT = PRINTABLE_MAX - PRINTABLE_MIN + 1  # 95

# Sigil tables (§7.9). Kept here so the stub is self-contained; the real ``sigil.py``
# (T1 Nidhi) may import these so the UI shows the same alphabet in both modes.
EMOJI64: tuple[str, ...] = (
    "🍯", "🐝", "🌊", "🐙", "🦀", "🐠", "🐬", "🐳",
    "🦈", "🐢", "🦭", "🪼", "🐚", "🧊", "🛶", "🧭",
    "🌴", "🌵", "🌻", "🌹", "🍀", "🍁", "🍄", "🌙",
    "🌟", "🌈", "🌋", "🪐", "🔥", "💧", "🍎", "🍋",
    "🍇", "🍉", "🍒", "🥝", "🥕", "🌽", "🥨", "🧀",
    "🦊", "🐼", "🐨", "🦁", "🐯", "🐸", "🦉", "🦋",
    "🎈", "🎲", "🎸", "🎯", "🚀", "🛸", "🏰", "🔑",
    "💎", "🔔", "📚", "🧩", "🪁", "🎨", "🧲", "🔭",
)  # fmt: skip
PALETTE16: tuple[str, ...] = (
    "#F5A524", "#E5484D", "#30A46C", "#0091FF", "#8E4EC6", "#12A594", "#F76B15", "#D6409F",
    "#3E63DD", "#46A758", "#FFC53D", "#AD7F58", "#00A2C7", "#E54666", "#6E56CF", "#8D8D8D",
)  # fmt: skip

_ENC_LABEL = b"honeyvault-enc-v1"
_SIGIL_LABEL = b"honeyvault-sigil-v1"


def _b64e(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64d(text: str, expected_len: int | None = None, what: str = "field") -> bytes:
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, TypeError, ValueError) as exc:
        raise InvalidInputError(f"{what}: invalid base64") from exc
    if expected_len is not None and len(raw) != expected_len:
        raise InvalidInputError(f"{what}: expected {expected_len} bytes, got {len(raw)}")
    return raw


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _validate_field(value: str, what: str) -> None:
    """§7.1: 1–32 printable ASCII chars. Error messages never echo the value."""
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_FIELD_LEN:
        raise InvalidInputError(f"{what} must be 1-{MAX_FIELD_LEN} characters")
    if any(not PRINTABLE_MIN <= ord(ch) <= PRINTABLE_MAX for ch in value):
        raise InvalidInputError(f"{what} must be printable ASCII")


def _lift(residue: int, modulus: int) -> int:
    """Random byte ``b`` with ``b % modulus == residue`` (so decode stays a simple ``%``)."""
    choices = (255 - residue) // modulus + 1
    return residue + modulus * secrets.randbelow(choices)


# ---------------------------------------------------------------------------------------------
# KDF + cipher
# ---------------------------------------------------------------------------------------------
class StubKDF:
    """``sha256(salt || password)`` expanded to ``hash_len``. Ignores cost params. NOT Argon2."""

    def derive(self, password: str, salt: bytes, params: KDFParams) -> bytes:
        """Derive ``params.hash_len`` bytes deterministically from (password, salt)."""
        base = hashlib.sha256(salt + password.encode("utf-8")).digest()
        out = base
        counter = 0
        while len(out) < params.hash_len:
            out += hashlib.sha256(base + counter.to_bytes(4, "big")).digest()
            counter += 1
        return out[: params.hash_len]


class StubCipher:
    """Keystream = ``sha256(key || nonce || counter)`` blocks, XORed with data. No MAC."""

    def apply(self, key: bytes, nonce: bytes, data: bytes) -> bytes:
        """XOR ``data`` with the keystream for (key, nonce); encrypt == decrypt."""
        stream = bytearray()
        counter = 0
        while len(stream) < len(data):
            stream += hashlib.sha256(key + nonce + counter.to_bytes(8, "big")).digest()
            counter += 1
        return bytes(a ^ b for a, b in zip(data, stream, strict=False))


# ---------------------------------------------------------------------------------------------
# DTEs
# ---------------------------------------------------------------------------------------------
class _StubFieldDTE:
    """Seed layout: ``[len byte][char byte × len][secrets padding]``, total ``seed_len`` bytes.

    decode: ``length = seed[0] % 32 + 1``; ``char = chr(seed[i] % 95 + 32)`` — total by
    construction. encode picks random bytes in the right residue classes (length-prefixed
    printable text, then ``secrets`` padding).
    """

    seed_len: int

    def __init__(self, seed_ints: int) -> None:
        self.seed_len = seed_ints * INT_BYTES

    def encode(self, value: str) -> bytes:
        """Encode a valid field (1–32 printable ASCII chars) into ``seed_len`` bytes."""
        _validate_field(value, "value")
        head = bytearray([_lift(len(value) - 1, MAX_FIELD_LEN)])
        head += bytes(_lift(ord(ch) - PRINTABLE_MIN, _PRINTABLE_COUNT) for ch in value)
        return bytes(head) + secrets.token_bytes(self.seed_len - len(head))

    def decode(self, seed: bytes) -> str:
        """TOTAL for ``len(seed) == seed_len``; other lengths are a programming error."""
        if len(seed) != self.seed_len:
            raise InvalidInputError(f"seed must be {self.seed_len} bytes")
        length = seed[0] % MAX_FIELD_LEN + 1
        return "".join(chr(b % _PRINTABLE_COUNT + PRINTABLE_MIN) for b in seed[1 : 1 + length])

    def sample(self) -> str:
        """Decode a uniformly random seed."""
        return self.decode(secrets.token_bytes(self.seed_len))


class StubPasswordModel(_StubFieldDTE):
    """Stub ``PasswordModel``: 66-int seed, uniform 'model', trailing-digit honeywords."""

    def __init__(self) -> None:
        super().__init__(PASSWORD_SEED_INTS)

    def sample_like(self, password: str) -> str:
        """Replace the trailing digit run with fresh random digits (append one if none)."""
        _validate_field(password, "password")
        stem = password.rstrip("0123456789")
        n_digits = len(password) - len(stem)
        if n_digits == 0:
            if len(password) < MAX_FIELD_LEN:
                stem, n_digits = password, 1
            else:
                stem, n_digits = password[:-1], 1
        digits = "".join(str(secrets.randbelow(10)) for _ in range(n_digits))
        return stem + digits

    def probability(self, password: str) -> float:
        """Constant placeholder probability."""
        return 1e-6


class StubUsernameModel(_StubFieldDTE):
    """Stub username ``FieldDTE``: 67-int seed (the real one spends int 0 on the domain)."""

    def __init__(self) -> None:
        super().__init__(USERNAME_SEED_INTS)


class StubEntryDTE:
    """``seed = username_seed (268 B) || password_seed (264 B)`` = ``ENTRY_SEED_LEN``."""

    seed_len: int = ENTRY_SEED_LEN

    def __init__(
        self,
        username_model: _StubFieldDTE | None = None,
        password_model: _StubFieldDTE | None = None,
    ) -> None:
        self.username_model = username_model or StubUsernameModel()
        self.password_model = password_model or StubPasswordModel()
        self._split = self.username_model.seed_len

    def encode(self, username: str, password: str) -> bytes:
        """Concatenate the two field seeds."""
        return self.username_model.encode(username) + self.password_model.encode(password)

    def decode(self, seed: bytes) -> tuple[str, str]:
        """TOTAL for ``len(seed) == ENTRY_SEED_LEN``."""
        if len(seed) != self.seed_len:
            raise InvalidInputError(f"seed must be {self.seed_len} bytes")
        return (
            self.username_model.decode(seed[: self._split]),
            self.password_model.decode(seed[self._split :]),
        )


# ---------------------------------------------------------------------------------------------
# Honey vault (blob v1)
# ---------------------------------------------------------------------------------------------
class StubHoneyVault:
    """``HoneyVaultAPI`` with the real blob v1 layout, stub KDF/cipher/DTE inside."""

    SCHEME = "HE-STUB-v1/SHA256-CTR/sha256"
    KDF_ALG = "stub-sha256"
    PW_MODEL_ID = "stub-password-v1"
    USER_MODEL_ID = "stub-username-v1"

    kdf = StubKDF()
    cipher = StubCipher()
    entry_dte = StubEntryDTE()

    def __init__(
        self,
        kdf_profile: str,
        kdf_params: KDFParams,
        salt: bytes,
        entries: list[dict[str, Any]] | None = None,
    ) -> None:
        self.kdf_profile = kdf_profile
        self.kdf_params = kdf_params
        self.salt = salt
        # each entry: id, service, nonce (bytes), ciphertext (bytes), created_at, updated_at
        self._entries: list[dict[str, Any]] = entries or []

    # ---- construction / serialisation ----
    @classmethod
    def new(cls, kdf_profile: str = "default") -> StubHoneyVault:
        """Empty vault with a fresh ``SALT_LEN``-byte salt."""
        if kdf_profile not in KDF_PROFILES:
            raise InvalidInputError(f"unknown kdf profile: {kdf_profile}")
        return cls(kdf_profile, KDF_PROFILES[kdf_profile], secrets.token_bytes(SALT_LEN))

    @classmethod
    def from_dict(cls, data: dict) -> StubHoneyVault:
        """Parse a blob v1 dict. Raises ``InvalidInputError`` if malformed (never pw-dependent)."""
        try:
            if data["format"] != "honeyvault" or data["version"] != FORMAT_VERSION:
                raise InvalidInputError("unsupported vault format/version")
            kdf = data["kdf"]
            params = KDFParams(
                time_cost=int(kdf["time_cost"]),
                memory_cost_kib=int(kdf["memory_cost_kib"]),
                parallelism=int(kdf["parallelism"]),
                hash_len=int(kdf["hash_len"]),
            )
            salt = _b64d(kdf["salt"], SALT_LEN, "kdf.salt")
            entries = [
                {
                    "id": str(e["id"]),
                    "service": str(e["service"]),
                    "nonce": _b64d(e["nonce"], CTR_NONCE_LEN, "entry.nonce"),
                    "ciphertext": _b64d(e["ciphertext"], ENTRY_SEED_LEN, "entry.ciphertext"),
                    "created_at": str(e["created_at"]),
                    "updated_at": str(e["updated_at"]),
                }
                for e in data["entries"]
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInputError("malformed vault blob") from exc
        return cls(str(kdf.get("profile", "default")), params, salt, entries)

    def to_dict(self) -> dict:
        """Blob v1 (PROJECT-BRIEF.md §7.8). Contains no MAC, checksum or key hash."""
        p = self.kdf_params
        return {
            "format": "honeyvault",
            "version": FORMAT_VERSION,
            "scheme": self.SCHEME,
            "kdf": {
                "alg": self.KDF_ALG,
                "profile": self.kdf_profile,
                "salt": _b64e(self.salt),
                "time_cost": p.time_cost,
                "memory_cost_kib": p.memory_cost_kib,
                "parallelism": p.parallelism,
                "hash_len": p.hash_len,
            },
            "dte": {
                "password_model": self.PW_MODEL_ID,
                "username_model": self.USER_MODEL_ID,
                "entry_seed_len": ENTRY_SEED_LEN,
            },
            "entries": [
                {
                    "id": e["id"],
                    "service": e["service"],
                    "nonce": _b64e(e["nonce"]),
                    "ciphertext": _b64e(e["ciphertext"]),
                    "created_at": e["created_at"],
                    "updated_at": e["updated_at"],
                }
                for e in self._entries
            ],
        }

    # ---- keys ----
    def _keys(self, master_password: str) -> tuple[bytes, bytes]:
        """(enc_key, sigil_key) via HMAC labels over the KDF output (§7.6)."""
        k = self.kdf.derive(master_password, self.salt, self.kdf_params)
        enc_key = hmac.new(k, _ENC_LABEL, hashlib.sha256).digest()
        sigil_key = hmac.new(k, _SIGIL_LABEL, hashlib.sha256).digest()
        return enc_key, sigil_key

    @staticmethod
    def _sigil(sigil_key: bytes) -> Sigil:
        h = hmac.new(sigil_key, b"sigil", hashlib.sha256).digest()
        return Sigil(
            emojis=(EMOJI64[h[0] % 64], EMOJI64[h[1] % 64], EMOJI64[h[2] % 64]),
            color=PALETTE16[h[3] % 16],
        )

    def _find(self, entry_id: str) -> dict[str, Any]:
        for e in self._entries:
            if e["id"] == entry_id:
                return e
        raise EntryNotFoundError("unknown entry id")

    def _seal(self, enc_key: bytes, entry: Entry) -> tuple[bytes, bytes]:
        if not isinstance(entry.service, str) or not entry.service.strip():
            raise InvalidInputError("service must be a non-empty string")
        seed = self.entry_dte.encode(entry.username, entry.password)
        nonce = secrets.token_bytes(CTR_NONCE_LEN)
        return nonce, self.cipher.apply(enc_key, nonce, seed)

    # ---- HoneyVaultAPI ----
    def entry_count(self) -> int:
        """Number of stored entries."""
        return len(self._entries)

    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Encrypt ONE entry under ``master_password`` and append it; returns its uuid4 id."""
        enc_key, _ = self._keys(master_password)
        nonce, ct = self._seal(enc_key, entry)
        now = _now()
        entry_id = str(uuid.uuid4())
        self._entries.append(
            {
                "id": entry_id,
                "service": entry.service,
                "nonce": nonce,
                "ciphertext": ct,
                "created_at": now,
                "updated_at": now,
            }
        )
        return entry_id

    def update_entry(self, master_password: str, entry_id: str, entry: Entry) -> None:
        """Re-encrypt only ``entry_id``. Raises ``EntryNotFoundError`` if the id is unknown."""
        target = self._find(entry_id)
        enc_key, _ = self._keys(master_password)
        target["nonce"], target["ciphertext"] = self._seal(enc_key, entry)
        target["service"] = entry.service
        target["updated_at"] = _now()

    def delete_entry(self, entry_id: str) -> None:
        """Remove ``entry_id``. Raises ``EntryNotFoundError`` if it is unknown."""
        self._entries.remove(self._find(entry_id))

    def unlock(self, master_password: str) -> UnlockResult:
        """NEVER raises: decrypt + total-decode every entry under whatever key ``pw`` yields."""
        enc_key, sigil_key = self._keys(master_password)
        entries = []
        for e in self._entries:
            seed = self.cipher.apply(enc_key, e["nonce"], e["ciphertext"])
            username, password = self.entry_dte.decode(seed)
            entries.append(
                DecodedEntry(
                    id=e["id"],
                    service=e["service"],
                    username=username,
                    password=password,
                    created_at=e["created_at"],
                    updated_at=e["updated_at"],
                )
            )
        return UnlockResult(entries=entries, sigil=self._sigil(sigil_key))

    def export_entry_seed(self, master_password: str, entry_id: str) -> bytes:
        """Decrypted seed of one entry (wrong pw -> decoy); ``EntryNotFoundError`` if unknown."""
        e = self._find(entry_id)
        enc_key, _ = self._keys(master_password)
        return self.cipher.apply(enc_key, e["nonce"], e["ciphertext"])


# ---------------------------------------------------------------------------------------------
# Conventional (baseline) vault
# ---------------------------------------------------------------------------------------------
class StubConventionalVault:
    """Baseline with an oracle: ``sha256(json) || json`` under the stub cipher.

    A wrong password breaks the checksum -> ``WrongPasswordError`` (stands in for AES-GCM
    ``InvalidTag``). Only for the attack comparison.
    """

    kdf = StubKDF()
    cipher = StubCipher()

    def __init__(
        self, kdf_profile: str, kdf_params: KDFParams, salt: bytes, nonce: bytes, ct: bytes
    ) -> None:
        self.kdf_profile = kdf_profile
        self.kdf_params = kdf_params
        self.salt = salt
        self.nonce = nonce
        self.ciphertext = ct

    def _key(self, master_password: str) -> bytes:
        return self.kdf.derive(master_password, self.salt, self.kdf_params)

    def _store(self, key: bytes, entries: list[dict[str, str]]) -> None:
        body = json.dumps(entries, separators=(",", ":")).encode("utf-8")
        self.nonce = secrets.token_bytes(CTR_NONCE_LEN)
        self.ciphertext = self.cipher.apply(key, self.nonce, hashlib.sha256(body).digest() + body)

    def _load(self, key: bytes) -> list[dict[str, str]]:
        plain = self.cipher.apply(key, self.nonce, self.ciphertext)
        digest, body = plain[:32], plain[32:]
        if not hmac.compare_digest(digest, hashlib.sha256(body).digest()):
            raise WrongPasswordError("wrong master password")
        return json.loads(body)

    @classmethod
    def new(cls, master_password: str, kdf_profile: str = "default") -> StubConventionalVault:
        """Create an empty vault already encrypted under ``master_password``."""
        if kdf_profile not in KDF_PROFILES:
            raise InvalidInputError(f"unknown kdf profile: {kdf_profile}")
        vault = cls(kdf_profile, KDF_PROFILES[kdf_profile], secrets.token_bytes(SALT_LEN), b"", b"")
        vault._store(vault._key(master_password), [])
        return vault

    @classmethod
    def from_dict(cls, data: dict) -> StubConventionalVault:
        """Parse the dict produced by ``to_dict``."""
        try:
            kdf = data["kdf"]
            params = KDFParams(
                int(kdf["time_cost"]),
                int(kdf["memory_cost_kib"]),
                int(kdf["parallelism"]),
                int(kdf["hash_len"]),
            )
            return cls(
                str(kdf["profile"]),
                params,
                _b64d(kdf["salt"], SALT_LEN, "kdf.salt"),
                _b64d(data["nonce"], CTR_NONCE_LEN, "nonce"),
                _b64d(data["ciphertext"], what="ciphertext"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInputError("malformed conventional vault") from exc

    def to_dict(self) -> dict:
        """JSON-compatible dict."""
        p = self.kdf_params
        return {
            "format": "conventional-vault",
            "version": 1,
            "scheme": "STUB-SHA256-CTR+SHA256-checksum",
            "kdf": {
                "alg": "stub-sha256",
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

    def add_entry(self, master_password: str, entry: Entry) -> str:
        """Append an entry (raises ``WrongPasswordError`` on a wrong password)."""
        _validate_field(entry.username, "username")
        _validate_field(entry.password, "password")
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
        """Return the entries or raise ``WrongPasswordError``."""
        return [DecodedEntry(**e) for e in self._load(self._key(master_password))]


# ---------------------------------------------------------------------------------------------
# Sharing + PKI
# ---------------------------------------------------------------------------------------------
def _placeholder_pem(label: str, body: str) -> bytes:
    b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
    return f"-----BEGIN {label}-----\n{b64}\n-----END {label}-----\n".encode("ascii")


def _placeholder_body(pem: bytes) -> str:
    try:
        lines = pem.decode("ascii").strip().splitlines()
        return base64.b64decode("".join(lines[1:-1]), validate=True).decode("utf-8")
    except (UnicodeDecodeError, binascii.Error, ValueError) as exc:
        raise InvalidSignatureError("not a stub PEM") from exc


class StubSharing:
    """``SharingAPI`` stub: base64 passthrough (NO encryption), envelope shape per §9."""

    ALG = "STUB-BASE64-PASSTHROUGH"
    SIGNATURE = "stub"

    def generate_identity(self) -> IdentityKeys:
        """Placeholder keypair; the two PEMs share a random key id."""
        kid = secrets.token_hex(8)
        return IdentityKeys(
            private_pem=_placeholder_pem("PRIVATE KEY", f"stub-private:{kid}"),
            public_pem=_placeholder_pem("PUBLIC KEY", f"stub-public:{kid}"),
        )

    def seal_share(
        self,
        seed: bytes,
        aad: dict,
        recipient_public_pem: bytes,
        sender_private_pem: bytes,
        sender_cert_pem: bytes,
    ) -> dict:
        """Envelope with the §9 keys; ``ciphertext`` is just base64(seed)."""
        return {
            "v": 1,
            "alg": self.ALG,
            "eph_pub": _b64e(secrets.token_bytes(91)),
            "salt": _b64e(secrets.token_bytes(32)),
            "nonce": _b64e(secrets.token_bytes(12)),
            "ciphertext": _b64e(seed),
            "aad": dict(aad),
            "sender_cert": sender_cert_pem.decode("ascii"),
            "signature": self.SIGNATURE,
        }

    def open_share(
        self, envelope: dict, recipient_private_pem: bytes, trusted_ca_pems: list[bytes]
    ) -> tuple[bytes, dict]:
        """Return (seed, aad). Raises ``InvalidSignatureError`` if the envelope was altered."""
        try:
            if envelope["v"] != 1 or envelope["alg"] != self.ALG:
                raise InvalidSignatureError("unsupported envelope")
            if not hmac.compare_digest(str(envelope["signature"]), self.SIGNATURE):
                raise InvalidSignatureError("bad signature")
            seed = base64.b64decode(envelope["ciphertext"], validate=True)
            aad = dict(envelope["aad"])
        except (KeyError, TypeError, ValueError, binascii.Error) as exc:
            raise InvalidSignatureError("malformed envelope") from exc
        if len(seed) != ENTRY_SEED_LEN:
            raise InvalidSignatureError("malformed envelope")
        return seed, aad


class StubPKI:
    """``PKIAPI`` stub: fake PEMs, NO real signatures. Deterministic ``CertInfo``.

    A user cert's body is ``stub-cert:<days>:<username>``; CA certs are ``stub-ca:root`` and
    ``stub-ca:issuing``. Validity starts at a fixed epoch and is never checked, so stub certs
    never expire. User certs carry no clientAuth EKU (like real user identity certs).
    """

    ROOT_CN = "HoneyVault Stub Root CA"
    ISSUER_CN = "HoneyVault Stub Issuing CA"
    EPOCH = datetime(2026, 1, 1, tzinfo=UTC)

    def root_ca_pem(self) -> bytes:
        """Placeholder root CA certificate."""
        return _placeholder_pem("CERTIFICATE", "stub-ca:root")

    def issuing_ca_pem(self) -> bytes:
        """Placeholder issuing CA certificate."""
        return _placeholder_pem("CERTIFICATE", "stub-ca:issuing")

    def issuing_ca_key_pem(self) -> bytes:
        """Placeholder issuing CA private key (pairs with ``issuing_ca_pem``)."""
        return _placeholder_pem("PRIVATE KEY", "stub-ca-key:issuing")

    def issue_user_certificate(
        self,
        username: str,
        public_pem: bytes,
        issuer_cert_pem: bytes,
        issuer_key_pem: bytes,
        days: int = 365,
    ) -> bytes:
        """Placeholder user certificate for ``username``; issuer arguments are not checked."""
        if not username or days < 1:
            raise InvalidInputError("username must be non-empty and days >= 1")
        return _placeholder_pem("CERTIFICATE", f"stub-cert:{days}:{username}")

    def verify_certificate(
        self,
        cert_pem: bytes,
        trusted_ca_pems: list[bytes],
        *,
        expected_cn: str | None = None,
        require_client_auth: bool = False,
    ) -> CertInfo:
        """Accept any stub user cert (``trusted_ca_pems`` ignored); check CN and EKU.

        Raises ``InvalidSignatureError`` for non-user certs, a CN mismatch, or
        ``require_client_auth`` (stub user certs have no clientAuth EKU).
        """
        try:
            info = self.describe(cert_pem)
        except InvalidInputError as exc:
            raise InvalidSignatureError("not a stub certificate") from exc
        if not _placeholder_body(cert_pem).startswith("stub-cert:"):
            raise InvalidSignatureError("not a stub user certificate")
        if expected_cn is not None and not hmac.compare_digest(
            info.subject_cn.encode("utf-8"), expected_cn.encode("utf-8")
        ):
            raise InvalidSignatureError("certificate CN mismatch")
        if require_client_auth:
            raise InvalidSignatureError("certificate lacks clientAuth EKU")
        return info

    def describe(self, cert_pem: bytes) -> CertInfo:
        """Parse a stub cert without verifying it. ``InvalidInputError`` if not a stub cert."""
        try:
            body = _placeholder_body(cert_pem)
        except InvalidSignatureError as exc:
            raise InvalidInputError("not a stub certificate") from exc
        days = 3650
        if body == "stub-ca:root":
            subject, issuer = self.ROOT_CN, self.ROOT_CN
        elif body == "stub-ca:issuing":
            subject, issuer = self.ISSUER_CN, self.ROOT_CN
        elif body.startswith("stub-cert:"):
            days_text, _, subject = body.removeprefix("stub-cert:").partition(":")
            if not days_text.isdigit() or not subject:
                raise InvalidInputError("not a stub certificate")
            days, issuer = int(days_text), self.ISSUER_CN
        else:
            raise InvalidInputError("not a stub certificate")
        digest = hashlib.sha256(cert_pem).digest()
        return CertInfo(
            subject_cn=subject,
            issuer_cn=issuer,
            serial=int.from_bytes(digest[:8], "big") >> 1,
            not_before=self.EPOCH.isoformat(),
            not_after=(self.EPOCH + timedelta(days=days)).isoformat(),
            fingerprint_sha256=digest.hex(),
        )
