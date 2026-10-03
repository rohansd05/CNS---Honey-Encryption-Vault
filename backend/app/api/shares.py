"""``/api/shares``: secure entry sharing (seal, inbox, sent, open).

Owner: T2 — Rohan. Contract: docs/api-contract.md (frozen).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/shares", tags=["shares"])

# TODO(T2 — Rohan): implement the endpoints listed in docs/api-contract.md.
