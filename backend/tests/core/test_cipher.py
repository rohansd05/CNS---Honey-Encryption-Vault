"""Tests for ``honeycore.cipher`` (PROJECT-BRIEF.md §7.7). Owner: T1 — Dhruv."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from honeycore.cipher import KEY_LEN, AESCTRCipher, new_nonce
from honeycore.interfaces import CTR_NONCE_LEN, ENTRY_SEED_LEN, InvalidInputError, StreamCipher

# NIST SP 800-38A, Appendix F.5.5 — CTR-AES256.Encrypt.
NIST_KEY = bytes.fromhex("603deb1015ca71be2b73aef0857d77811f352c073b6108d72d9810a30914dff4")
NIST_COUNTER = bytes.fromhex("f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff")
NIST_PLAINTEXT = bytes.fromhex(
    "6bc1bee22e409f96e93d7e117393172a"
    "ae2d8a571e03ac9c9eb76fac45af8e51"
    "30c81c46a35ce411e5fbc1191a0a52ef"
    "f69f2445df4f9b17ad2b417be66c3710"
)
NIST_CIPHERTEXT = bytes.fromhex(
    "601ec313775789a5b7a7f504bbf3d228"
    "f443e3ca4d62b59aca84e990cacaf5c5"
    "2b0930daa23de94ce87017ba2d84988d"
    "dfc9c58db67aada613c2dd08457941a6"
)

KEY = bytes(range(KEY_LEN))
NONCE = bytes(range(CTR_NONCE_LEN))
cipher = AESCTRCipher()


def test_satisfies_protocol() -> None:
    assert isinstance(cipher, StreamCipher)


def test_nist_known_answer_encrypt() -> None:
    assert cipher.apply(NIST_KEY, NIST_COUNTER, NIST_PLAINTEXT) == NIST_CIPHERTEXT


def test_nist_known_answer_decrypt() -> None:
    assert cipher.apply(NIST_KEY, NIST_COUNTER, NIST_CIPHERTEXT) == NIST_PLAINTEXT


def test_nist_known_answer_partial_block() -> None:
    # CTR has no padding: a truncated plaintext gives the truncated ciphertext.
    assert cipher.apply(NIST_KEY, NIST_COUNTER, NIST_PLAINTEXT[:21]) == NIST_CIPHERTEXT[:21]


@given(st.binary(max_size=2 * ENTRY_SEED_LEN))
def test_apply_is_an_involution(data: bytes) -> None:
    assert cipher.apply(KEY, NONCE, cipher.apply(KEY, NONCE, data)) == data


@given(st.binary(max_size=2 * ENTRY_SEED_LEN))
def test_ciphertext_length_equals_plaintext_length(data: bytes) -> None:
    assert len(cipher.apply(KEY, NONCE, data)) == len(data)


def test_entry_seed_roundtrip_no_expansion() -> None:
    seed = bytes(i % 256 for i in range(ENTRY_SEED_LEN))
    ct = cipher.apply(KEY, NONCE, seed)
    assert len(ct) == ENTRY_SEED_LEN
    assert ct != seed
    assert cipher.apply(KEY, NONCE, ct) == seed


def test_empty_input() -> None:
    assert cipher.apply(KEY, NONCE, b"") == b""


def test_deterministic_for_same_key_and_nonce() -> None:
    assert cipher.apply(KEY, NONCE, b"x" * 100) == cipher.apply(KEY, NONCE, b"x" * 100)


def test_differs_by_nonce_and_key() -> None:
    data = b"\x00" * 64
    base = cipher.apply(KEY, NONCE, data)
    assert cipher.apply(KEY, bytes(CTR_NONCE_LEN), data) != base
    assert cipher.apply(bytes(KEY_LEN), NONCE, data) != base


def test_wrong_key_decrypts_without_error() -> None:
    # No MAC: a wrong key must silently yield a different same-length plaintext.
    seed = b"\x42" * ENTRY_SEED_LEN
    ct = cipher.apply(KEY, NONCE, seed)
    wrong = cipher.apply(b"\xff" * KEY_LEN, NONCE, ct)
    assert len(wrong) == ENTRY_SEED_LEN
    assert wrong != seed


def test_accepts_bytearray_and_memoryview() -> None:
    data = b"honey" * 10
    expected = cipher.apply(KEY, NONCE, data)
    assert cipher.apply(bytearray(KEY), memoryview(NONCE), bytearray(data)) == expected


@pytest.mark.parametrize("key_len", [0, 16, 24, 31, 33, 64])
def test_wrong_key_length_raises(key_len: int) -> None:
    with pytest.raises(InvalidInputError):
        cipher.apply(b"\x00" * key_len, NONCE, b"data")


@pytest.mark.parametrize("nonce_len", [0, 8, 12, 15, 17, 32])
def test_wrong_nonce_length_raises(nonce_len: int) -> None:
    with pytest.raises(InvalidInputError):
        cipher.apply(KEY, b"\x00" * nonce_len, b"data")


def test_new_nonce_length_and_uniqueness() -> None:
    nonces = {new_nonce() for _ in range(64)}
    assert len(nonces) == 64
    assert all(len(n) == CTR_NONCE_LEN for n in nonces)
