"""Pydantic v2 request/response schemas for ``/api/vault``.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §3, §0.5.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _check_printable_ascii(v: str, field_name: str) -> str:
    """Validate 1..32 printable ASCII chars (0x20..0x7E) without leaking values in errors."""
    if not (1 <= len(v) <= 32):
        raise ValueError(f"{field_name} length must be between 1 and 32 characters")
    if not all(0x20 <= ord(c) <= 0x7E for c in v):
        raise ValueError(f"{field_name} must contain only printable ASCII characters")
    return v


class UnlockRequest(BaseModel):
    """Request payload for unlocking the vault."""

    master_password: str = Field(min_length=1, max_length=128)


class SigilResponse(BaseModel):
    """Vault sigil key fingerprint."""

    emojis: list[str] = Field(min_length=3, max_length=3)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class DecodedEntryResponse(BaseModel):
    """Decoded vault entry item."""

    id: str
    service: str
    username: str
    password: str
    created_at: str
    updated_at: str


class UnlockResponse(BaseModel):
    """Response payload for vault unlock."""

    entries: list[DecodedEntryResponse]
    sigil: SigilResponse


class EntryCreateRequest(BaseModel):
    """Request payload for adding an entry."""

    master_password: str = Field(min_length=1, max_length=128)
    service: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=32)

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("service must be a non-empty string")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _check_printable_ascii(v, "username")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_printable_ascii(v, "password")


class EntryUpdateRequest(BaseModel):
    """Request payload for updating an entry."""

    master_password: str = Field(min_length=1, max_length=128)
    service: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=32)

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("service must be a non-empty string")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return _check_printable_ascii(v, "username")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _check_printable_ascii(v, "password")


class EntryMutationResponse(BaseModel):
    """Response payload returning the entry ID on creation or update."""

    id: str
