"""Tests for ``honeycore.baseline`` (PROJECT-BRIEF.md §7.10). Owner: T1 — Dhruv.

The baseline is the vault WITH a password oracle: these tests check that the oracle exists.
Uses the fast ``demo`` KDF profile.
"""

from __future__ import annotations

import base64
import copy
import json
from typing import Any

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from honeycore.baseline import AAD, GCM_NONCE_LEN, ConventionalVault
from honeycore.interfaces import (
    KDF_PROFILES,
    SALT_LEN,
    ConventionalVaultAPI,
    Entry,
    InvalidInputError,
    WrongPasswordError,
)
from honeycore.kdf import Argon2KDF, derive_subkeys

MASTER = "Tr0ub4dor&3-master"
ENTRIES = [
    Entry("github.com", "alice@gmail.com", "monkey123!"),
    Entry("bank.example", "alice_1990", "correct horse battery"),
]


@pytest.fixture(scope="module")
def blob() -> dict:
    vault = ConventionalVault.new(MASTER, "demo")
    for e in ENTRIES:
        vault.add_entry(MASTER, e)
    return vault.to_dict()


@pytest.fixture
def vault(blob: dict) -> ConventionalVault:
    return ConventionalVault.from_dict(copy.deepcopy(blob))


def _flip(b64: str, index: int) -> str:
    raw = bytearray(base64.b64decode(b64))
    raw[index] ^= 0x01
    return base64.b64encode(bytes(raw)).decode()


def test_satisfies_protocol(vault: ConventionalVault) -> None:
    assert isinstance(vault, ConventionalVaultAPI)


def test_new_vault_is_empty_and_encrypted() -> None:
    v = ConventionalVault.new(MASTER, "demo")
    assert v.unlock(MASTER) == []
    assert len(v.nonce) == GCM_NONCE_LEN
    assert len(v.salt) == SALT_LEN
    with pytest.raises(WrongPasswordError):
        v.unlock("wrong")


def test_new_unknown_profile_raises() -> None:
    with pytest.raises(InvalidInputError):
        ConventionalVault.new(MASTER, "turbo")


# --- right / wrong password --------------------------------------------------------------


def test_right_password_returns_entries(vault: ConventionalVault) -> None:
    got = vault.unlock(MASTER)
    assert [(e.service, e.username, e.password) for e in got] == [
        (e.service, e.username, e.password) for e in ENTRIES
    ]
    assert len({e.id for e in got}) == len(ENTRIES)
    assert all(e.created_at == e.updated_at for e in got)


@pytest.mark.parametrize("password", ["", "wrong", MASTER + " ", MASTER.lower(), "пароль"])
def test_wrong_password_raises(vault: ConventionalVault, password: str) -> None:
    with pytest.raises(WrongPasswordError) as excinfo:
        vault.unlock(password)
    assert MASTER not in str(excinfo.value)
    assert password not in str(excinfo.value) or password in ("", "wrong")


def test_try_password_is_an_oracle(vault: ConventionalVault) -> None:
    assert vault.try_password(MASTER) is True
    assert vault.try_password("wrong") is False
    assert vault.try_password("") is False


def test_lone_surrogate_password_is_just_wrong(vault: ConventionalVault) -> None:
    assert vault.try_password("\ud800") is False


# --- add_entry ---------------------------------------------------------------------------


def test_add_entry_reencrypts_with_new_nonce(vault: ConventionalVault) -> None:
    old_nonce, old_ct = vault.nonce, vault.ciphertext
    new_id = vault.add_entry(MASTER, Entry("reddit.com", "bob", "hunter2"))
    assert vault.nonce != old_nonce
    assert vault.ciphertext != old_ct
    got = vault.unlock(MASTER)
    assert len(got) == len(ENTRIES) + 1
    assert (got[-1].id, got[-1].username, got[-1].password) == (new_id, "bob", "hunter2")


def test_add_entry_wrong_password_raises_and_leaves_vault(vault: ConventionalVault) -> None:
    before = vault.to_dict()
    with pytest.raises(WrongPasswordError):
        vault.add_entry("wrong", Entry("x.com", "bob", "pw"))
    assert vault.to_dict() == before


