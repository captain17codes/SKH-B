"""Triage HTTP surface: the endpoint where the brief is actually answered.

``POST /api/triage/run`` is the one request in this codebase that takes a pile of
competing complaints, a finite number of rupees and crew-hours, and returns a
decision it can defend ticket by ticket -- including for the tickets it turned
down. Everything else here reads that decision back.

Two rules shaped this module:

* **Nothing is computed here.** The ranking, the urgency fold, the knapsack and
  the audit trail all live in ``services.prioritisation``. A router that does
  arithmetic is a router whose arithmetic cannot be unit-tested without a running
  server, and the previous version of this file carried a hard-coded
  ``category -> (cost, hours)`` table that is exactly the "fixed rule dressed as
  AI" the hackathon brief warns against. It is gone; costs come from the cost
  engine or are declared unknown.
* **The response shapes the React app already reads are preserved exactly.**
  ``budget_cap``, ``workforce_cap_hours``, ``solver_status``, ``summary``,
  ``cost_estimate``, ``hours_estimate``, ``cci_score`` and friends all still mean
  what ``ManifestView.jsx`` and ``Dashboard.jsx`` expect. New fields
  (``reason_code``, ``attribution``, ``top_driver``, ``rank`` ...) are additive,
  so the frontend teammate can adopt them at their own pace and nothing breaks
  in the meantime.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, transaction  # noqa: E402
from services import prioritisation as svc  # noqa: E402

router = APIRouter(prefix="/api/triage", tags=["triage"])

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _actor(request: Request) -> str:
    """Who to record against this run.

    Auth is not enforced yet, so this cannot be trusted as an identity -- but a
    manifest with ``created_by: anonymous_127.0.0.1`` is still more honest than a
    manifest with no attribution at all, and the field does not change shape once
    JWT lands.
    """
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("username"):
        return str(user["username"])
    client = request.client.host if request.client else "unknown"
    return f"anonymous_{client}"


def _require_date(value: str) -> str:
    if not _ISO_DATE.match(value or ""):
        raise HTTPException(status_code=400,
                            detail="date must be YYYY-MM-DD")
    return value


class TriageRunRequest(BaseModel):
    """What the panel is asking for.

    ``daily_budget`` and ``daily_workforce`` are optional on purpose. The shipped
    frontend always sends them, so its contract is untouched, but a council that
    has entered today's real figures through ``PUT /capacity`` should not have to
    re-type them into every run -- omitting them uses the stored, attributable
    row and the manifest records which of the two it was.
    """
    daily_budget: Optional[float] = Field(None, ge=0)
    daily_workforce: Optional[float] = Field(None, ge=0)
    ward_id: Optional[str] = None
    dispatch_date: Optional[str] = Field(
        None, description="YYYY-MM-DD; defaults to today")
    dry_run: bool = Field(False, description="compute the plan, write nothing")
    solver: Optional[str] = Field(
        None, description="'dp' or 'cpsat'; defaults to the configured solver")


class CapacityResource(BaseModel):
    resource_type: str
    display_name: Optional[str] = None
    available_now: Optional[float] = None
    hourly_rate_inr: Optional[float] = None
    rate_source: Optional[str] = None
    note: Optional[str] = None

class CapacityPayload(BaseModel):
    """Today's real constraints, as entered by a named officer.

    ``verified_by`` is not decoration: a capacity figure nobody signed for is
    labelled as such in every manifest built on top of it, so the run can say
    "this plan assumed a default the council never confirmed" instead of quietly
    presenting a guess as a fact.
    """
    capacity_date: Optional[str] = None
    ward_id: Optional[str] = None
    budget_inr: Optional[float] = Field(None, ge=0)
    workforce_hours: Optional[float] = Field(None, ge=0)
    verified_by: Optional[str] = None
    note: Optional[str] = None
    resources: Optional[list[CapacityResource]] = None


def _solver_status(solver: Any, optimal: Any, outcome: Any) -> str:
    """A one-word status that does not overclaim.

    The old router returned ``OPTIMAL`` whenever anything at all was selected,
    which is a claim about the search, not about the answer. A beam-limited DP
    genuinely may have missed a better set, and a day whose safety floor alone
    blows the budget is not "optimal" under any reading -- it is a warning.
    """
    if outcome == "mandatory_over_capacity":
        return "MANDATORY_OVER_CAPACITY"
    if solver in (None, ""):
        return "NOT_RUN"
    return "OPTIMAL" if optimal else "FEASIBLE_BEAM_LIMITED"


def _num(value: Any) -> Any:
    """Round for display without turning a missing number into zero.

    ``cost_estimate: 0`` and ``cost_estimate: null`` mean opposite things here --
    free versus not yet estimated -- so the two must never collapse.
    """
    return None if value is None else round(float(value), 2)


def _item_view(entry: dict) -> dict:
    """One manifest line in the shape the dashboard already reads, plus the why.

    Every key the shipped ``ManifestView.jsx`` touches keeps its name and meaning.
    The additions are the defensible part: which criterion drove the score, the
    exact per-criterion decomposition, and a machine code plus a sentence saying
    why this ticket was or was not scheduled today.
    """
    decision = entry.get("decision") or "deferred"
    return {
        # --- the existing frontend contract, unchanged
        "ticket_id": entry.get("ticket_id"),
        "selected": decision == "allocated",
        "cost_estimate": _num(entry.get("cost_inr")),
        "hours_estimate": _num(entry.get("hours")),
        "category": entry.get("category"),
        "cci_score": entry.get("cci_score"),
        "citizen_phone": entry.get("citizen_phone"),
        "lat": entry.get("lat"),
        "lon": entry.get("lon"),
        "ward_id": entry.get("ward_id"),
        # --- additive: the justification
        "ref_no": entry.get("ref_no"),
        "description": entry.get("description"),
        "status": entry.get("status"),
        "rank": entry.get("rank_position"),
        "topsis_rank": entry.get("topsis_rank"),
        "decision": decision,
        "reason_code": entry.get("reason_code"),
        "reason_text": entry.get("reason_text"),
        "cci_base": entry.get("cci_base"),
        "community_multiplier": entry.get("community_multiplier"),
        "report_count": entry.get("report_count"),
        "priority_floor": entry.get("priority_floor"),
        "cost_status": entry.get("cost_status"),
        "department_id": entry.get("department_id"),
        "required_roles": entry.get("required_roles"),
        "top_driver": entry.get("top_driver"),
        "attribution": entry.get("attribution", []),
        "adjustment": entry.get("adjustment", {}),
        "sla": entry.get("sla", {}),
        "d_positive": entry.get("d_positive"),
        "d_negative": entry.get("d_negative"),
    }

def _run_item_view(row: dict) -> dict:
    """The same line shape, built from a live run instead of a stored manifest.

    ``services.prioritisation`` names these fields after the ticket columns they
    came from (``estimated_cost_inr``), while a stored manifest names them after
    the manifest columns (``cost_inr``). Both are correct in their own layer; the
    API must present one vocabulary, so the translation happens here rather than
    leaking two shapes to the frontend.
    """
    return _item_view({
        "ticket_id": row.get("ticket_id"),
        "decision": row.get("decision"),
        "cost_inr": row.get("estimated_cost_inr"),
        "hours": row.get("estimated_hours"),
        "category": row.get("category"),
        "cci_score": row.get("cci_score"),
        "citizen_phone": row.get("citizen_phone"),
        "lat": row.get("lat"), "lon": row.get("lon"),
        "ward_id": row.get("ward_id"), "ref_no": row.get("ref_no"),
        "description": row.get("description"), "status": row.get("status"),
        "rank_position": row.get("rank"), "topsis_rank": row.get("topsis_rank"),
        "reason_code": row.get("reason_code"),
        "reason_text": row.get("reason_text"),
        "cci_base": row.get("cci_base"),
        "community_multiplier": row.get("community_multiplier"),
        "report_count": row.get("report_count"),
        "priority_floor": row.get("priority_floor"),
        "cost_status": row.get("cost_status"),
        "top_driver": row.get("top_driver"),
        "attribution": row.get("attribution", []),
        "sla": row.get("sla", {}),
    })


def _manifest_view(manifest: dict) -> dict:
    """A stored manifest as the dashboard reads it, with the caveats attached.

    ``budget_cap`` / ``workforce_cap_hours`` / ``solver_status`` / ``summary`` are
    the names the shipped component destructures, so they stay. Underneath them
    the manifest also carries what it was allowed to assume: which weight version
    ranked the queue, where the capacity number came from, whether anyone signed
    for it, and how many tickets were held back purely because nobody has costed
    them yet. A plan is only defensible if its assumptions travel with it.
    """
    notes = manifest.get("notes")
    notes = notes if isinstance(notes, dict) else {}
    scheduled = [_item_view(r) for r in manifest.get("scheduled", [])]
    deferred = [_item_view(r) for r in manifest.get("deferred", [])]
    return {
        # --- the existing frontend contract, unchanged
        "manifest_id": manifest.get("id"),
        "dispatch_date": manifest.get("dispatch_date"),
        "budget_cap": _num(manifest.get("budget_available")),
        "workforce_cap_hours": _num(manifest.get("workforce_available")),
        "solver_status": _solver_status(manifest.get("solver"),
                                        notes.get("solver_optimal", True),
                                        manifest.get("budget_outcome")),
        "summary": {
            "total_tickets": manifest.get("total_candidates") or 0,
            "scheduled": manifest.get("allocated_count") or 0,
            "deferred": manifest.get("deferred_count") or 0,
        },
        "scheduled": scheduled,
        "deferred": deferred,
        # --- additive: what this plan assumed and what it spent
        "run_id": manifest.get("run_id"),
        "ward_id": manifest.get("ward_id"),
        "weight_version": manifest.get("weight_version"),
        "weights": notes.get("weights") or {},
        "budget_used": _num(manifest.get("budget_used")),
        "workforce_used": _num(manifest.get("workforce_used")),
        "budget_outcome": manifest.get("budget_outcome"),
        "solver": manifest.get("solver"),
        "solver_optimal": notes.get("solver_optimal"),
        "states_explored": notes.get("states_explored"),
        "objective_value": manifest.get("objective_value"),
        "cost_incomplete_count": manifest.get("cost_incomplete_count") or 0,
        "capacity_source": notes.get("capacity_source"),
        "capacity_verified": notes.get("capacity_verified"),
        "capacity_verified_by": notes.get("capacity_verified_by"),
        "allocator_notes": notes.get("allocator_notes") or [],
        "normalisation_notes": notes.get("normalisation_notes") or [],
        "skipped": notes.get("skipped") or [],
        "created_by": manifest.get("created_by"),
        "created_at": manifest.get("created_at"),
    }

@router.post("/run")
def run(payload: TriageRunRequest, request: Request,
        conn: sqlite3.Connection = Depends(get_db)):
    """Decide today's work under today's constraints, and record why.

    The whole run happens inside one transaction: either the manifest, the score
    history and every ticket status move land together, or none of them do. A
    half-written manifest -- tickets marked scheduled with no line explaining the
    decision -- is worse than a failed request, because it looks authoritative.

    ``dry_run: true`` returns the identical body with ``persisted: false`` and a
    null ``manifest_id``. That is the answer to "what would another 50,000 rupees
    buy us today?", which is the question that turns this from a scheduler into a
    budgeting argument the council can take to a meeting.
    """
    if payload.dispatch_date:
        _require_date(payload.dispatch_date)
    try:
        if payload.dry_run:
            result = svc.run_triage(
                conn, dispatch_date=payload.dispatch_date,
                ward_id=payload.ward_id, budget=payload.daily_budget,
                workforce=payload.daily_workforce, actor=_actor(request),
                solver=payload.solver, dry_run=True)
        else:
            with transaction(conn):
                result = svc.run_triage(
                    conn, dispatch_date=payload.dispatch_date,
                    ward_id=payload.ward_id, budget=payload.daily_budget,
                    workforce=payload.daily_workforce, actor=_actor(request),
                    solver=payload.solver, dry_run=False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    allocated = [_run_item_view(r) for r in result["allocated"]]
    deferred = [_run_item_view(r) for r in result["deferred"]]
    plan = result.get("plan") or {}
    capacity = result.get("capacity") or {}
    # ``total_cci_score`` is the top-ranked ticket's score, which is what the
    # previous implementation reported and what the dashboard tile shows. A sum
    # would be meaningless: adding closeness coefficients across tickets produces
    # a number that grows with queue length and says nothing about urgency.
    scores = [r["cci_score"] or 0.0 for r in allocated + deferred]
    top_score = max(scores) if scores else 0.0
    return {
        # --- the existing frontend contract, unchanged
        "message": result["message"],
        "prioritized_count": result["candidates"],
        "scheduled_count": plan.get("allocated_count", len(allocated)),
        "deferred_count": plan.get("deferred_count", len(deferred)),
        "manifest_id": result["manifest_id"],
        "total_cci_score": round(float(top_score), 6),
        # --- additive: the plan itself and everything it assumed
        "run_id": result["run_id"],
        "persisted": result["persisted"],
        "dry_run": payload.dry_run,
        "dispatch_date": result["dispatch_date"],
        "ward_id": result["ward_id"],
        "capacity": capacity,
        "budget_cap": _num(capacity.get("budget_inr")),
        "workforce_cap_hours": _num(capacity.get("workforce_hours")),
        "weight_version": result["weight_version"],
        "weights": result.get("weights") or {},
        "solver_status": _solver_status(plan.get("solver"),
                                       plan.get("optimal", True),
                                       plan.get("budget_outcome")),
        "plan": plan,
        "scheduled": allocated,
        "deferred": deferred,
        "unscorable": result["skipped"],
    }

@router.get("/manifest/{manifest_date}")
def manifest_for_date(manifest_date: str, ward_id: Optional[str] = None,
                      conn: sqlite3.Connection = Depends(get_db)):
    """The plan that was issued on a given day, exactly as it was issued.

    This reads the *stored* decisions rather than re-running the engine. If the
    weights changed this morning, yesterday's manifest must still show what was
    actually decided and under which weight version -- otherwise the audit trail
    rewrites itself every time the council revises its priorities, which is the
    one thing an audit trail may never do.
    """
    _require_date(manifest_date)
    manifest = svc.get_manifest(conn, dispatch_date=manifest_date,
                                ward_id=ward_id)
    if manifest is None:
        raise HTTPException(status_code=404,
                            detail=f"no dispatch manifest for {manifest_date}")
    return _manifest_view(manifest)


@router.get("/today")
def manifest_today(ward_id: Optional[str] = None,
                   conn: sqlite3.Connection = Depends(get_db)):
    """Today's plan. 404 until triage has been run, which the dashboard expects."""
    return manifest_for_date(svc.today_iso(), ward_id=ward_id, conn=conn)


