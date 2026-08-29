"""Ticket HTTP surface.

This router is intentionally thin. Every decision -- category canonicalisation,
ward resolution, the two SLA clocks, deduplication, cost estimation, criteria
derivation -- lives in ``services.tickets`` so that the entire ingest path can be
executed and tested without an HTTP server. What is left here is request parsing,
status codes and the response shapes the existing React app already consumes.

Two compatibility rules are load-bearing and must not be "cleaned up":

* ``POST /api/tickets/submit`` returns ``id``, ``message`` and ``is_duplicate``
  because ``src/components/TicketForm.jsx`` reads exactly those three fields;
* ``GET /api/tickets/list`` returns the array under ``tickets`` (with ``items``
  as an alias) because ``Dashboard.jsx`` reads ``ticketsRes.tickets``, and each
  row carries ``cci_score`` rather than ``latest_cci``.

Three bugs from the previous version are fixed by construction: ``is_duplicate``
was called on a function returning a *tuple* (always truthy, so every photo
report was merged), proximity was queried but never actually compared, and the
per-category TFN table hard-coded the very "fixed rule dressed as AI" the brief
rules out. The photo is also no longer mandatory -- refusing a report because a
citizen has no camera is not something a municipal council can defend.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional

from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     Request, UploadFile)
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, transaction  # noqa: E402
from services import tickets as svc  # noqa: E402
from services import wards as ward_svc  # noqa: E402

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _actor(request: Request) -> str:
    """Who is acting, as far as we can honestly tell.

    Until the auth layer lands this is the caller's IP, not an identity. Naming
    it ``anonymous_<ip>`` keeps the audit trail truthful instead of attributing
    the action to a user that was never authenticated.
    """
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("username"):
        return str(user["username"])
    client = request.client.host if request.client else "unknown"
    return f"anonymous_{client}"


class CostInputPayload(BaseModel):
    """Real money and real hours an officer measured, replacing estimated lines.

    Field names match ``domain.costing``'s runtime inputs exactly so an operator
    entry lands on the same line it replaces, and the resulting breakdown still
    says which lines came from a reference rate and which from the field.
    """
    runtime_vehicle_cost: Optional[float] = Field(None, ge=0)
    runtime_labour_cost: Optional[float] = Field(None, ge=0)
    runtime_material_cost: Optional[float] = Field(None, ge=0)
    other_cost: Optional[float] = Field(None, ge=0)
    crew_hours: Optional[float] = Field(None, ge=0)
    equipment_hours: Optional[dict[str, float]] = Field(
        None, description="machine code -> hours, e.g. {'JCB_3DX': 2.5}")
    note: Optional[str] = None


class ConditionPayload(BaseModel):
    """Escalating conditions, only ever set by a human who checked."""
    blocks_major_road: Optional[bool] = None
    access_isolated: Optional[bool] = None
    critical_facility_isolated: Optional[bool] = None
    note: Optional[str] = None


class StatusPayload(BaseModel):
    status: str
    note: Optional[str] = None


class WardPayload(BaseModel):
    """Ward master data. Everything optional: partial truth beats invention."""
    id: Optional[str] = None
    ward_no: Optional[str] = None
    name: Optional[str] = None
    population: Optional[int] = Field(None, ge=0)
    households: Optional[int] = Field(None, ge=0)
    area_sq_km: Optional[float] = Field(None, gt=0)
    centroid_lat: Optional[float] = Field(None, ge=-90, le=90)
    centroid_lon: Optional[float] = Field(None, ge=-180, le=180)
    equity_index: Optional[float] = Field(None, ge=0, le=1)
    flood_exposure: Optional[float] = Field(None, ge=0, le=1)
    data_confidence: Optional[str] = None
    source_note: Optional[str] = None


@router.post("/submit")
async def submit_ticket(
    request: Request,
    citizen_phone: Optional[str] = Form(None),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lon: Optional[float] = Form(None),
    ward_id: Optional[str] = Form(None),
    landmark: Optional[str] = Form(None),
    sensitive_site: Optional[str] = Form(None),
    affected_population: Optional[int] = Form(None),
    duration_hours: Optional[float] = Form(None),
    channel: Optional[str] = Form("web"),
    file: Optional[UploadFile] = File(None),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Register a citizen report and tell the citizen what happened to it.

    The photo is optional. When present it is hashed and used for duplicate
    detection; when absent the report falls back to text-plus-proximity
    matching, which is weaker and is reported as such rather than silently
    treated as equivalent.
    """
    uploads: list[dict[str, Any]] = []
    if file is not None and file.filename:
        content = await file.read()
        if content:
            uploads.append({"filename": file.filename, "content": content})

    payload = {
        "citizen_phone": citizen_phone, "category": category,
        "description": description, "lat": lat, "lon": lon,
        "ward_id": ward_id, "landmark": landmark,
        "sensitive_site": sensitive_site,
        "affected_population": affected_population,
        "duration_hours": duration_hours, "channel": channel or "web",
    }
    try:
        with transaction(conn):
            result = svc.create_ticket(conn, payload, uploads, _actor(request))
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500,
                            detail=f"could not store the report: {exc}") from exc
    return result


