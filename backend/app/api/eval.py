"""`/api/eval`: evaluation summary (serves eval/results/latest.json).

Owner: T2 — Tanuj. Contract: docs/api-contract.md §7 (frozen).

GET /eval/summary — no auth
    200  JSON contents of EVAL_RESULTS_PATH
    404  {\"detail\": \"No evaluation results yet\"}  if the file is missing
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings

router = APIRouter(prefix="/api/eval", tags=["eval"])


@router.get("/summary")
def eval_summary() -> JSONResponse:
    """Return the latest evaluation results JSON.

    Reads ``EVAL_RESULTS_PATH`` (relative to the backend working directory).
    Never raises on wrong passwords — there is no auth on this endpoint.
    """
    settings = get_settings()
    path = Path(settings.eval_results_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No evaluation results yet")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # Treat a corrupt/unreadable file as "not yet available".
        raise HTTPException(status_code=404, detail="No evaluation results yet") from exc

    return JSONResponse(content=data)
