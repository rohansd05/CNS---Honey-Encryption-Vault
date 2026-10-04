"""Honeywords service for sweetword generation and verification.

Owner: T2 — Rohan. Phase 1 (PROJECT-BRIEF.md §8).
Pure library logic: no database access.
"""

from __future__ import annotations

import base64
import hmac
import secrets
import string
from dataclasses import dataclass

from argon2.low_level import Type, hash_secret_raw

from honeycore.interfaces import KDF_PROFILES, SALT_LEN, InvalidInputError, PasswordModel

PRINTABLE_MIN = 0x20
PRINTABLE_MAX = 0x7E
MAX_FIELD_LEN = 32


@dataclass(frozen=True)
class HoneywordRecord:
    """Stores salt, sweetword hashes, and KDF profile for a user."""

    salt_b64: str
    hashes: list[str]  # hex strings
    kdf_profile: str


def _is_valid_field(value: str) -> bool:
    """Check if value is 1..32 printable ASCII characters."""
    return 1 <= len(value) <= MAX_FIELD_LEN and all(
        PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in value
    )


def _tail_tweak(real: str) -> str:
    """Generate a decoy candidate by tweaking the trailing digit/symbol run."""
    run_len = 0
    for c in reversed(real):
        if c.isdigit() or c in string.punctuation:
            run_len += 1
        else:
            break

    if run_len > 0:
        stem = real[:-run_len]
        run = real[-run_len:]
        tweaked_chars: list[str] = []
        for c in run:
            if c.isdigit():
                tweaked_chars.append(secrets.choice(string.digits))
            else:
                tweaked_chars.append(secrets.choice(string.punctuation))
        candidate = stem + "".join(tweaked_chars)
        if candidate != real:
            return candidate

    # If no trailing run or tweak produced identical string, append 1–2 digits
    n_digits = secrets.choice([1, 2])
    digits = "".join(secrets.choice(string.digits) for _ in range(n_digits))
    if len(real) + n_digits <= MAX_FIELD_LEN:
        return real + digits
    return real[:-n_digits] + digits


def generate_sweetwords(
    real: str,
    k: int,
    password_model: PasswordModel,
) -> tuple[list[str], int]:
    """Generate k distinct sweetwords containing real, returning (sweetwords, real_index).

    Composition:
    - the real password
    - about half via password_model.sample_like(real)
    - the rest via tail-tweaks (trailing digit/symbol run randomised; else append 1–2 digits)
    - topped up with password_model.sample() if short

    All sweetwords are distinct, valid 1..32 printable ASCII, and shuffled using
    secrets.SystemRandom.
    """
    if not _is_valid_field(real):
        raise InvalidInputError("Real password must be 1-32 printable ASCII characters")
    if k < 2:
        raise InvalidInputError("Honeywords k must be at least 2")

    sweetwords: set[str] = {real}
    target_sample_like = (k - 1) // 2

    # 1. Sample-like decoys
    for _ in range(target_sample_like * 20):
        if len(sweetwords) >= 1 + target_sample_like:
            break
        candidate = password_model.sample_like(real)
        if _is_valid_field(candidate) and candidate not in sweetwords:
            sweetwords.add(candidate)

    # 2. Tail-tweaks for the rest
    for _ in range((k - len(sweetwords)) * 20):
        if len(sweetwords) >= k:
            break
        candidate = _tail_tweak(real)
        if _is_valid_field(candidate) and candidate not in sweetwords:
            sweetwords.add(candidate)

    # 3. Top up with password_model.sample() if still short
    for _ in range((k - len(sweetwords)) * 20):
        if len(sweetwords) >= k:
            break
        candidate = password_model.sample()
        if _is_valid_field(candidate) and candidate not in sweetwords:
            sweetwords.add(candidate)

    # 4. Fallback random printable strings if model was exhausted
    chars = string.ascii_letters + string.digits
    while len(sweetwords) < k:
        length = max(8, min(len(real), 16))
        candidate = "".join(secrets.choice(chars) for _ in range(length))
        if candidate not in sweetwords:
            sweetwords.add(candidate)

    rng = secrets.SystemRandom()
    sweetwords_list = list(sweetwords)
    rng.shuffle(sweetwords_list)
    real_index = sweetwords_list.index(real)

    return sweetwords_list, real_index


def hash_sweetword(pw: str, salt: bytes | str, profile: str) -> str:
    """Hash a sweetword using Argon2id with KDF_PROFILES[profile].

    Returns a 32-byte hash as a lowercase hex string.
    """
    if profile not in KDF_PROFILES:
        raise InvalidInputError(f"Unknown KDF profile: {profile}")

    salt_bytes = base64.b64decode(salt) if isinstance(salt, str) else bytes(salt)
    params = KDF_PROFILES[profile]

    raw = hash_secret_raw(
        secret=pw.encode("utf-8"),
        salt=salt_bytes,
        time_cost=params.time_cost,
        memory_cost=params.memory_cost_kib,
        parallelism=params.parallelism,
        hash_len=params.hash_len,
        type=Type.ID,
    )
    return raw.hex()


def create_record(
    real: str,
    k: int,
    profile: str,
    password_model: PasswordModel,
) -> tuple[HoneywordRecord, int]:
    """Generate sweetwords and derive sweetword hashes under a single per-user salt.

    Returns (record, real_index).
    """
    salt = secrets.token_bytes(SALT_LEN)
    sweetwords, real_index = generate_sweetwords(real, k, password_model)
    hashes = [hash_sweetword(sw, salt, profile) for sw in sweetwords]
    salt_b64 = base64.b64encode(salt).decode("ascii")

    record = HoneywordRecord(
        salt_b64=salt_b64,
        hashes=hashes,
        kdf_profile=profile,
    )
    return record, real_index


def find_index(record: HoneywordRecord, candidate: str) -> int | None:
    """Verify candidate against all sweetword hashes in constant time (no early exit).

    Hashes candidate once using the record's salt and KDF profile, then compares
    against all hashes in record.hashes using hmac.compare_digest.
    """
    salt = base64.b64decode(record.salt_b64)
    candidate_hash = hash_sweetword(candidate, salt, record.kdf_profile)

    found_index: int | None = None
    for i, h in enumerate(record.hashes):
        if hmac.compare_digest(candidate_hash, h):
            found_index = i

    return found_index
