"""``/api/users``: user identity lookup (public key + X.509 certificate).

Owner: T2 — Rohan. Contract: docs/api-contract.md (frozen).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/users", tags=["users"])

# TODO(T2 — Rohan): implement the endpoints listed in docs/api-contract.md.
