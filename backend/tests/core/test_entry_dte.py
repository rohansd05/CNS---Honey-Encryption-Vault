"""Tests for ``honeycore.dte.entry_dte`` (PROJECT-BRIEF.md §7.5). Owner: T1 — Nidhi.

Uses the packaged PCFG models (skipped if not trained yet) and the real ``HoneyVault`` with
Argon2id on the fast ``demo`` profile. Credentials below are made up, never corpus lines.
"""

from __future__ import annotations

import secrets

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.dte.entry_dte import PASSWORD_SEED_LEN, USERNAME_SEED_LEN, PCFGEntryDTE
from honeycore.dte.password_dte import DEFAULT_MODEL_PATH as PASSWORD_MODEL_PATH
from honeycore.dte.pcfg import is_valid_field, template
from honeycore.dte.username_dte import DEFAULT_MODEL_PATH as USERNAME_MODEL_PATH
from honeycore.interfaces import (
    ENTRY_SEED_LEN,
    MAX_FIELD_LEN,
    Entry,
    EntryDTE,
    InvalidInputError,
    UnlockResult,
)
from honeycore.vault import DTE_KEYS, HoneyVault

pytestmark = pytest.mark.skipif(
    not (PASSWORD_MODEL_PATH.exists() and USERNAME_MODEL_PATH.exists()),
    reason="default PCFG models not trained yet (scripts/train_pcfg.py)",
)

printable = st.characters(min_codepoint=0x20, max_codepoint=0x7E)
printable_text = st.text(alphabet=printable, min_size=1, max_size=MAX_FIELD_LEN)

MASTER = "correct horse battery staple"
ENTRIES = [
    Entry("github.com", "octo_dev", "Tr0ub4dor&3"),
    Entry("gmail.com", "jane.doe@gmail.com", "sunshine2024!"),
    Entry("bank.example", "jdoe1987", "N0t-a-real-pw"),
    Entry("netflix.com", "movie_fan", "letmein99"),
    Entry("ssh", "root", "x" * MAX_FIELD_LEN),
]
WRONG_PASSWORD_COUNT = 200


@pytest.fixture(scope="module")
def dte() -> PCFGEntryDTE:
    return PCFGEntryDTE.load_default()


@pytest.fixture(scope="module")
def vault_cls(dte: PCFGEntryDTE) -> type[HoneyVault]:
    return HoneyVault.bind(dte)


@pytest.fixture(scope="module")
def filled(vault_cls: type[HoneyVault]) -> tuple[HoneyVault, list[str]]:
    vault = vault_cls.new("demo")
    ids = [vault.add_entry(MASTER, e) for e in ENTRIES]
    return vault, ids


@pytest.fixture(scope="module")
def wrong_unlocks(
    vault_cls: type[HoneyVault], filled: tuple[HoneyVault, list[str]]
) -> list[UnlockResult]:
    stolen = vault_cls.from_dict(filled[0].to_dict())  # what an attacker works on
    return [stolen.unlock(f"guess-{i}-{secrets.token_hex(4)}") for i in range(WRONG_PASSWORD_COUNT)]


def _valid(value: object) -> bool:
    return isinstance(value, str) and is_valid_field(value)


# ---- contract -------------------------------------------------------------------------------


def test_protocol_and_seed_layout(dte: PCFGEntryDTE) -> None:
    assert isinstance(dte, EntryDTE)
    assert dte.seed_len == ENTRY_SEED_LEN == 532
    assert (USERNAME_SEED_LEN, PASSWORD_SEED_LEN) == (268, 264)
    assert dte.username_model.seed_len == USERNAME_SEED_LEN
    assert dte.password_model.seed_len == PASSWORD_SEED_LEN


def test_model_ids_match_vault_dte_block(dte: PCFGEntryDTE) -> None:
    assert set(dte.model_ids) == DTE_KEYS - {"entry_seed_len"}
    assert dict(dte.model_ids) == {
        "password_model": "pcfg-password-v1",
        "username_model": "pcfg-username-v1",
    }
    with pytest.raises(TypeError):
        dte.model_ids["username_model"] = "other-model"  # type: ignore[index]


def test_load_default_is_cached_and_shares_models(dte: PCFGEntryDTE) -> None:
    assert PCFGEntryDTE.load_default() is dte
    fresh = PCFGEntryDTE()
    assert fresh.username_model is dte.username_model
    assert fresh.password_model is dte.password_model


def test_composes_explicit_models(dte: PCFGEntryDTE) -> None:
    custom = PCFGEntryDTE(dte.username_model, dte.password_model)
    assert custom.decode(custom.encode("amy", "pw1")) == ("amy", "pw1")


def test_rejects_models_with_wrong_seed_len(dte: PCFGEntryDTE) -> None:
    with pytest.raises(ValueError, match="username model seed_len"):
        PCFGEntryDTE(dte.password_model, dte.password_model)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="password model seed_len"):
        PCFGEntryDTE(dte.username_model, dte.username_model)  # type: ignore[arg-type]


# ---- encode / decode ------------------------------------------------------------------------


@settings(max_examples=300, deadline=None)
@given(username=printable_text, password=printable_text)
def test_roundtrip_any_printable_pair(dte: PCFGEntryDTE, username: str, password: str) -> None:
    seed = dte.encode(username, password)
    assert len(seed) == ENTRY_SEED_LEN
    assert dte.decode(seed) == (username, password)


