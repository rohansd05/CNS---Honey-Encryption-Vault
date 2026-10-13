"""Tests for ``honeycore.vault`` (PROJECT-BRIEF.md §7.8). Owner: T1 — Dhruv.

Uses ``HoneyVault.bind(StubEntryDTE())`` (the real PCFG entry DTE is T1 Nidhi's, Phase 2) with
the real Argon2id KDF and AES-256-CTR cipher on the fast ``demo`` profile.
"""

from __future__ import annotations

import base64
import copy
import json
import secrets
import string
from collections import Counter
from datetime import datetime
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.cipher import AESCTRCipher
from honeycore.interfaces import (
    CTR_NONCE_LEN,
    ENTRY_SEED_LEN,
    KDF_PROFILES,
    MAX_FIELD_LEN,
    PRINTABLE_MAX,
    PRINTABLE_MIN,
    SALT_LEN,
    Entry,
    EntryNotFoundError,
    HoneyVaultAPI,
    InvalidInputError,
    KDFParams,
)
from honeycore.kdf import Argon2KDF, derive_subkeys
from honeycore.sigil import compute_sigil
from honeycore.stubs import StubCipher, StubEntryDTE, StubKDF
from honeycore.vault import (
    DTE_KEYS,
    ENTRY_KEYS,
    KDF_KEYS,
    MAX_SERVICE_LEN,
    SCHEME,
    TOP_KEYS,
    HoneyVault,
    VaultFormatError,
)

MASTER = "Tr0ub4dor&3-master"
ENTRY_DTE = StubEntryDTE()
Vault = HoneyVault.bind(ENTRY_DTE)

ENTRIES = [
    Entry("github.com", "alice@gmail.com", "monkey123!"),
    Entry("mail.google.com", "alice", "P@ssw0rd"),
    Entry("bank.example", "alice_1990", "correct horse battery"),
    Entry("reddit.com", "throwaway42", "hunter2"),
    Entry("x" * MAX_SERVICE_LEN, "a", "b"),
]


def _printable_field(value: str) -> bool:
    return 1 <= len(value) <= MAX_FIELD_LEN and all(
        PRINTABLE_MIN <= ord(c) <= PRINTABLE_MAX for c in value
    )


def _wrong_password(i: int) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation + " "
    n = 1 + secrets.randbelow(40)
    pw = "".join(secrets.choice(alphabet) for _ in range(n))
    return pw if pw != MASTER else pw + str(i)


@pytest.fixture(scope="module")
def filled() -> tuple[HoneyVault, list[str]]:
    vault = Vault.new("demo")
    ids = [vault.add_entry(MASTER, e) for e in ENTRIES]
    return vault, ids


@pytest.fixture
def vault(filled: tuple[HoneyVault, list[str]]) -> HoneyVault:
    """A fresh mutable copy of the module-level filled vault."""
    return Vault.from_dict(filled[0].to_dict())


@pytest.fixture(scope="module")
def wrong_unlocks(filled: tuple[HoneyVault, list[str]]) -> list[Any]:
    vault, _ = filled
    return [vault.unlock(_wrong_password(i)) for i in range(300)]


# --- construction / DI -------------------------------------------------------------------


def test_satisfies_protocol() -> None:
    assert isinstance(Vault.new("demo"), HoneyVaultAPI)


def test_new_vault_is_empty_with_profile_and_salt() -> None:
    v = Vault.new("demo")
    assert v.entry_count() == 0
    assert v.kdf_profile == "demo"
    assert v.kdf_params == KDF_PROFILES["demo"]
    assert len(v.salt) == SALT_LEN
    assert Vault.new("demo").salt != v.salt


def test_new_unknown_profile_raises() -> None:
    with pytest.raises(InvalidInputError):
        Vault.new("turbo")


def test_bind_returns_subclass_without_mutating_base() -> None:
    assert issubclass(Vault, HoneyVault) and Vault is not HoneyVault
    assert Vault._entry_dte is ENTRY_DTE
    assert isinstance(Vault._kdf, Argon2KDF)
    assert isinstance(Vault._cipher, AESCTRCipher)
    assert HoneyVault._entry_dte is None