@pytest.mark.parametrize(
    "entry",
    [Entry("", "bob", "pw"), Entry("x.com", "", "pw"), Entry("x.com", "bob", "p" * 33)],
)
def test_add_entry_invalid_input(vault: ConventionalVault, entry: Entry) -> None:
    before = vault.to_dict()
    with pytest.raises(InvalidInputError):
        vault.add_entry(MASTER, entry)
    assert vault.to_dict() == before


def test_plaintext_is_canonical_entries_json(vault: ConventionalVault) -> None:
    k = Argon2KDF().derive(MASTER, vault.salt, vault.kdf_params)
    body = AESGCM(derive_subkeys(k)[0]).decrypt(vault.nonce, vault.ciphertext, AAD)
    parsed = json.loads(body)
    assert set(parsed) == {"entries"}
    assert body == json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()


# --- tampering ---------------------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 17, -1])
def test_tampered_ciphertext_raises(blob: dict, index: int) -> None:
    tampered = copy.deepcopy(blob)
    tampered["ciphertext"] = _flip(tampered["ciphertext"], index)
    v = ConventionalVault.from_dict(tampered)
    with pytest.raises(WrongPasswordError):
        v.unlock(MASTER)
    assert v.try_password(MASTER) is False


@pytest.mark.parametrize(("field", "path"), [("nonce", ("nonce",)), ("salt", ("kdf", "salt"))])
def test_tampered_nonce_or_salt_raises(blob: dict, field: str, path: tuple[str, ...]) -> None:
    tampered = copy.deepcopy(blob)
    holder = tampered if len(path) == 1 else tampered[path[0]]
    holder[field] = _flip(holder[field], 0)
    with pytest.raises(WrongPasswordError):
        ConventionalVault.from_dict(tampered).unlock(MASTER)


def test_truncated_ciphertext_raises(blob: dict) -> None:
    tampered = copy.deepcopy(blob)
    raw = base64.b64decode(tampered["ciphertext"])
    tampered["ciphertext"] = base64.b64encode(raw[:-1]).decode()
    with pytest.raises(WrongPasswordError):
        ConventionalVault.from_dict(tampered).unlock(MASTER)


# --- serialisation -----------------------------------------------------------------------


def test_blob_shape(blob: dict) -> None:
    demo = KDF_PROFILES["demo"]
    assert set(blob) == {"format", "version", "kdf", "nonce", "ciphertext"}
    assert blob["format"] == "conventional"
    assert blob["version"] == 1
    assert blob["kdf"] == {
        "alg": "argon2id",
        "profile": "demo",
        "salt": blob["kdf"]["salt"],
        "time_cost": demo.time_cost,
        "memory_cost_kib": demo.memory_cost_kib,
        "parallelism": demo.parallelism,
        "hash_len": demo.hash_len,
    }
    assert len(base64.b64decode(blob["nonce"], validate=True)) == GCM_NONCE_LEN


def test_round_trip(vault: ConventionalVault, blob: dict) -> None:
    reloaded = ConventionalVault.from_dict(json.loads(json.dumps(vault.to_dict())))
    assert reloaded.to_dict() == blob
    assert reloaded.unlock(MASTER) == vault.unlock(MASTER)


def _put(path: tuple[str, ...], value: Any) -> Any:
    def mutate(b: dict) -> None:
        obj = b
        for p in path[:-1]:
            obj = obj[p]
        obj[path[-1]] = value

    return mutate


@pytest.mark.parametrize(
    "mutate",
    [
        _put(("format",), "honeyvault"),
        _put(("version",), 2),
        _put(("tag",), "extra"),
        _put(("kdf", "alg"), "pbkdf2"),
        _put(("kdf", "time_cost"), 0),
        _put(("nonce",), base64.b64encode(b"\x00" * 16).decode()),
        _put(("ciphertext",), "!!!"),
        _put(("ciphertext",), base64.b64encode(b"\x00" * 8).decode()),
        _put(("ciphertext",), None),
    ],
)
def test_from_dict_rejects_malformed(blob: dict, mutate: Any) -> None:
    bad = copy.deepcopy(blob)
    mutate(bad)
    with pytest.raises(ValueError):
        ConventionalVault.from_dict(bad)
