"""Pydantic v2 schemas for /api/admin endpoints.

Owner: T2 — Tanuj / Rohan. Contract: docs/api-contract.md §6 (frozen).
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


def format_utc_iso(dt: datetime.datetime | str) -> str:
    """Format datetime or string as UTC ISO-8601 with explicit Z offset."""
    if isinstance(dt, str):
        if dt.endswith("Z") or "+" in dt or dt.endswith("-00:00"):
            return dt
        return dt + "Z"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    else:
        dt = dt.astimezone(datetime.UTC)
    return dt.isoformat().replace("+00:00", "Z")


class AlertResponse(BaseModel):
    """Honeyword breach alert schema for admin view."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    kind: str
    severity: str
    sweetword_index: int | None = None
    source_ip: str | None = None
    user_agent: str | None = None
    created_at: datetime.datetime

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_tz_aware(cls, dt: datetime.datetime) -> datetime.datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=datetime.UTC)
        return dt.astimezone(datetime.UTC)

    @field_serializer("created_at", when_used="always")
    def serialize_created_at(self, dt: datetime.datetime) -> str:
        return format_utc_iso(dt)