@router.get("/manifest-by-id/{manifest_id}")
def manifest_by_id(manifest_id: str,
                   conn: sqlite3.Connection = Depends(get_db)):
    """A specific run, when several were issued on the same date.

    Re-running after a cost estimate arrives or the capacity is corrected is
    normal and produces a second manifest for the same day; ``/manifest/{date}``
    returns the newest, and this returns any of them by id so the two can be
    compared.
    """
    manifest = svc.get_manifest(conn, manifest_id=manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404,
                            detail=f"manifest {manifest_id} not found")
    return _manifest_view(manifest)


@router.get("/manifests")
def manifests(limit: int = Query(30, ge=1, le=200),
              ward_id: Optional[str] = None,
              conn: sqlite3.Connection = Depends(get_db)):
    """Recent runs, newest first -- enough to chart demand against capacity."""
    rows = svc.list_manifests(conn, limit=limit, ward_id=ward_id)
    return {"count": len(rows), "manifests": rows}

@router.get("/priorities")
def priorities(status: Optional[str] = None,
               ward_id: Optional[str] = None,
               limit: int = Query(50, ge=1, le=200),
               conn: sqlite3.Connection = Depends(get_db)):
    """The live queue in dispatch order, using each ticket's latest stored score.

    Unscored tickets sort last rather than being dropped. A ticket nobody has
    managed to score yet is still a citizen waiting, and a queue that quietly
    omits it is precisely the failure this project exists to prevent -- so it
    appears at the bottom with a null score and ``scored: false`` instead of
    vanishing or being ranked as a zero it never earned.
    """
    rows = svc.current_priorities(conn, ward_id=ward_id, limit=limit)
    if status:
        wanted = {s.strip() for s in status.split(",") if s.strip()}
        rows = [r for r in rows if r.get("status") in wanted]
    tickets = [{
        # --- the existing frontend contract, unchanged
        "id": row.get("id"),
        "citizen_phone": row.get("citizen_phone"),
        "category": row.get("category"),
        "cci_score": row.get("latest_cci"),
        "status": row.get("status"),
        "community_multiplier": row.get("community_multiplier"),
        "ward_id": row.get("ward_id"),
        "lat": row.get("lat"),
        "lon": row.get("lon"),
        # --- additive
        "ref_no": row.get("ref_no"),
        "description": row.get("description"),
        "scored": row.get("latest_cci") is not None,
        "rank": row.get("latest_rank"),
        "weight_version": row.get("latest_weight_version"),
        "report_count": row.get("report_count"),
        "priority_floor": row.get("priority_floor"),
        "cost_status": row.get("cost_status"),
        "estimated_cost_inr": _num(row.get("estimated_cost_inr")),
        "estimated_hours": _num(row.get("estimated_hours")),
        "is_statutory_rts": bool(row.get("is_statutory_rts")),
        "rts_deadline_at": row.get("rts_deadline_at"),
        "operational_deadline_at": row.get("operational_deadline_at"),
        "reported_at": row.get("reported_at"),
    } for row in rows]
    return {
        "tickets": tickets,
        "total": len(tickets),
        "unscored": sum(1 for t in tickets if not t["scored"]),
    }

