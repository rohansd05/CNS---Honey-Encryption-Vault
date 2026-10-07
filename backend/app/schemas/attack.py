"""Pydantic v2 schemas for the /api/attack endpoints.

Owner: T2 — Tanuj. Contract: docs/api-contract.md §8 (frozen).
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StolenVaultResponse(BaseModel):
    """Payload returned by GET /api/attack/stolen-vault."""

    honey_blob: dict[str, Any]
    baseline_blob: dict[str, Any]
    owner: str


class DictionaryAttackRequest(BaseModel):
    """Request payload for POST /api/attack/dictionary."""

    max_guesses: int = Field(
        default=300,
        ge=1,
        le=2000,
        description="Maximum number of candidate guesses to evaluate (1..2000, default 300)",
    )
    custom_guesses: list[str] | None = Field(
        default=None,
        description="Optional candidate passwords (<= 2000 items, each 1..32 printable chars)",
    )

    @field_validator("custom_guesses")
    @classmethod
    def validate_custom_guesses(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        if len(v) > 2000:
            raise ValueError("custom_guesses cannot exceed 2000 items")
        for idx, guess in enumerate(v):
            if not (1 <= len(guess) <= 32):
                raise ValueError(f"Guess at index {idx} must be 1-32 characters")
            if any(ord(c) < 32 or ord(c) > 126 for c in guess):
                raise ValueError(f"Guess at index {idx} must be printable ASCII")
        return v


class CrackedEntry(BaseModel):
    """An entry as returned by dictionary attack results."""

    id: str
    service: str
    username: str
    password: str
    created_at: str
    updated_at: str


class BaselineAttackResult(BaseModel):
    """Conventional baseline outcome in dictionary attack response."""

    cracked: bool
    guess_index: int | None = None
    elapsed_ms: int
    recovered_entries: list[CrackedEntry]


class HoneySample(BaseModel):
    """One sampled vault from the honey encryption dictionary attack."""

    guess_index: int
    guess: str
    entries: list[CrackedEntry]


class HoneyAttackResult(BaseModel):
    """Honey vault outcome in dictionary attack response."""

    guesses_tried: int
    elapsed_ms: int
    distinct_vaults: int
    samples: list[HoneySample]


class RevealResult(BaseModel):
    """Post-hoc reveal showing where the real master password landed."""

    real_guess_index: int | None = None


class DictionaryAttackResponse(BaseModel):
    """Complete response payload for POST /api/attack/dictionary."""

    baseline: BaselineAttackResult
    honey: HoneyAttackResult
    reveal: RevealResult


class StolenHoneywordsResponse(BaseModel):
    """Payload returned by GET /api/attack/stolen-honeywords."""

    username: str
    k: int
    salt: str
    hashes: list[str]
    cracked_sweetwords: list[str]


class AttackAlarmResponse(BaseModel):
    """An alert entry returned by GET /api/attack/alarms."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    kind: str
    severity: str
    sweetword_index: int | None = None
    source_ip: str | None = None
    user_agent: str | None = None
    created_at: datetime.datetime
