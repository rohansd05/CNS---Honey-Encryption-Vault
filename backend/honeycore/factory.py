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

import hashlib
import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from honeycore.interfaces import (
    PKIAPI,
    ConventionalVaultAPI,
    EntryDTE,
    HoneyVaultAPI,
    PasswordModel,
    SharingAPI,
)

# Trusted SHA-256 digests for model artifacts (keyed by (kind, model_id)).
# Manifest records approved models: filename and lowercase hex SHA-256 digest.
MODEL_INTEGRITY_MANIFEST: dict[tuple[str, str], tuple[str, str]] = {
    ("password", "pcfg-password-v1"): (
        "pcfg_password_v1.json.gz",
        "f2ba0b8ab81e06aded1b456c0dc1c8fbf0e46e10d21dd0628346994a64a7a83d",
    ),
    ("password", "pcfg-password-v2"): (
        "pcfg_password_v2.json.gz",
        "8b225bb35d85624a2da1f4a3611574f2895336030660f2a838a63a3f159e76a6",
    ),
    ("username", "pcfg-username-v1"): (
        "pcfg_username_v1.json.gz",
        "ec5ffa2dfe40b0f469e8fe1ec74b37f67eb7b03e720edbe3abe9f89a57a26578",
    ),
}

MODEL_SHA256_MANIFEST: dict[str, str] = {
    fname: sha for _, (fname, sha) in MODEL_INTEGRITY_MANIFEST.items()
}


def _sha256(path: Path) -> str:
    """Return the lowercase hex SHA-256 digest of ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


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
    """Validate model ID approval, file existence, and SHA-256 integrity against the manifest."""
    from honeycore.dte import password_dte, username_dte

    for kind, mod in (
        ("password", password_dte),
        ("username", username_dte),
    ):
        model_id = getattr(mod, "MODEL_ID", None)
        path: Path | None = getattr(mod, "DEFAULT_MODEL_PATH", None)

        if (kind, model_id) not in MODEL_INTEGRITY_MANIFEST:
            raise RuntimeError(f"Unknown or unapproved PCFG {kind} model ID: {model_id!r}")

        expected_filename, expected_hash = MODEL_INTEGRITY_MANIFEST[(kind, model_id)]

        if path is None or path.name != expected_filename or path.name not in MODEL_SHA256_MANIFEST:
            name = path.name if path is not None else "None"
            raise RuntimeError(
                f"PCFG {kind} model file {name} is not in the trusted model manifest"
            )

        if not path.is_file():
            raise RuntimeError(
                f"PCFG {kind} model file not found: {path}. Train it from backend/ with: "
                f"python scripts/train_pcfg.py --kind {kind} --input {_TRAIN_INPUTS[kind]} "
                f"--out honeycore/models/{path.name} "
                "(fetch corpora first with scripts/download_corpus.py)"
            )

        actual_hash = _sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"PCFG {kind} model integrity check failed for {path.name}: "
                f"expected SHA-256 {expected_hash}, got {actual_hash}"
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