@router.get("/list")
def list_tickets(
    status: Optional[str] = None,
    ward_id: Optional[str] = None,
    category: Optional[str] = None,
    sla: Optional[str] = Query(None, description="ON_TRACK | DUE_SOON | BREACHED"),
    include_duplicates: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Work queue, highest live priority first, duplicates hidden by default."""
    result = svc.list_tickets(conn, status=status, ward_id=ward_id,
                              category=category, sla=sla,
                              include_duplicates=include_duplicates,
                              limit=limit, offset=offset)
    # 'tickets' is the key the shipped dashboard reads; 'items' is the new name.
    return {"tickets": result["items"], "items": result["items"],
            "count": result["count"], "total": result["total"],
            "limit": limit, "offset": offset}


@router.get("/queue")
def prioritisation_queue(ward_id: Optional[str] = None,
                         conn: sqlite3.Connection = Depends(get_db)):
    """Exactly the rows the next triage run will consider, and nothing else."""
    rows = svc.queue_for_prioritisation(conn, ward_id)
    return {"count": len(rows), "tickets": rows,
            "note": "open, scored or deferred non-duplicate tickets"}


@router.get("/wards")
def list_wards(include_inactive: bool = False,
               conn: sqlite3.Connection = Depends(get_db)):
    """Ward list plus an honest statement of what is missing from it."""
    return {"wards": ward_svc.list_wards(conn, include_inactive),
            "coverage": ward_svc.coverage(conn)}


@router.put("/wards/{ward_id}")
def upsert_ward(ward_id: str, payload: WardPayload, request: Request,
                conn: sqlite3.Connection = Depends(get_db)):
    """Enter or correct ward data. Recorded as operator-entered, not verified.

    This is the path by which the equity criterion stops being a wide "we do not
    know" interval, so the provenance of each number matters more than the
    number itself.
    """
    body = payload.model_dump(exclude_none=True)
    body["id"] = ward_id
    with transaction(conn):
        ward = ward_svc.upsert_ward(conn, body, _actor(request))
        rescored = [svc.rescore_ticket(conn, row["id"])
                    for row in svc.queue_for_prioritisation(conn, ward["id"])]
    return {"ward": ward, "rescored": len(rescored),
            "note": "equity for this ward's open tickets was re-derived"}


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Everything known about one report, including why it scored as it did."""
    detail = svc.get_ticket(conn, ticket_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return detail


@router.post("/{ticket_id}/cost")
def enter_cost(ticket_id: str, payload: CostInputPayload, request: Request,
               conn: sqlite3.Connection = Depends(get_db)):
    """Replace estimated cost lines with measured ones and re-derive C4.

    Unknown lines stay NULL rather than becoming 0: a ticket whose cost is
    unknown must not out-compete one that is genuinely cheap.
    """
    body = payload.model_dump(exclude_none=True)
    if not body:
        raise HTTPException(status_code=400, detail="no cost values supplied")
    with transaction(conn):
        result = svc.update_cost_inputs(conn, ticket_id, body, _actor(request))
    if not result.get("updated"):
        raise HTTPException(status_code=404,
                            detail=result.get("reason", "ticket not found"))
    return result


@router.post("/{ticket_id}/conditions")
def confirm_conditions(ticket_id: str, payload: ConditionPayload,
                       request: Request,
                       conn: sqlite3.Connection = Depends(get_db)):
    """Confirm on-ground conditions that can raise the priority floor.

    Kept behind an explicit human confirmation because 'critical' is the level
    at which other citizens' work gets displaced, and a self-declared checkbox
    on a public form is not evidence.
    """
    body = payload.model_dump(exclude_none=True)
    if not body:
        raise HTTPException(status_code=400, detail="no conditions supplied")
    with transaction(conn):
        result = svc.confirm_conditions(conn, ticket_id, body, _actor(request))
    if not result.get("updated"):
        raise HTTPException(status_code=404,
                            detail=result.get("reason", "ticket not found"))
    return result


@router.post("/{ticket_id}/status")
def set_status(ticket_id: str, payload: StatusPayload, request: Request,
               conn: sqlite3.Connection = Depends(get_db)):
    """Move a ticket along the lifecycle, refusing impossible transitions."""
    with transaction(conn):
        result = svc.update_status(conn, ticket_id, payload.status,
                                   _actor(request), payload.note)
    if not result.get("updated"):
        reason = result.get("reason", "ticket not found")
        code = 404 if "not found" in reason else 409
        raise HTTPException(status_code=code, detail=reason)
    return result


@router.post("/{ticket_id}/unmerge")
def unmerge(ticket_id: str, request: Request,
            conn: sqlite3.Connection = Depends(get_db)):
    """Undo a merge an officer judges wrong, restoring the ticket's own place.

    An automated merge that cannot be reversed is an automated deletion of a
    citizen's complaint, so this endpoint is part of the dedup design, not an
    afterthought.
    """
    from services import dedup

    with transaction(conn):
        result = dedup.unmerge(conn, ticket_id, _actor(request))
    if not result.get("applied"):
        raise HTTPException(status_code=409,
                            detail=result.get("reason", "not a merged ticket"))
    return result


@router.post("/{ticket_id}/rescore")
def rescore(ticket_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Re-derive the four criteria after underlying facts changed."""
    with transaction(conn):
        result = svc.rescore_ticket(conn, ticket_id)
    if not result.get("updated"):
        raise HTTPException(status_code=404,
                            detail=result.get("reason", "ticket not found"))
    return result
