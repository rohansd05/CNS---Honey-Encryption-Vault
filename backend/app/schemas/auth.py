"""Pydantic v2 schemas for authentication, user profiles, and admin alerts.

Owner: T2 — Rohan. Contract: docs/api-contract.md §2, §6, §0.5.
"""

from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """Payload for user registration."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_.-]+$",
        description="Account username",
    )
    login_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Authentication password for login",
    )
    master_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Master password for decrypting the honey vault",
    )


class RegisterResponse(BaseModel):
    """Response returned upon successful registration."""

    id: str
    username: str


class LoginRequest(BaseModel):
    """Payload for user login."""

    username: str = Field(..., min_length=1, max_length=32)
    login_password: str = Field(..., min_length=1, max_length=128)


class UserSummary(BaseModel):
    """Public user identity metadata included in authentication responses."""

    id: str
    username: str
    is_admin: bool


class LoginResponse(BaseModel):
    """Response payload for successful login with JWT."""

    access_token: str
    token_type: str = "bearer"  # noqa: S105
    user: UserSummary


class UserMeResponse(BaseModel):
    """Current authenticated user profile and vault statistics."""

    id: str
    username: str
    is_admin: bool
    created_at: datetime.datetime
    entry_count: int


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
