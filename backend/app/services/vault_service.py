"""Vault service managing HoneyVaultAPI lifecycle and operations.

Owner: T2 — Tanuj.
Performs unlock, add, update, delete, export all through HoneyVaultAPI.
Never inspects or mutates blob internals directly.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.core import User, Vault
from honeycore.factory import HoneyCore
from honeycore.interfaces import Entry, HoneyVaultAPI, UnlockResult


class VaultHandle:
    """Wrapper exposing the HoneyVaultAPI instance while retaining the DB record."""

    def __init__(self, vault: HoneyVaultAPI, record: Vault) -> None:
        self.vault = vault
        self.record = record

    def __iter__(self):
        yield self.vault
        yield self.record

    def __getitem__(self, idx: int) -> Any:
        return (self.vault, self.record)[idx]

    def __len__(self) -> int:
        return 2

    def __getattr__(self, name: str) -> Any:
        return getattr(self.vault, name)


def get_or_create_vault(
    db: Session,
    user: User,
    honeycore: HoneyCore,
) -> VaultHandle:
    """Fetch existing vault for user or lazily create a new one using vault_cls.new()."""
    user_id = user.id if hasattr(user, "id") else str(user)
    vault_record = db.get(Vault, user_id)
    settings = get_settings()

    if vault_record is None:
        vault_obj = honeycore.vault_cls.new(settings.vault_kdf_profile)
        vault_record = Vault(user_id=user_id, blob=vault_obj.to_dict())
        db.add(vault_record)
        db.commit()
        db.refresh(vault_record)
    else:
        vault_obj = honeycore.vault_cls.from_dict(vault_record.blob)

    return VaultHandle(vault=vault_obj, record=vault_record)


def unlock_vault(
    db: Session,
    user: User,
    honeycore: HoneyCore,
    master_password: str,
) -> UnlockResult:
    """Unlock the user's vault with master_password.

    ALWAYS returns UnlockResult (decoy or real), never raises on wrong password.
    """
    handle = get_or_create_vault(db, user, honeycore)
    return handle.vault.unlock(master_password)


def add_entry(
    db: Session,
    user: User,
    honeycore: HoneyCore,
    master_password: str,
    entry: Entry,
) -> str:
    """Encrypt and append an entry to the user's vault, returning the new entry ID."""
    handle = get_or_create_vault(db, user, honeycore)
    entry_id = handle.vault.add_entry(master_password, entry)
    handle.record.blob = handle.vault.to_dict()
    db.commit()
    return entry_id


def update_entry(
    db: Session,
    user: User,
    honeycore: HoneyCore,
    master_password: str,
    entry_id: str,
    entry: Entry,
) -> str:
    """Update an existing entry in the user's vault."""
    handle = get_or_create_vault(db, user, honeycore)
    handle.vault.update_entry(master_password, entry_id, entry)
    handle.record.blob = handle.vault.to_dict()
    db.commit()
    return entry_id


def delete_entry(
    db: Session,
    user: User,
    honeycore: HoneyCore,
    entry_id: str,
) -> None:
    """Delete an entry from the user's vault."""
    handle = get_or_create_vault(db, user, honeycore)
    handle.vault.delete_entry(entry_id)
    handle.record.blob = handle.vault.to_dict()
    db.commit()


def export_vault(
    db: Session,
    user: User,
    honeycore: HoneyCore,
) -> dict:
    """Export the user's vault blob v1."""
    handle = get_or_create_vault(db, user, honeycore)
    return handle.vault.to_dict()


# Direct function aliases
unlock = unlock_vault
add = add_entry
update = update_entry
delete = delete_entry
export = export_vault
