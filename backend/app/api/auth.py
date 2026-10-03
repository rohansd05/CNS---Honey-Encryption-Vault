"""``/api/auth``: register / login / me (JWT, honeywords login via Rohan's service).

Owner: T2 — Tanuj. Contract: docs/api-contract.md (frozen).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/auth", tags=["auth"])

# TODO(T2 — Tanuj): implement the endpoints listed in docs/api-contract.md.
