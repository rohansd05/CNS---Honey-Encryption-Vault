"""Password strength estimation API endpoint.

Owner: T5 — Aryan. Contract: docs/api-contract.md §9.
Unauthenticated utility endpoint. Synchronous, no database access.
Invariant: never logs, prints, stores, or returns submitted passwords.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.utils.strength import estimate_strength

router = APIRouter(prefix="/api/utils", tags=["utils"])


class StrengthRequest(BaseModel):
    """Request payload for password strength estimation."""

    password: str = Field(
        min_length=1,
        max_length=128,
        description="Password to evaluate for strength",
    )


class StrengthResponse(BaseModel):
    """Response payload for password strength estimation."""

    score: int = Field(ge=0, le=4, description="Strength score from 0 (weak) to 4 (very strong)")
    entropy_bits: float = Field(description="Estimated entropy in bits")
    feedback: list[str] = Field(
        default_factory=list,
        description="Actionable suggestions for improving password strength",
    )


@router.post("/strength", response_model=StrengthResponse)
def check_password_strength(payload: StrengthRequest) -> StrengthResponse:
    """Estimate password strength, entropy bits, and actionable feedback.

    Unauthenticated utility endpoint. Does not log, store, or return the submitted password.
    """
    result = estimate_strength(payload.password)
    return StrengthResponse(
        score=result.score,
        entropy_bits=result.entropy_bits,
        feedback=result.feedback,
    )
