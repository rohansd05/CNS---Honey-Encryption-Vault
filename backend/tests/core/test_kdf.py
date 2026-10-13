"""Tests for ``honeycore.kdf`` (PROJECT-BRIEF.md §7.6). Owner: T1 — Dhruv.

Uses the ``demo`` profile for speed, except where a test compares profiles.
"""

from __future__ import annotations

import dataclasses
import hashlib
import hmac

import pytest

from honeycore.interfaces import KDF, KDF_PROFILES, SALT_LEN, InvalidInputError
from honeycore.kdf import ENC_KEY_LABEL, SIGIL_KEY_LABEL, Argon2KDF, derive_subkeys, new_salt

DEMO = KDF_PROFILES["demo"]
SALT_A = bytes(range(SALT_LEN))
SALT_B = bytes(range(1, SALT_LEN + 1))


@pytest.fixture(scope="module")
def kdf() -> Argon2KDF:
    return Argon2KDF()


def test_satisfies_protocol(kdf: Argon2KDF) -> None:
    assert isinstance(kdf, KDF)


def test_deterministic(kdf: Argon2KDF) -> None:
    assert kdf.derive("correct horse", SALT_A, DEMO) == kdf.derive("correct horse", SALT_A, DEMO)


def test_output_length_default(kdf: Argon2KDF) -> None:
    assert len(kdf.derive("pw", SALT_A, DEMO)) == DEMO.hash_len == 32


@pytest.mark.parametrize("hash_len", [16, 32, 64])
def test_output_length_follows_params(kdf: Argon2KDF, hash_len: int) -> None:
    params = dataclasses.replace(DEMO, hash_len=hash_len)
    assert len(kdf.derive("pw", SALT_A, params)) == hash_len


def test_differs_by_password(kdf: Argon2KDF) -> None:
    assert kdf.derive("hunter2", SALT_A, DEMO) != kdf.derive("hunter3", SALT_A, DEMO)


def test_differs_by_salt(kdf: Argon2KDF) -> None:
    assert kdf.derive("hunter2", SALT_A, DEMO) != kdf.derive("hunter2", SALT_B, DEMO)


def test_differs_by_profile(kdf: Argon2KDF) -> None:
    keys = {kdf.derive("hunter2", SALT_A, params) for params in KDF_PROFILES.values()}
    assert len(keys) == len(KDF_PROFILES)


def test_never_rejects_a_password(kdf: Argon2KDF) -> None:
    # Invariant §1.2: any master password (empty, unicode) must still yield a key.
    keys = {kdf.derive(pw, SALT_A, DEMO) for pw in ["", " ", "pässwörd", "密码", "a" * 200]}
    assert len(keys) == 5
    assert all(len(k) == 32 for k in keys)


def test_password_is_utf8_encoded(kdf: Argon2KDF) -> None:
    from argon2.low_level import Type, hash_secret_raw

    expected = hash_secret_raw(
        "pässwörd".encode(),
        SALT_A,
        time_cost=DEMO.time_cost,
        memory_cost=DEMO.memory_cost_kib,
        parallelism=DEMO.parallelism,
        hash_len=DEMO.hash_len,
        type=Type.ID,
    )
    assert kdf.derive("pässwörd", SALT_A, DEMO) == expected


def test_matches_independent_argon2id(kdf: Argon2KDF) -> None:
    """Cross-check against cryptography's Argon2id (skipped if this OpenSSL lacks it)."""
    try:
        from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
    except ImportError:
        pytest.skip("cryptography has no Argon2id")
    try:
        ref = Argon2id(
            salt=SALT_A,
            length=DEMO.hash_len,
            iterations=DEMO.time_cost,
            lanes=DEMO.parallelism,
            memory_cost=DEMO.memory_cost_kib,
        ).derive(b"hunter2")
    except Exception as exc:  # UnsupportedAlgorithm on older OpenSSL builds
        pytest.skip(f"Argon2id unsupported by this backend: {type(exc).__name__}")
    assert kdf.derive("hunter2", SALT_A, DEMO) == ref


@pytest.mark.parametrize("salt_len", [0, 8, SALT_LEN - 1, SALT_LEN + 1, 32])
def test_wrong_salt_length_raises(kdf: Argon2KDF, salt_len: int) -> None:
    with pytest.raises(InvalidInputError):
        kdf.derive("pw", b"\x00" * salt_len, DEMO)


def test_salt_error_does_not_leak_password(kdf: Argon2KDF) -> None:
    with pytest.raises(InvalidInputError) as excinfo:
        kdf.derive("sup3r-s3cret", b"short", DEMO)
    assert "sup3r-s3cret" not in str(excinfo.value)


# --- subkeys -----------------------------------------------------------------------------


def test_subkeys_differ_and_are_32_bytes() -> None:
    enc_key, sigil_key = derive_subkeys(b"\x11" * 32)
    assert enc_key != sigil_key
    assert len(enc_key) == len(sigil_key) == 32


def test_subkeys_match_spec() -> None:
    master = bytes(range(32))
    enc_key, sigil_key = derive_subkeys(master)
    assert ENC_KEY_LABEL == b"honeyvault-enc-v1"
    assert SIGIL_KEY_LABEL == b"honeyvault-sigil-v1"
    assert enc_key == hmac.new(master, b"honeyvault-enc-v1", hashlib.sha256).digest()
    assert sigil_key == hmac.new(master, b"honeyvault-sigil-v1", hashlib.sha256).digest()


def test_subkeys_deterministic_and_key_dependent() -> None:
    assert derive_subkeys(b"\x01" * 32) == derive_subkeys(b"\x01" * 32)
    assert derive_subkeys(b"\x01" * 32) != derive_subkeys(b"\x02" * 32)


def test_subkeys_differ_from_master() -> None:
    master = b"\x07" * 32
    assert master not in derive_subkeys(master)


def test_subkeys_reject_empty_master() -> None:
    with pytest.raises(InvalidInputError):
        derive_subkeys(b"")


def test_end_to_end_key_schedule(kdf: Argon2KDF) -> None:
    enc_a, sigil_a = derive_subkeys(kdf.derive("hunter2", SALT_A, DEMO))
    enc_b, sigil_b = derive_subkeys(kdf.derive("hunter3", SALT_A, DEMO))
    assert len({enc_a, sigil_a, enc_b, sigil_b}) == 4


# --- salts -------------------------------------------------------------------------------


def test_new_salt_length_and_uniqueness() -> None:
    salts = {new_salt() for _ in range(64)}
    assert len(salts) == 64
    assert all(len(s) == SALT_LEN for s in salts)