def test_bind_injects_kdf_and_cipher() -> None:
    stub_vault_cls = HoneyVault.bind(ENTRY_DTE, kdf=StubKDF(), cipher=StubCipher())
    v = stub_vault_cls.new("demo")
    entry_id = v.add_entry(MASTER, ENTRIES[0])
    got = v.unlock(MASTER).entries[0]
    assert (got.id, got.username, got.password) == (entry_id, "alice@gmail.com", "monkey123!")
    # different primitives -> a real-crypto vault reads the same blob as a decoy
    decoy = Vault.from_dict(v.to_dict()).unlock(MASTER).entries[0]
    assert (decoy.username, decoy.password) != ("alice@gmail.com", "monkey123!")


def test_bind_rejects_wrong_seed_len() -> None:
    class BadDTE(StubEntryDTE):
        seed_len = ENTRY_SEED_LEN - 4

    with pytest.raises(ValueError):
        HoneyVault.bind(BadDTE())


# --- right password ----------------------------------------------------------------------


def test_right_password_returns_exact_entries(filled: tuple[HoneyVault, list[str]]) -> None:
    vault, ids = filled
    result = vault.unlock(MASTER)
    assert [e.id for e in result.entries] == ids
    assert [(e.service, e.username, e.password) for e in result.entries] == [
        (e.service, e.username, e.password) for e in ENTRIES
    ]


def test_unlock_empty_vault() -> None:
    result = Vault.new("demo").unlock(MASTER)
    assert result.entries == []
    assert len(result.sigil.emojis) == 3


def test_unlock_derives_key_once(vault: HoneyVault) -> None:
    calls = 0

    class CountingKDF(Argon2KDF):
        def derive(self, password: str, salt: bytes, params: KDFParams) -> bytes:
            nonlocal calls
            calls += 1
            return super().derive(password, salt, params)

    counted = HoneyVault.bind(ENTRY_DTE, kdf=CountingKDF()).from_dict(vault.to_dict())
    counted.unlock(MASTER)
    assert calls == 1


def test_timestamps_are_iso8601_utc(filled: tuple[HoneyVault, list[str]]) -> None:
    for e in filled[0].unlock(MASTER).entries:
        for ts in (e.created_at, e.updated_at):
            assert datetime.fromisoformat(ts).utcoffset().total_seconds() == 0


# --- wrong passwords ---------------------------------------------------------------------


def test_wrong_passwords_never_raise_and_keep_shape(
    filled: tuple[HoneyVault, list[str]], wrong_unlocks: list[Any]
) -> None:
    vault, ids = filled
    services = [e.service for e in ENTRIES]
    assert len(wrong_unlocks) == 300
    for result in wrong_unlocks:
        assert len(result.entries) == vault.entry_count() == len(ENTRIES)
        assert [e.id for e in result.entries] == ids
        assert [e.service for e in result.entries] == services
        for e in result.entries:
            assert _printable_field(e.username)
            assert _printable_field(e.password)


def test_wrong_passwords_do_not_reveal_real_credentials(wrong_unlocks: list[Any]) -> None:
    real = {(e.username, e.password) for e in ENTRIES}
    for result in wrong_unlocks:
        assert not real & {(e.username, e.password) for e in result.entries}


@pytest.mark.parametrize(
    "password",
    ["", " ", MASTER + " ", MASTER.upper(), "пароль", "🍯" * 50, "x" * 10_000, "\ud800lone"],
)
def test_edge_case_passwords_never_raise(
    filled: tuple[HoneyVault, list[str]], password: str
) -> None:
    result = filled[0].unlock(password)
    assert len(result.entries) == len(ENTRIES)
    for e in result.entries:
        assert _printable_field(e.username) and _printable_field(e.password)


def _small_blob() -> dict:
    v = Vault.new("demo")
    v.add_entry(MASTER, ENTRIES[0])
    return v.to_dict()


_SMALL_BLOB = _small_blob()


@settings(max_examples=40, deadline=None)
@given(st.text(max_size=64))
def test_any_text_password_never_raises(password: str) -> None:
    vault = Vault.from_dict(_SMALL_BLOB)
    result = vault.unlock(password)
    assert len(result.entries) == 1
    assert _printable_field(result.entries[0].password)


# --- sigil -------------------------------------------------------------------------------


def test_sigil_stable_for_right_password(filled: tuple[HoneyVault, list[str]]) -> None:
    vault, _ = filled
    first = vault.unlock(MASTER).sigil
    assert vault.unlock(MASTER).sigil == first
    assert Vault.from_dict(vault.to_dict()).unlock(MASTER).sigil == first


