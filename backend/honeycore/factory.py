"""Select the honeycore implementation (``HONEYCORE_IMPL=stub|real``).

Owner: T1 lead — Nidhi ("real" wiring lands in Phase 2). Callers (the API, attack demo,
eval) must obtain every honeycore object through ``load_honeycore`` and never import
``stubs`` or real modules directly, so the stub -> real swap is a one-line env change.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Literal

from honeycore.interfaces import (
    ConventionalVaultAPI,
    EntryDTE,
    HoneyVaultAPI,
    PasswordModel,
    SharingAPI,
)


@dataclass(frozen=True)
class HoneyCore:
    """Bundle of honeycore implementations used by the rest of the backend."""

    vault_cls: type[HoneyVaultAPI]
    conventional_vault_cls: type[ConventionalVaultAPI]
    entry_dte: EntryDTE
    password_model: PasswordModel
    sharing: SharingAPI
    pki: Any  # no frozen PKI Protocol yet (T4 Parth to propose via contract-change)


# (module under honeycore, expected export, owner). Exports are instantiated with no args,
# except vault classes which are used as classes. Phase 2 may revise this table.
_REAL_PARTS: dict[str, tuple[str, str, str]] = {
    "vault_cls": ("vault", "HoneyVault", "T1 Dhruv"),
    "conventional_vault_cls": ("baseline", "ConventionalVault", "T1 Dhruv"),
    "entry_dte": ("dte.entry_dte", "PCFGEntryDTE", "T1 Nidhi"),
    "password_model": ("dte.password_dte", "PCFGPasswordModel", "T1 Nidhi"),
    "sharing": ("sharing", "Sharing", "T4 Parth"),
    "pki": ("pki", "PKI", "T4 Parth"),
}
_CLASS_FIELDS = {"vault_cls", "conventional_vault_cls"}


def _load_real_part(module: str, name: str, owner: str) -> Any:
    qualified = f"honeycore.{module}"
    try:
        obj = getattr(importlib.import_module(qualified), name)
    except (ImportError, AttributeError) as exc:
        raise NotImplementedError(f"{qualified} not implemented yet — owner: {owner}") from exc
    return obj


def load_honeycore(impl: Literal["stub", "real"]) -> HoneyCore:
    """Return the stub or real honeycore bundle.

    ``"real"`` imports modules lazily and raises ``NotImplementedError`` naming the owner of
    the first missing piece.
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
        parts: dict[str, Any] = {}
        for field_name, (module, name, owner) in _REAL_PARTS.items():
            obj = _load_real_part(module, name, owner)
            parts[field_name] = obj if field_name in _CLASS_FIELDS else obj()
        return HoneyCore(**parts)
    raise ValueError(f"unknown HONEYCORE_IMPL: {impl!r} (expected 'stub' or 'real')")
