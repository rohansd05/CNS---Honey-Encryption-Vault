"""Invariant tests for ``honeycore.stubs`` and ``honeycore.factory``. Owner: T1 — Nidhi.

The same properties must hold for the real implementations (Phase 1/2).
"""

from __future__ import annotations

import json
import secrets
import string

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from honeycore.factory import HoneyCore, load_honeycore
from honeycore.interfaces import (
    ENTRY_SEED_LEN,
    MAX_FIELD_LEN,
    PASSWORD_SEED_INTS,
    PKIAPI,
    USERNAME_SEED_INTS,
    CertInfo,
    ConventionalVaultAPI,
    Entry,
    EntryDTE,
    EntryNotFoundError,
    FieldDTE,
    HoneyVaultAPI,
    InvalidInputError,
    InvalidSignatureError,
    PasswordModel,
    SharingAPI,
    WrongPasswordError,
)
from honeycore.stubs import (
    EMOJI64,
    PALETTE16,
    StubConventionalVault,
    StubEntryDTE,
    StubHoneyVault,
    StubPasswordModel,
    StubPKI,
    StubSharing,
    StubUsernameModel,
)

PRINTABLE = "".join(chr(c) for c in range(0x20, 0x7F))
fields = st.text(alphabet=PRINTABLE, min_size=1, max_size=MAX_FIELD_LEN)
MASTER = "correct horse battery staple"
SAMPLE_ENTRIES = [
    Entry("github.com", "alice@gmail.com", "monkey123!"),
    Entry("bank.example", "alice", "P@ssw0rd2024"),
    Entry("mail.example", "a" * MAX_FIELD_LEN, " ~" * (MAX_FIELD_LEN // 2)),
]


def _is_valid_field(value: str) -> bool:
    return 1 <= len(value) <= MAX_FIELD_LEN and all(c in PRINTABLE for c in value)


def _random_guess() -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(1 + secrets.randbelow(20)))


def _vault_with_entries() -> StubHoneyVault:
    vault = StubHoneyVault.new("demo")
    for entry in SAMPLE_ENTRIES:
        vault.add_entry(MASTER, entry)
    return vault


# ---- protocol conformance / factory ----
def test_stubs_satisfy_protocols() -> None:
    core = load_honeycore("stub")
    assert isinstance(core, HoneyCore)
    assert isinstance(core.entry_dte, EntryDTE)
    assert isinstance(core.password_model, PasswordModel)
    assert isinstance(StubUsernameModel(), FieldDTE)
    assert isinstance(core.sharing, SharingAPI)
    assert isinstance(core.pki, PKIAPI)
    assert isinstance(core.vault_cls.new(), HoneyVaultAPI)
    assert isinstance(core.conventional_vault_cls.new(MASTER, "demo"), ConventionalVaultAPI)


def test_real_impl_reports_owner() -> None:
    with pytest.raises(NotImplementedError, match="owner:"):
        load_honeycore("real")


def test_sigil_tables() -> None:
    assert len(EMOJI64) == len(set(EMOJI64)) == 64
    assert len(PALETTE16) == len(set(PALETTE16)) == 16


# ---- seed lengths ----
def test_seed_lengths() -> None:
    assert StubPasswordModel().seed_len == PASSWORD_SEED_INTS * 4 == 264
    assert StubUsernameModel().seed_len == USERNAME_SEED_INTS * 4 == 268
    dte = StubEntryDTE()
    assert dte.seed_len == ENTRY_SEED_LEN == 532
    assert len(dte.encode("u", "p")) == ENTRY_SEED_LEN
    assert len(dte.encode("u" * MAX_FIELD_LEN, "p" * MAX_FIELD_LEN)) == ENTRY_SEED_LEN


# ---- round-trip ----
@settings(max_examples=200)
@given(username=fields, password=fields)
def test_entry_dte_round_trip(username: str, password: str) -> None:
    dte = StubEntryDTE()
    assert dte.decode(dte.encode(username, password)) == (username, password)


@given(value=fields)
def test_field_round_trip(value: str) -> None:
    for model in (StubPasswordModel(), StubUsernameModel()):
        assert model.decode(model.encode(value)) == value


@pytest.mark.parametrize("bad", ["", "x" * (MAX_FIELD_LEN + 1), "tab\there", "naïve"])
def test_encode_rejects_invalid(bad: str) -> None:
    with pytest.raises(InvalidInputError):
        StubPasswordModel().encode(bad)


# ---- totality ----
def test_decode_total_on_random_seeds() -> None:
    pw, user, entry = StubPasswordModel(), StubUsernameModel(), StubEntryDTE()
    for _ in range(500):
        assert _is_valid_field(pw.decode(secrets.token_bytes(pw.seed_len)))
        assert _is_valid_field(user.decode(secrets.token_bytes(user.seed_len)))
        u, p = entry.decode(secrets.token_bytes(ENTRY_SEED_LEN))
        assert _is_valid_field(u) and _is_valid_field(p)


def test_sample_and_sample_like_are_valid() -> None:
    model = StubPasswordModel()
    for _ in range(100):
        assert _is_valid_field(model.sample())
    like = model.sample_like("monkey123")
    assert like[:6] == "monkey" and like[6:].isdigit() and len(like) == 9
    assert _is_valid_field(model.sample_like("z" * MAX_FIELD_LEN))
    assert model.probability("anything") == pytest.approx(1e-6)


# ---- honey vault ----
def test_unlock_correct_password_returns_real_entries() -> None:
    vault = _vault_with_entries()
    result = vault.unlock(MASTER)
    assert [(e.service, e.username, e.password) for e in result.entries] == [
        (e.service, e.username, e.password) for e in SAMPLE_ENTRIES
    ]
    assert result.sigil == vault.unlock(MASTER).sigil  # deterministic per key


def test_unlock_never_raises_on_wrong_passwords() -> None:
    vault = _vault_with_entries()
    real_sigil = vault.unlock(MASTER).sigil
    differing_sigils = 0
    for _ in range(200):
        result = vault.unlock(_random_guess())
        assert len(result.entries) == vault.entry_count() == len(SAMPLE_ENTRIES)
        for e in result.entries:
            assert _is_valid_field(e.username) and _is_valid_field(e.password)
        assert set(result.sigil.emojis) <= set(EMOJI64)
        assert result.sigil.color in PALETTE16
        differing_sigils += result.sigil != real_sigil
    assert differing_sigils > 150


def test_vault_blob_round_trip_and_shape() -> None:
    vault = _vault_with_entries()
    blob = json.loads(json.dumps(vault.to_dict()))
    assert set(blob) == {"format", "version", "scheme", "kdf", "dte", "entries"}
    assert blob["format"] == "honeyvault" and blob["version"] == 1
    assert blob["dte"]["entry_seed_len"] == ENTRY_SEED_LEN
    assert set(blob["entries"][0]) == {
        "id",
        "service",
        "nonce",
        "ciphertext",
        "created_at",
        "updated_at",
    }
    restored = StubHoneyVault.from_dict(blob)
    assert restored.to_dict() == vault.to_dict()
    assert restored.unlock(MASTER) == vault.unlock(MASTER)


def test_update_and_delete_touch_one_entry() -> None:
    vault = _vault_with_entries()
    before = vault.to_dict()["entries"]
    first_id, second_id = before[0]["id"], before[1]["id"]
    updated = Entry("github.com", "alice", "new-secret-1")
    vault.update_entry(MASTER, first_id, updated)
    after = vault.to_dict()["entries"]
    assert after[1] == before[1] and after[2] == before[2]
    assert vault.unlock(MASTER).entries[0].password == updated.password
    vault.delete_entry(second_id)
    assert vault.entry_count() == 2
    with pytest.raises(KeyError):
        vault.delete_entry(second_id)


def test_unknown_entry_id_raises_entry_not_found() -> None:
    vault = _vault_with_entries()
    assert issubclass(EntryNotFoundError, KeyError)
    with pytest.raises(EntryNotFoundError):
        vault.update_entry(MASTER, "no-such-id", SAMPLE_ENTRIES[0])
    with pytest.raises(EntryNotFoundError):
        vault.delete_entry("no-such-id")
    with pytest.raises(EntryNotFoundError):
        vault.export_entry_seed(MASTER, "no-such-id")
    assert vault.entry_count() == len(SAMPLE_ENTRIES)


def test_export_entry_seed_decodes_to_entry() -> None:
    vault = _vault_with_entries()
    entry_id = vault.to_dict()["entries"][0]["id"]
    seed = vault.export_entry_seed(MASTER, entry_id)
    assert len(seed) == ENTRY_SEED_LEN
    first = SAMPLE_ENTRIES[0]
    assert StubEntryDTE().decode(seed) == (first.username, first.password)


def test_from_dict_rejects_malformed_blob() -> None:
    with pytest.raises(InvalidInputError):
        StubHoneyVault.from_dict({"format": "nope"})


# ---- conventional vault ----
def test_conventional_vault_has_oracle() -> None:
    vault = StubConventionalVault.new(MASTER, "demo")
    vault.add_entry(MASTER, SAMPLE_ENTRIES[0])
    restored = StubConventionalVault.from_dict(json.loads(json.dumps(vault.to_dict())))
    assert [e.password for e in restored.unlock(MASTER)] == [SAMPLE_ENTRIES[0].password]
    with pytest.raises(WrongPasswordError):
        restored.unlock("not the master")


# ---- sharing ----
def test_sharing_round_trip_and_tamper() -> None:
    sharing = StubSharing()
    alice, bob = sharing.generate_identity(), sharing.generate_identity()
    seed = secrets.token_bytes(ENTRY_SEED_LEN)
    aad = {"sender": "alice", "recipient": "bob", "service": "github.com"}
    env = sharing.seal_share(seed, aad, bob.public_pem, alice.private_pem, b"CERT")
    assert set(env) == {
        "v",
        "alg",
        "eph_pub",
        "salt",
        "nonce",
        "ciphertext",
        "aad",
        "sender_cert",
        "signature",
    }
    assert sharing.open_share(env, bob.private_pem, []) == (seed, aad)
    with pytest.raises(InvalidSignatureError):
        sharing.open_share({**env, "signature": "forged"}, bob.private_pem, [])


# ---- PKI ----
def _stub_user_cert(pki: StubPKI, username: str = "alice", days: int = 365) -> bytes:
    keys = StubSharing().generate_identity()
    return pki.issue_user_certificate(
        username, keys.public_pem, pki.issuing_ca_pem(), pki.issuing_ca_key_pem(), days=days
    )


def test_pki_issue_verify_describe() -> None:
    pki = StubPKI()
    cert = _stub_user_cert(pki)
    assert cert.startswith(b"-----BEGIN CERTIFICATE-----")
    info = pki.verify_certificate(cert, [pki.root_ca_pem()], expected_cn="alice")
    assert isinstance(info, CertInfo)
    assert info.subject_cn == "alice" and info.issuer_cn == StubPKI.ISSUER_CN
    assert info == pki.describe(cert) == pki.describe(_stub_user_cert(pki))  # deterministic
    assert info.serial > 0 and len(info.fingerprint_sha256) == 64
    assert info.not_before < info.not_after
    assert pki.describe(_stub_user_cert(pki, days=30)).not_after < info.not_after
    assert pki.describe(pki.issuing_ca_pem()).issuer_cn == StubPKI.ROOT_CN


def test_pki_verify_rejects_cn_eku_and_garbage() -> None:
    pki = StubPKI()
    cert = _stub_user_cert(pki)
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(cert, [pki.root_ca_pem()], expected_cn="mallory")
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(cert, [pki.root_ca_pem()], require_client_auth=True)
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(pki.root_ca_pem(), [pki.root_ca_pem()])
    with pytest.raises(InvalidSignatureError):
        pki.verify_certificate(b"not a pem", [pki.root_ca_pem()])
    with pytest.raises(InvalidInputError):
        pki.describe(b"not a pem")