def test_sigil_matches_key_schedule(filled: tuple[HoneyVault, list[str]]) -> None:
    vault, _ = filled
    k = Argon2KDF().derive(MASTER, vault.salt, vault.kdf_params)
    assert vault.unlock(MASTER).sigil == compute_sigil(derive_subkeys(k)[1])


def test_sigil_differs_for_wrong_passwords(
    filled: tuple[HoneyVault, list[str]], wrong_unlocks: list[Any]
) -> None:
    right = filled[0].unlock(MASTER).sigil
    sigils = [r.sigil for r in wrong_unlocks]
    # P(collision) per wrong password is 1 / (64^3 * 16) ≈ 2.4e-7.
    assert sum(s == right for s in sigils) <= 1
    assert len(set(sigils)) >= 290
    # emojis and colours are spread out, not stuck on a few values
    assert len(Counter(s.color for s in sigils)) >= 12
    assert len(Counter(e for s in sigils for e in s.emojis)) >= 55


# --- add / update / delete / export ------------------------------------------------------


def test_add_does_not_touch_other_entries(vault: HoneyVault) -> None:
    before = copy.deepcopy(vault.to_dict()["entries"])
    vault.add_entry(MASTER, Entry("new.example", "bob", "s3cret"))
    after = vault.to_dict()["entries"]
    assert after[: len(before)] == before
    assert len(after) == len(before) + 1


def test_update_reencrypts_only_target(vault: HoneyVault) -> None:
    before = {e["id"]: e for e in copy.deepcopy(vault.to_dict()["entries"])}
    target = next(iter(before))
    vault.update_entry(MASTER, target, Entry("gitlab.com", "alice2", "n3w-pass"))
    after = {e["id"]: e for e in vault.to_dict()["entries"]}
    assert list(after) == list(before)
    for entry_id, e in after.items():
        if entry_id == target:
            assert e["nonce"] != before[target]["nonce"]
            assert e["ciphertext"] != before[target]["ciphertext"]
            assert e["service"] == "gitlab.com"
            assert e["created_at"] == before[target]["created_at"]
            assert e["updated_at"] >= before[target]["updated_at"]
        else:
            assert e == before[entry_id]
    got = {e.id: e for e in vault.unlock(MASTER).entries}[target]
    assert (got.service, got.username, got.password) == ("gitlab.com", "alice2", "n3w-pass")


def test_typo_on_update_damages_only_that_entry(vault: HoneyVault) -> None:
    target = vault.unlock(MASTER).entries[1].id
    vault.update_entry(MASTER + "x", target, Entry("mail.google.com", "alice", "changed"))
    entries = vault.unlock(MASTER).entries
    for i, e in enumerate(entries):
        if e.id == target:
            assert (e.username, e.password) != ("alice", "changed")
        else:
            assert (e.username, e.password) == (ENTRIES[i].username, ENTRIES[i].password)


def test_delete(vault: HoneyVault) -> None:
    ids = [e.id for e in vault.unlock(MASTER).entries]
    vault.delete_entry(ids[2])
    assert vault.entry_count() == len(ENTRIES) - 1
    assert [e.id for e in vault.unlock(MASTER).entries] == ids[:2] + ids[3:]


def test_export_entry_seed(vault: HoneyVault) -> None:
    entry_id = vault.unlock(MASTER).entries[0].id
    seed = vault.export_entry_seed(MASTER, entry_id)
    assert len(seed) == ENTRY_SEED_LEN
    assert ENTRY_DTE.decode(seed) == ("alice@gmail.com", "monkey123!")
    wrong = vault.export_entry_seed("not the master", entry_id)
    assert len(wrong) == ENTRY_SEED_LEN and wrong != seed


@pytest.mark.parametrize("op", ["update", "delete", "export"])
def test_unknown_id_raises_entry_not_found(vault: HoneyVault, op: str) -> None:
    with pytest.raises(EntryNotFoundError) as excinfo:
        if op == "update":
            vault.update_entry(MASTER, "nope", ENTRIES[0])
        elif op == "delete":
            vault.delete_entry("nope")
        else:
            vault.export_entry_seed(MASTER, "nope")
    assert isinstance(excinfo.value, KeyError)


