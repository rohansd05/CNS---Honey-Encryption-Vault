"""Select the honeycore implementation (``HONEYCORE_IMPL=stub|real``).

Owner: T1 lead — Nidhi. Callers (the API, attack demo, eval) must obtain every honeycore object
through ``load_honeycore`` and never import ``stubs`` or real modules directly, so the
stub <-> real swap is a one-line env change.

``"real"`` builds the bundle once per process (the PCFG models are a few MB each):
``entry_dte = PCFGEntryDTE.load_default()``, ``vault_cls = HoneyVault.bind(entry_dte)``,
``password_model`` = the entry DTE's ``PCFGPasswordModel`` (the same loaded instance, used for
honeywords), the baseline ``ConventionalVault``, ``Sharing()`` and ``PKI()``.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from honeycore.interfaces import (
    PKIAPI,
    ConventionalVaultAPI,
    EntryDTE,
    HoneyVaultAPI,
    PasswordModel,
    SharingAPI,
)

# Example training input per model kind, for the missing-model error (paths from backend/).
_TRAIN_INPUTS: dict[str, str] = {
    "password": "../data/raw/rockyou-withcount.txt.bz2",
    "username": "../data/raw/xato-net-10-million-usernames.txt",
}


@dataclass(frozen=True)
class HoneyCore:
    """Bundle of honeycore implementations used by the rest of the backend."""

    vault_cls: type[HoneyVaultAPI]
    conventional_vault_cls: type[ConventionalVaultAPI]
    entry_dte: EntryDTE
    password_model: PasswordModel
    sharing: SharingAPI
    pki: PKIAPI


def _load_real_part(module: str, name: str, owner: str) -> Any:
    """Import ``honeycore.<module>.<name>``; ``NotImplementedError`` naming the owner if absent."""
    qualified = f"honeycore.{module}"
    try:
        obj = getattr(importlib.import_module(qualified), name)
    except (ImportError, AttributeError) as exc:
        raise NotImplementedError(f"{qualified} not implemented yet — owner: {owner}") from exc
    return obj


def _require_model_files() -> None:
    """Raise ``RuntimeError`` naming the first missing model file and its train command."""
    from honeycore.dte import password_dte, username_dte

    for kind, path in (
        ("password", password_dte.DEFAULT_MODEL_PATH),
        ("username", username_dte.DEFAULT_MODEL_PATH),
    ):
        if not path.is_file():
            raise RuntimeError(
                f"PCFG {kind} model file not found: {path}. Train it from backend/ with: "
                f"python scripts/train_pcfg.py --kind {kind} --input {_TRAIN_INPUTS[kind]} "
                f"--out honeycore/models/{path.name} "
                "(fetch corpora first with scripts/download_corpus.py)"
            )


@lru_cache(maxsize=1)
def _load_real() -> HoneyCore:
    """Build the real bundle (cached: models are parsed once per process)."""
    vault_cls = _load_real_part("vault", "HoneyVault", "T1 Dhruv")
    conventional_vault_cls = _load_real_part("baseline", "ConventionalVault", "T1 Dhruv")
    entry_dte_cls = _load_real_part("dte.entry_dte", "PCFGEntryDTE", "T1 Nidhi")
    sharing_cls = _load_real_part("sharing", "Sharing", "T4 Parth")
    pki_cls = _load_real_part("pki", "PKI", "T4 Parth")

    _require_model_files()
    entry_dte = entry_dte_cls.load_default()
    return HoneyCore(
        vault_cls=vault_cls.bind(entry_dte),
        conventional_vault_cls=conventional_vault_cls,
        entry_dte=entry_dte,
        # Same instance as PCFGPasswordModel.load_default() inside the entry DTE: one load.
        password_model=entry_dte.password_model,
        sharing=sharing_cls(),
        pki=pki_cls(),
    )


def load_honeycore(impl: Literal["stub", "real"]) -> HoneyCore:
    """Return the stub or real honeycore bundle.

    ``"real"`` imports modules lazily and returns a process-cached bundle. Raises
    ``NotImplementedError`` naming the owner of a missing module, and ``RuntimeError`` naming
    the file and the ``train_pcfg.py`` command if a PCFG model file is missing.
    """
    if impl == "stub":
        from honeycore import stubs

        return HoneyCore(
            vault_cls=stubs.StubHoneyVault,
            conventional_vault_cls=stubs.StubConventionalVault,
            entry_dte=stubs.StubEntryDTE(),
            password_model=stubs.StubPasswordModel(),
            sharing=stubs.StubSharing(),
            pki=stubs.StubPKI(),
        )
    if impl == "real":
        return _load_real()
    raise ValueError(f"unknown HONEYCORE_IMPL: {impl!r} (expected 'stub' or 'real')")
