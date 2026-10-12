"""Entry DTE: ``username_seed || password_seed`` = ``ENTRY_SEED_LEN`` bytes (PROJECT-BRIEF.md §7.5).

Owner: T1 — Nidhi. Phase 2.

Seed layout (``ENTRY_SEED_INTS`` = 133 big-endian uint32, one per choice, see §7.2)::

    bytes [0, 268)    username seed: PCFGUsernameModel, 67 ints (§7.4)
    bytes [268, 532)  password seed: PCFGPasswordModel, 66 ints (§7.3)

The halves are independent, so ``decode`` is total because both field DTEs are total: every
532-byte string maps to a (username, password) pair of 1..32 printable ASCII chars each. The
seed length never depends on the content (AGENTS.md §1.4).

``model_ids`` carries exactly the ids ``HoneyVault`` writes into the blob's ``dte`` block
(``password_model`` / ``username_model``, §7.8).
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType

from honeycore.dte.password_dte import PCFGPasswordModel
from honeycore.dte.username_dte import PCFGUsernameModel
from honeycore.interfaces import (
    ENTRY_SEED_LEN,
    INT_BYTES,
    PASSWORD_SEED_INTS,
    USERNAME_SEED_INTS,
)

__all__ = ["PASSWORD_SEED_LEN", "USERNAME_SEED_LEN", "PCFGEntryDTE"]

USERNAME_SEED_LEN = USERNAME_SEED_INTS * INT_BYTES  # 268
PASSWORD_SEED_LEN = PASSWORD_SEED_INTS * INT_BYTES  # 264
if USERNAME_SEED_LEN + PASSWORD_SEED_LEN != ENTRY_SEED_LEN:  # pragma: no cover - frozen constants
    raise RuntimeError("username + password seed lengths must equal ENTRY_SEED_LEN")


class PCFGEntryDTE:
    """``EntryDTE`` composing the PCFG username and password DTEs (PROJECT-BRIEF.md §7.5).

    ``PCFGEntryDTE()`` uses the default (process-cached) models; ``load_default()`` returns a
    cached instance; ``PCFGEntryDTE(username_model, password_model)`` composes any models
    (e.g. small ones trained in tests).
    """

    seed_len: int = ENTRY_SEED_LEN

    def __init__(
        self,
        username_model: PCFGUsernameModel | None = None,
        password_model: PCFGPasswordModel | None = None,
    ) -> None:
        """Compose the field DTEs (defaults: the packaged models, loaded once per process).

        Raises:
            FileNotFoundError: a default model file is missing (``scripts/train_pcfg.py``).
            ValueError: a model's ``seed_len`` does not match the §7.0 layout.
        """
        self.username_model = (
            username_model if username_model is not None else _default_username_model()
        )
        self.password_model = (
            password_model if password_model is not None else _default_password_model()
        )
        if self.username_model.seed_len != USERNAME_SEED_LEN:
            raise ValueError(f"username model seed_len must be {USERNAME_SEED_LEN}")
        if self.password_model.seed_len != PASSWORD_SEED_LEN:
            raise ValueError(f"password model seed_len must be {PASSWORD_SEED_LEN}")
        self.model_ids: Mapping[str, str] = MappingProxyType(
            {
                "password_model": self.password_model.model_id,
                "username_model": self.username_model.model_id,
            }
        )

    @classmethod
    def load_default(cls) -> PCFGEntryDTE:
        """Return the process-wide entry DTE over the packaged models (built once, cached).

        Raises:
            FileNotFoundError: a default model file is missing (``scripts/train_pcfg.py``).
        """
        return _default_entry_dte()

    def encode(self, username: str, password: str) -> bytes:
        """Encode one credential to a fresh random ``ENTRY_SEED_LEN``-byte seed.

        Raises:
            InvalidInputError: a field is outside the §7.1 limits (the value is not echoed).
        """
        seed = self.username_model.encode(username) + self.password_model.encode(password)
        if len(seed) != ENTRY_SEED_LEN:  # pragma: no cover - guarded by the seed_len checks
            raise RuntimeError("entry seed has the wrong length")
        return seed

    def decode(self, seed: bytes) -> tuple[str, str]:
        """TOTAL: map any ``ENTRY_SEED_LEN``-byte seed to a valid ``(username, password)``.

        Raises:
            ValueError: only if ``len(seed) != ENTRY_SEED_LEN``.
        """
        if len(seed) != ENTRY_SEED_LEN:
            raise ValueError(f"entry seed must be {ENTRY_SEED_LEN} bytes")
        return (
            self.username_model.decode(seed[:USERNAME_SEED_LEN]),
            self.password_model.decode(seed[USERNAME_SEED_LEN:]),
        )

    def sample(self) -> tuple[str, str]:
        """Return ``decode(random seed)``: a credential drawn from the model distribution."""
        return self.decode(secrets.token_bytes(ENTRY_SEED_LEN))


@lru_cache(maxsize=1)
def _default_username_model() -> PCFGUsernameModel:
    return PCFGUsernameModel.load_default()


@lru_cache(maxsize=1)
def _default_password_model() -> PCFGPasswordModel:
    return PCFGPasswordModel.load_default()


@lru_cache(maxsize=1)
def _default_entry_dte() -> PCFGEntryDTE:
    return PCFGEntryDTE(_default_username_model(), _default_password_model())
