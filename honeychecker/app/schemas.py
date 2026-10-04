"""Pydantic schemas for the honeychecker service.

Owner: T2 — Rohan.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RegisterRequest(BaseModel):
    """Payload for registering a user's real sweetword index."""

    user_id: str = Field(..., min_length=1, description="Unique user ID (UUID)")
    index: int = Field(..., ge=0, description="Real sweetword index (non-negative)")


class RegisterResponse(BaseModel):
    """Response returned upon successful registration."""

    status: str = "registered"


class CheckRequest(BaseModel):
    """Payload for checking a submitted sweetword index."""

    user_id: str = Field(..., min_length=1, description="Unique user ID (UUID)")
    index: int = Field(..., ge=0, description="Submitted sweetword index (non-negative)")


class CheckResponse(BaseModel):
    """Result of sweetword index comparison."""

    match: bool


class AlarmOut(BaseModel):
    """Alarm item returned by GET /hc/alarms."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    claimed_index: int
    kind: str
    created_at: datetime.datetime

    @computed_field
    @property
    def submitted_index(self) -> int:
        """Alias for claimed_index matching docs/api-contract.md."""
        return self.claimed_index


class HealthResponse(BaseModel):
    """Liveness probe response."""

    status: str
    service: str = "honeychecker"
    version: str
    db: str
