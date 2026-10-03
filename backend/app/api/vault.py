"""``/api/vault``: unlock (ALWAYS 200), entry CRUD, export of the vault blob.

Owner: T2 — Tanuj. Contract: docs/api-contract.md (frozen).
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/vault", tags=["vault"])

# TODO(T2 — Tanuj): implement the endpoints listed in docs/api-contract.md.