@router.get("/capacity")
def capacity(capacity_date: Optional[str] = None,
             ward_id: Optional[str] = None,
             conn: sqlite3.Connection = Depends(get_db)):
    """What the council has to spend, and whether anyone stands behind the figure.

    Resolution order is ward row, then council row, then the configured default,
    and the answer says which one it used. ``configured_default_not_entered_by
    _council`` is not an error -- it is the honest label for a plan built on an
    assumption, and it travels into every manifest produced from it.
    """
    if capacity_date:
        _require_date(capacity_date)
    return svc.resolve_capacity(conn, capacity_date or svc.today_iso(), ward_id)


@router.put("/capacity")
def put_capacity(payload: CapacityPayload, request: Request,
                 conn: sqlite3.Connection = Depends(get_db)):
    """Record today's real budget and crew-hours. Upsert on (date, ward).

    Sending ``verified_by`` is what promotes a typed number into an attributable
    one. Both are stored; only the second lets a manifest claim its constraints
    were confirmed by a named officer.
    """
    if payload.capacity_date:
        _require_date(payload.capacity_date)
    if payload.budget_inr is None and payload.workforce_hours is None:
        raise HTTPException(
            status_code=400,
            detail="provide budget_inr and/or workforce_hours")
    with transaction(conn):
        result = svc.set_capacity(
            conn, capacity_date=payload.capacity_date, ward_id=payload.ward_id,
            budget_inr=payload.budget_inr,
            workforce_hours=payload.workforce_hours,
            verified_by=payload.verified_by, note=payload.note,
            resources=[r.model_dump() for r in payload.resources or []],
            actor=_actor(request))
    return result

