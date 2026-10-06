"""Tests for ``load_honeycore("real")`` wiring (honeycore/factory.py). Owner: T1 — Nidhi."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from honeycore import factory, sigil, stubs
from honeycore.baseline import ConventionalVault
from honeycore.dte import password_dte, username_dte
from honeycore.dte.entry_dte import PCFGEntryDTE
from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.factory import HoneyCore, load_honeycore
from honeycore.interfaces import (
    ENTRY_SEED_LEN,
    PKIAPI,
    ConventionalVaultAPI,
    Entry,
    EntryDTE,
    HoneyVaultAPI,
    PasswordModel,
    SharingAPI,
)
from honeycore.pki import PKI
from honeycore.sharing import Sharing
from honeycore.vault import SCHEME, HoneyVault

needs_models = pytest.mark.skipif(
    not (password_dte.DEFAULT_MODEL_PATH.exists() and username_dte.DEFAULT_MODEL_PATH.exists()),
    reason="default PCFG models not trained yet (scripts/train_pcfg.py)",
)


@pytest.fixture(scope="module")
def real() -> HoneyCore:
    return load_honeycore("real")


@needs_models
def test_real_bundle_is_complete(real: HoneyCore) -> None:
    assert issubclass(real.vault_cls, HoneyVault)
    assert real.vault_cls is not HoneyVault  # bound subclass, base left untouched
    assert real.conventional_vault_cls is ConventionalVault
    assert isinstance(real.entry_dte, PCFGEntryDTE)
    assert isinstance(real.password_model, PCFGPasswordModel)
    assert isinstance(real.sharing, Sharing)
    assert isinstance(real.pki, PKI)

    assert isinstance(real.vault_cls.new("demo"), HoneyVaultAPI)
    assert isinstance(real.conventional_vault_cls.new("pw", "demo"), ConventionalVaultAPI)
    assert isinstance(real.entry_dte, EntryDTE)
    assert isinstance(real.password_model, PasswordModel)
    assert isinstance(real.sharing, SharingAPI)
    assert isinstance(real.pki, PKIAPI)


@needs_models
def test_real_bundle_is_cached_and_models_loaded_once(real: HoneyCore) -> None:
    assert load_honeycore("real") is real
    assert real.entry_dte is PCFGEntryDTE.load_default()
    assert real.password_model is real.entry_dte.password_model
    assert real.vault_cls._dte() is real.entry_dte


@needs_models
def test_real_vault_uses_pcfg_entry_dte(real: HoneyCore) -> None:
    vault = real.vault_cls.new("demo")
    entry_id = vault.add_entry("master-pw", Entry("example.com", "alice", "hunter2!"))
    blob = vault.to_dict()
    assert blob["scheme"] == SCHEME
    assert blob["dte"] == {
        "password_model": "pcfg-password-v1",
        "username_model": "pcfg-username-v1",
        "entry_seed_len": ENTRY_SEED_LEN,
    }
    [entry] = real.vault_cls.from_dict(blob).unlock("master-pw").entries
    assert (entry.id, entry.username, entry.password) == (entry_id, "alice", "hunter2!")


@needs_models
def test_real_password_model_serves_honeywords(real: HoneyCore) -> None:
    decoy = real.password_model.sample_like("monkey12!")
    assert decoy != "monkey12!"
    assert len(decoy) == len("monkey12!")


def test_stub_and_real_sigils_share_tables() -> None:
    assert stubs.EMOJI64 is sigil.EMOJI64
    assert stubs.PALETTE16 is sigil.PALETTE16


@pytest.fixture
def no_real_cache() -> Iterator[None]:
    """Run with an empty bundle cache; the next ``load_honeycore("real")`` rebuilds it."""
    factory._load_real.cache_clear()
    yield
    factory._load_real.cache_clear()


@pytest.mark.parametrize(
    ("module", "kind"), [(password_dte, "password"), (username_dte, "username")]
)
def test_missing_model_raises_runtime_error_with_train_command(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    no_real_cache: None,
    module: object,
    kind: str,
) -> None:
    missing = tmp_path / f"pcfg_{kind}_v1.json.gz"
    monkeypatch.setattr(module, "DEFAULT_MODEL_PATH", missing)
    with pytest.raises(RuntimeError) as info:
        load_honeycore("real")
    message = str(info.value)
    assert str(missing) in message
    assert f"python scripts/train_pcfg.py --kind {kind}" in message
    assert not isinstance(info.value, FileNotFoundError)


@pytest.mark.parametrize(
    ("module", "owner"),
    [("honeycore.sharing", "T4 Parth"), ("honeycore.dte.entry_dte", "T1 Nidhi")],
)
def test_missing_module_reports_owner(
    monkeypatch: pytest.MonkeyPatch, no_real_cache: None, module: str, owner: str
) -> None:
    monkeypatch.setitem(sys.modules, module, None)  # makes ``import module`` fail
    with pytest.raises(NotImplementedError, match=f"{module} not implemented yet — owner: {owner}"):
        load_honeycore("real")


def test_unknown_impl_rejected() -> None:
    with pytest.raises(ValueError, match="HONEYCORE_IMPL"):
        load_honeycore("fake")  # type: ignore[arg-type]