@pytest.mark.parametrize("entry", ENTRIES, ids=lambda e: e.service)
def test_roundtrip_examples(dte: PCFGEntryDTE, entry: Entry) -> None:
    assert dte.decode(dte.encode(entry.username, entry.password)) == (
        entry.username,
        entry.password,
    )


def test_seed_is_username_seed_then_password_seed(dte: PCFGEntryDTE) -> None:
    seed = dte.encode("jane.doe@gmail.com", "sunshine2024!")
    assert dte.username_model.decode(seed[:USERNAME_SEED_LEN]) == "jane.doe@gmail.com"
    assert dte.password_model.decode(seed[USERNAME_SEED_LEN:]) == "sunshine2024!"


def test_encode_is_randomised_and_fixed_length(dte: PCFGEntryDTE) -> None:
    seeds = {dte.encode("a", "b") for _ in range(20)} | {dte.encode("u" * 32, "p" * 32)}
    assert len(seeds) == 21
    assert {len(s) for s in seeds} == {ENTRY_SEED_LEN}


@pytest.mark.parametrize(
    ("username", "password", "field"),
    [
        ("", "pw", "username"),
        ("u" * (MAX_FIELD_LEN + 1), "pw", "username"),
        ("café", "pw", "username"),
        ("user", "", "password"),
        ("user", "p" * (MAX_FIELD_LEN + 1), "password"),
        ("user", "tab\there", "password"),
    ],
)
def test_encode_rejects_invalid_fields(
    dte: PCFGEntryDTE, username: str, password: str, field: str
) -> None:
    with pytest.raises(InvalidInputError, match=field) as info:
        dte.encode(username, password)
    for secret in (username, password):
        if len(secret) > 3:
            assert secret not in str(info.value)


def test_decode_is_total_on_random_seeds(dte: PCFGEntryDTE) -> None:
    for _ in range(3000):
        username, password = dte.decode(secrets.token_bytes(ENTRY_SEED_LEN))
        assert _valid(username)
        assert _valid(password)


@pytest.mark.parametrize("fill", [b"\x00", b"\xff", b"\x7f", b"\x80"])
def test_decode_is_total_on_constant_seeds(dte: PCFGEntryDTE, fill: bytes) -> None:
    username, password = dte.decode(fill * ENTRY_SEED_LEN)
    assert _valid(username)
    assert _valid(password)


@settings(max_examples=300, deadline=None)
@given(st.binary(min_size=ENTRY_SEED_LEN, max_size=ENTRY_SEED_LEN))
def test_decode_is_total_hypothesis(dte: PCFGEntryDTE, seed: bytes) -> None:
    username, password = dte.decode(seed)
    assert _valid(username)
    assert _valid(password)


@pytest.mark.parametrize("n", [0, 1, ENTRY_SEED_LEN - 1, ENTRY_SEED_LEN + 1, 2 * ENTRY_SEED_LEN])
def test_decode_rejects_wrong_length(dte: PCFGEntryDTE, n: int) -> None:
    with pytest.raises(ValueError, match=str(ENTRY_SEED_LEN)):
        dte.decode(bytes(n))


def test_sample_is_valid_and_varied(dte: PCFGEntryDTE) -> None:
    samples = [dte.sample() for _ in range(200)]
    assert all(_valid(u) and _valid(p) for u, p in samples)
    assert len(set(samples)) > 150


# ---- real HoneyVault (demo KDF profile) ------------------------------------------------------


def test_vault_blob_carries_model_ids(filled: tuple[HoneyVault, list[str]]) -> None:
    blob = filled[0].to_dict()
    assert blob["dte"] == {
        "password_model": "pcfg-password-v1",
        "username_model": "pcfg-username-v1",
        "entry_seed_len": ENTRY_SEED_LEN,
    }


def test_vault_right_password_returns_exact_entries(
    vault_cls: type[HoneyVault], filled: tuple[HoneyVault, list[str]]
) -> None:
    vault, ids = filled
    result = vault_cls.from_dict(vault.to_dict()).unlock(MASTER)
    assert [e.id for e in result.entries] == ids
    assert [Entry(e.service, e.username, e.password) for e in result.entries] == ENTRIES


def test_vault_wrong_passwords_never_raise_and_decode_validly(
    wrong_unlocks: list[UnlockResult], filled: tuple[HoneyVault, list[str]]
) -> None:
    _, ids = filled
    assert len(wrong_unlocks) == WRONG_PASSWORD_COUNT
    for result in wrong_unlocks:
        assert [e.id for e in result.entries] == ids
        assert [e.service for e in result.entries] == [e.service for e in ENTRIES]
        for e in result.entries:
            assert _valid(e.username)
            assert _valid(e.password)


def test_vault_wrong_passwords_do_not_reveal_real_credentials(
    wrong_unlocks: list[UnlockResult],
) -> None:
    real = {(e.username, e.password) for e in ENTRIES}
    for result in wrong_unlocks:
        assert not real & {(e.username, e.password) for e in result.entries}


def test_vault_decoy_passwords_mostly_have_known_templates(
    dte: PCFGEntryDTE, wrong_unlocks: list[UnlockResult]
) -> None:
    decoys = [e.password for r in wrong_unlocks for e in r.entries]
    known = sum(dte.password_model._has_template(template(pw)) for pw in decoys)
    assert known / len(decoys) >= 0.80


def test_vault_decoys_are_diverse(wrong_unlocks: list[UnlockResult]) -> None:
    first = {(r.entries[0].username, r.entries[0].password) for r in wrong_unlocks}
    assert len(first) > WRONG_PASSWORD_COUNT // 2
