"""Criteria-weight HTTP surface: the panel's way into the ranking.

These endpoints are what turn "the weights came from somewhere defensible" from a
claim into a demonstrable workflow. A panel member sees the linguistic scale, sends
six comparisons, and gets back either live weights or a refusal that names the
comparison to revisit.

Nothing here is additive to the frontend contract: no shipped component calls
these paths, so they can be added without touching ``src/``.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, transaction  # noqa: E402
from domain import ahp  # noqa: E402
from domain.criteria import CRITERIA, CRITERIA_TYPES  # noqa: E402
from services import weights as svc  # noqa: E402

router = APIRouter(prefix="/api/weights", tags=["weights"])


def _actor(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("username"):
        return str(user["username"])
    client = request.client.host if request.client else "unknown"
    return f"anonymous_{client}"


class Comparison(BaseModel):
    """One pairwise judgement: how much more important is ``a`` than ``b``?"""
    a: str = Field(..., description="criterion code, e.g. C2_safety")
    b: str = Field(..., description="criterion code, e.g. C4_cost")
    value: Any = Field(..., description="a scale label ('moderate'), a Saaty "
                                       "integer 1-9, its reciprocal, or a TFN "
                                       "triple [l, m, u]")


class DerivePayload(BaseModel):
    comparisons: list[Comparison] = Field(..., min_length=1)
    label: Optional[str] = None
    note: Optional[str] = None
    activate: bool = Field(True, description="adopt these weights if CR < 0.10")


@router.get("/scale")
def scale():
    """The linguistic scale, the criteria and the gate -- everything a form needs.

    Exposed so the UI never hard-codes the scale: if the fuzzification of
    'moderately more important' is ever revised, the form follows automatically.
    """
    return {
        "criteria": [{"code": code, "type": CRITERIA_TYPES[code],
                      "label": label}
                     for code, label in (
                         ("C1_infra", "Infrastructural criticality"),
                         ("C2_safety", "Public safety and health risk"),
                         ("C3_equity", "Socio-spatial equity"),
                         ("C4_cost", "Resource requirement"))
                     if code in CRITERIA],
        "scale": [{"label": key, "tfn": list(tfn),
                   "saaty_equivalent": int(tfn[1])}
                  for key, tfn in ahp.LINGUISTIC_SCALE.items()],
        "reciprocal_prefix": "inverse_",
        "comparisons_required": [
            {"a": CRITERIA[i], "b": CRITERIA[j]}
            for i in range(len(CRITERIA)) for j in range(i + 1, len(CRITERIA))],
        "consistency_threshold": ahp.CR_THRESHOLD,
        "method": "buckley_geometric_mean_fuzzy_ahp",
        "gate": ("A submission whose consistency ratio reaches 0.10 is stored as "
                 "evidence but cannot become the live weight set."),
    }


@router.get("/active")
def active(conn: sqlite3.Connection = Depends(get_db)):
    """The weights currently ranking work, in numbers and in a sentence."""
    with transaction(conn):
        # get_active seeds the declared default the first time it is called, so
        # this read can write exactly once in the lifetime of a deployment.
        explained = svc.explain_active(conn)
    return explained


@router.get("/versions")
def versions(limit: int = Query(50, ge=1, le=200),
             conn: sqlite3.Connection = Depends(get_db)):
    """Full weight history, including the sets that failed the gate."""
    rows = svc.list_versions(conn, limit)
    return {"count": len(rows), "versions": rows,
            "active_version": next((r["version"] for r in rows
                                    if r["is_active"]), None)}


@router.get("/versions/{version}")
def version_detail(version: int, conn: sqlite3.Connection = Depends(get_db)):
    row = svc.get_version(conn, version)
    if not row:
        raise HTTPException(status_code=404, detail=f"version {version} not found")
    return row


@router.get("/compare")
def compare(from_version: int, to_version: int,
            conn: sqlite3.Connection = Depends(get_db)):
    """Per-criterion delta between two weight sets."""
    result = svc.compare_versions(conn, from_version, to_version)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/preview")
def preview(payload: DerivePayload):
    """Derive weights without storing anything.

    Lets a panel see the effect of a judgement before committing to it, which is
    the difference between a consistency gate that teaches and one that merely
    rejects.
    """
    try:
        derivation = ahp.derive([c.model_dump() for c in payload.comparisons])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"crisp_weights": derivation["crisp_weights"],
            "fuzzy_weights": derivation["fuzzy_weights"],
            "consistency": derivation["consistency"],
            "cr_passed": derivation["cr_passed"],
            "would_activate": derivation["cr_passed"],
            "stored": False}


@router.post("/derive")
def derive(payload: DerivePayload, request: Request,
           conn: sqlite3.Connection = Depends(get_db)):
    """Store a panel's judgements and adopt them if they are consistent.

    Returns 200 even when the gate refuses: the submission was recorded, and the
    body explains precisely why it is not in force. A 4xx would suggest the panel
    did something malformed, when in fact they did something contradictory -- a
    different problem with a different fix.
    """
    try:
        with transaction(conn):
            result = svc.derive_and_save(
                conn, [c.model_dump() for c in payload.comparisons],
                label=payload.label, created_by=_actor(request),
                note=payload.note, activate=payload.activate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/versions/{version}/activate")
def activate(version: int, request: Request,
             conn: sqlite3.Connection = Depends(get_db)):
    """Roll back to, or forward to, a stored consistent weight set."""
    with transaction(conn):
        result = svc.activate_version(conn, version, _actor(request))
    if not result.get("activated"):
        reason = result.get("reason", "could not activate")
        raise HTTPException(status_code=404 if "does not exist" in reason else 409,
                            detail=reason)
    return result