@pytest.mark.parametrize(
    "entry",
    [
        Entry("", "alice", "pw"),
        Entry("   ", "alice", "pw"),
        Entry("x" * (MAX_SERVICE_LEN + 1), "alice", "pw"),
        Entry("evil\nservice", "alice", "pw"),
        Entry("ok.com", "", "pw"),
        Entry("ok.com", "a" * (MAX_FIELD_LEN + 1), "pw"),
        Entry("ok.com", "alice", "p\tw"),
        Entry("ok.com", "alice", "pässword"),
        Entry("ok.com", "alice", ""),
    ],
)
def test_invalid_entry_raises_and_leaves_vault_unchanged(vault: HoneyVault, entry: Entry) -> None:
    before = vault.to_dict()
    target = before["entries"][0]["id"]
    with pytest.raises(InvalidInputError):
        vault.add_entry(MASTER, entry)
    with pytest.raises(InvalidInputError):
        vault.update_entry(MASTER, target, entry)
    assert vault.to_dict() == before


def test_invalid_input_error_does_not_echo_secret(vault: HoneyVault) -> None:
    with pytest.raises(InvalidInputError) as excinfo:
        vault.add_entry(MASTER, Entry("ok.com", "alice", "s3cret-pw-" + "x" * 40))
    assert "s3cret" not in str(excinfo.value)
    assert MASTER not in str(excinfo.value)


# --- blob v1 -----------------------------------------------------------------------------


def test_blob_keys_are_exactly_v1(filled: tuple[HoneyVault, list[str]]) -> None:
    blob = filled[0].to_dict()
    assert set(blob) == TOP_KEYS == {"format", "version", "scheme", "kdf", "dte", "entries"}
    assert (
        set(blob["kdf"])
        == KDF_KEYS
        == {
            "alg",
            "profile",
            "salt",
            "time_cost",
            "memory_cost_kib",
            "parallelism",
            "hash_len",
        }
    )
    assert set(blob["dte"]) == DTE_KEYS == {"password_model", "username_model", "entry_seed_len"}
    for e in blob["entries"]:
        assert (
            set(e)
            == ENTRY_KEYS
            == {
                "id",
                "service",
                "nonce",
                "ciphertext",
                "created_at",
                "updated_at",
            }
        )


def test_blob_values(filled: tuple[HoneyVault, list[str]]) -> None:
    blob = filled[0].to_dict()
    demo = KDF_PROFILES["demo"]
    assert blob["format"] == "honeyvault"
    assert blob["version"] == 1
    assert blob["scheme"] == SCHEME == "HE-PCFG-v1/AES-256-CTR/argon2id"
    assert blob["kdf"] == {
        "alg": "argon2id",
        "profile": "demo",
        "salt": blob["kdf"]["salt"],
        "time_cost": demo.time_cost,
        "memory_cost_kib": demo.memory_cost_kib,
        "parallelism": demo.parallelism,
        "hash_len": demo.hash_len,
    }
    assert len(base64.b64decode(blob["kdf"]["salt"], validate=True)) == SALT_LEN
    assert blob["dte"] == {
        "password_model": "pcfg-password-v1",
        "username_model": "pcfg-username-v1",
        "entry_seed_len": ENTRY_SEED_LEN,
    }


def test_every_ciphertext_is_entry_seed_len(filled: tuple[HoneyVault, list[str]]) -> None:
    entries = filled[0].to_dict()["entries"]
    for e in entries:
        assert len(base64.b64decode(e["ciphertext"], validate=True)) == ENTRY_SEED_LEN
        assert len(base64.b64decode(e["nonce"], validate=True)) == CTR_NONCE_LEN
    assert len({e["nonce"] for e in entries}) == len(entries)


def test_ciphertext_length_independent_of_content() -> None:
    v = Vault.new("demo")
    v.add_entry(MASTER, Entry("a.com", "a", "b"))
    v.add_entry(MASTER, Entry("b.com", "u" * MAX_FIELD_LEN, "p" * MAX_FIELD_LEN))
    lengths = {len(e["ciphertext"]) for e in v.to_dict()["entries"]}
    assert len(lengths) == 1


def test_blob_contains_no_key_material(filled: tuple[HoneyVault, list[str]]) -> None:
    vault, _ = filled
    text = json.dumps(vault.to_dict())
    k = Argon2KDF().derive(MASTER, vault.salt, vault.kdf_params)
    for secret in (k, *derive_subkeys(k)):
        assert base64.b64encode(secret).decode() not in text
        assert secret.hex() not in text
    assert MASTER not in text


