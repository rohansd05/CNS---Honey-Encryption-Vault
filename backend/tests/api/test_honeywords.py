"""Tests for sweetword generation, Argon2 hashing, and constant-time verification.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import hmac

import pytest

from app.services.honeywords import (
    HoneywordRecord,
    create_record,
    find_index,
    generate_sweetwords,
    hash_sweetword,
)
from honeycore.interfaces import InvalidInputError
from honeycore.stubs import StubPasswordModel


@pytest.fixture
def model() -> StubPasswordModel:
    return StubPasswordModel()


def test_generate_sweetwords_basic(model: StubPasswordModel) -> None:
    """Generate k distinct sweetwords containing the real one at real_index."""
    k = 10
    real = "CorrectHorse99!"
    sweetwords, real_index = generate_sweetwords(real, k, model)

    assert len(sweetwords) == k
    assert len(set(sweetwords)) == k, "All sweetwords must be distinct"
    assert 0 <= real_index < k
    assert sweetwords[real_index] == real

    for sw in sweetwords:
        assert 1 <= len(sw) <= 32
        assert all(0x20 <= ord(c) <= 0x7E for c in sw)


def test_generate_sweetwords_different_endings(model: StubPasswordModel) -> None:
    """Tail tweaks handle digit runs, symbol runs, and passwords ending in letters."""
    passwords = [
        "summer2023",  # trailing digits
        "secret#@!",  # trailing symbols
        "alphapassword",  # no trailing digits/symbols (appends digits)
        "a",  # single character
        "A" * 32,  # max length
    ]
    for pw in passwords:
        sweetwords, real_index = generate_sweetwords(pw, 10, model)
        assert len(sweetwords) == 10
        assert len(set(sweetwords)) == 10
        assert sweetwords[real_index] == pw


def test_generate_sweetwords_invalid_inputs(model: StubPasswordModel) -> None:
    """Invalid password lengths, characters, or k values raise InvalidInputError."""
    with pytest.raises(InvalidInputError):
        generate_sweetwords("", 10, model)

    with pytest.raises(InvalidInputError):
        generate_sweetwords("A" * 33, 10, model)

    with pytest.raises(InvalidInputError):
        generate_sweetwords("has\nnewline", 10, model)

    with pytest.raises(InvalidInputError):
        generate_sweetwords("valid", 1, model)


def test_hash_sweetword_demo_profile() -> None:
    """Hash sweetword using Argon2id with demo profile returning 32B hex."""
    salt = b"1234567890123456"
    h1 = hash_sweetword("hunter2", salt, "demo")
    assert isinstance(h1, str)
    assert len(h1) == 64  # 32 bytes hex encoded
    assert bytes.fromhex(h1)  # valid hex

    # Deterministic with same salt and password
    assert hash_sweetword("hunter2", salt, "demo") == h1

    # Different password yields different hash
    assert hash_sweetword("hunter3", salt, "demo") != h1

    # Different salt yields different hash
    salt2 = b"6543210987654321"
    assert hash_sweetword("hunter2", salt2, "demo") != h1


def test_create_record_and_find_index(model: StubPasswordModel) -> None:
    """create_record derives ONE salt for all k sweetwords, and find_index matches."""
    real = "dragon123"
    record, real_index = create_record(real, 10, "demo", model)

    assert isinstance(record, HoneywordRecord)
    assert len(record.hashes) == 10
    assert record.kdf_profile == "demo"
    assert len(record.salt_b64) > 0

    # Real password matches real_index
    assert find_index(record, real) == real_index

    # Unknown password returns None
    assert find_index(record, "not_a_sweetword_at_all_999") is None
    assert find_index(record, "dragon124") != real_index  # if 124 is a decoy or not


def test_find_index_matches_all_decoys(model: StubPasswordModel) -> None:
    """find_index correctly matches every decoy in the generated sweetword set."""
    real = "p@ssword!12"
    salt = b"0123456789abcdef"
    sweetwords, real_index = generate_sweetwords(real, 10, model)
    hashes = [hash_sweetword(sw, salt, "demo") for sw in sweetwords]
    import base64

    record = HoneywordRecord(
        salt_b64=base64.b64encode(salt).decode("ascii"),
        hashes=hashes,
        kdf_profile="demo",
    )

    for idx, sw in enumerate(sweetwords):
        matched = find_index(record, sw)
        assert matched == idx


def test_find_index_timing_constant_time(
    model: StubPasswordModel, monkeypatch: pytest.MonkeyPatch
) -> None:
    """find_index must compare against ALL hashes with hmac.compare_digest (no early exit)."""
    real = "winter2024"
    record, _ = create_record(real, 10, "demo", model)

    call_count = 0
    orig_compare = hmac.compare_digest

    def counting_compare(a: str | bytes, b: str | bytes) -> bool:
        nonlocal call_count
        call_count += 1
        return orig_compare(a, b)

    monkeypatch.setattr(hmac, "compare_digest", counting_compare)

    # Even when real password matches (regardless of where it is in the list)
    find_index(record, real)
    assert call_count == 10, "Must compare against all 10 hashes without early exit"

    call_count = 0
    find_index(record, "completely_unknown_password")
    assert call_count == 10, "Must compare against all 10 hashes on failure"