def test_model_ids_from_entry_dte() -> None:
    class NamedDTE(StubEntryDTE):
        model_ids = {"password_model": "stub-pw-v9", "username_model": "stub-user-v9"}

    v = HoneyVault.bind(NamedDTE()).new("demo")
    assert v.to_dict()["dte"] == {
        "password_model": "stub-pw-v9",
        "username_model": "stub-user-v9",
        "entry_seed_len": ENTRY_SEED_LEN,
    }


def test_round_trip(filled: tuple[HoneyVault, list[str]]) -> None:
    vault, _ = filled
    blob = json.loads(json.dumps(vault.to_dict()))
    loaded = Vault.from_dict(blob)
    assert loaded.to_dict() == vault.to_dict()
    assert loaded.unlock(MASTER) == vault.unlock(MASTER)
    wrong = "definitely wrong"
    assert loaded.unlock(wrong) == vault.unlock(wrong)


def _mutations() -> list[tuple[str, Any]]:
    def drop(path: tuple[Any, ...]) -> Any:
        def f(b: dict) -> None:
            obj = b
            for p in path[:-1]:
                obj = obj[p]
            del obj[path[-1]]

        return f

    def put(path: tuple[Any, ...], value: Any) -> Any:
        def f(b: dict) -> None:
            obj = b
            for p in path[:-1]:
                obj = obj[p]
            obj[path[-1]] = value

        return f

    short_ct = base64.b64encode(b"\x00" * (ENTRY_SEED_LEN - 1)).decode()
    return [
        ("missing scheme", drop(("scheme",))),
        ("extra top key", put(("mac",), "deadbeef")),
        ("wrong format", put(("format",), "nocrack")),
        ("version 2", put(("version",), 2)),
        ("version bool", put(("version",), True)),
        ("other scheme", put(("scheme",), "HE-STUB-v1/SHA256-CTR/sha256")),
        ("stub kdf alg", put(("kdf", "alg"), "stub-sha256")),
        ("missing salt", drop(("kdf", "salt"))),
        ("bad salt b64", put(("kdf", "salt"), "!!not-base64!!")),
        ("short salt", put(("kdf", "salt"), base64.b64encode(b"\x00" * 8).decode())),
        ("time_cost str", put(("kdf", "time_cost"), "3")),
        ("time_cost 0", put(("kdf", "time_cost"), 0)),
        ("huge memory", put(("kdf", "memory_cost_kib"), 2**40)),
        ("hash_len 4", put(("kdf", "hash_len"), 4)),
        ("empty profile", put(("kdf", "profile"), "")),
        ("seed len", put(("dte", "entry_seed_len"), 528)),
        ("model id type", put(("dte", "password_model"), 1)),
        ("entries not list", put(("entries",), {})),
        ("entry extra key", put(("entries", 0, "tag"), "x")),
        ("entry missing nonce", drop(("entries", 0, "nonce"))),
        ("short nonce", put(("entries", 0, "nonce"), base64.b64encode(b"\x00" * 12).decode())),
        ("short ciphertext", put(("entries", 0, "ciphertext"), short_ct)),
        ("ciphertext not str", put(("entries", 0, "ciphertext"), 123)),
        ("empty service", put(("entries", 0, "service"), "")),
        ("bad timestamp", put(("entries", 0, "created_at"), "yesterday")),
        ("naive timestamp", put(("entries", 0, "updated_at"), "2026-10-04T12:00:00")),
        ("empty id", put(("entries", 0, "id"), "")),
    ]


@pytest.mark.parametrize(("name", "mutate"), _mutations(), ids=[m[0] for m in _mutations()])
def test_from_dict_rejects_malformed(
    filled: tuple[HoneyVault, list[str]], name: str, mutate: Any
) -> None:
    blob = copy.deepcopy(filled[0].to_dict())
    mutate(blob)
    with pytest.raises(ValueError) as excinfo:
        Vault.from_dict(blob)
    assert isinstance(excinfo.value, VaultFormatError)
    assert isinstance(excinfo.value, InvalidInputError)


def test_from_dict_rejects_duplicate_ids(filled: tuple[HoneyVault, list[str]]) -> None:
    blob = copy.deepcopy(filled[0].to_dict())
    blob["entries"].append(copy.deepcopy(blob["entries"][0]))
    with pytest.raises(ValueError):
        Vault.from_dict(blob)


@pytest.mark.parametrize("blob", [None, [], "honeyvault", 42])
def test_from_dict_rejects_non_dict(blob: Any) -> None:
    with pytest.raises(ValueError):
        Vault.from_dict(blob)
