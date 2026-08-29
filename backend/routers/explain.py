"""Explanation HTTP surface: why this ticket, and what the citizen was told.

Two audiences, one source of truth. An officer defending a plan needs the
arithmetic -- distances, per-criterion contributions, the rivals that took the
capacity. A citizen needs one paragraph in their own language. Both come out of
``services.explain`` from the *stored* score, so an explanation describes the
decision that was actually taken under the weights that were actually in force,
even after the weights change.

Nothing here alters an existing contract: no shipped component in ``src/`` calls
any ``/api/explain`` path, so this router is purely additive and cannot conflict
with the frontend track.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, transaction  # noqa: E402
from services import explain as svc  # noqa: E402

router = APIRouter(prefix="/api/explain", tags=["explain"])


def _actor(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if isinstance(user, dict) and user.get("username"):
        return str(user["username"])
    client = request.client.host if request.client else "unknown"
    return f"anonymous_{client}"


def _resolve_run(conn, run_id: str) -> str:
    """Accept the literal ``latest`` so a caller need not track run ids.

    Handled here rather than as a separate ``/run/latest`` route because two
    routes differing only in whether a segment is literal are an ordering trap
    for whoever edits this file next.
    """
    if run_id != "latest":
        return run_id
    resolved = svc.latest_run_id(conn)
    if not resolved:
        raise HTTPException(status_code=404,
                            detail="no prioritisation run has been recorded yet")
    return resolved


@router.get("/run/{run_id}")
def run_review(run_id: str, limit: int = Query(100, ge=1, le=500),
               conn: sqlite3.Connection = Depends(get_db)):
    """One line per ticket in a run -- the post-run review screen.

    ``run_id`` may be ``latest``. Wrapped in a transaction because reading an
    explanation stores it: the text shown to an officer and the text sent to a
    citizen must be the same recorded row, not two independent renderings.
    """
    resolved = _resolve_run(conn, run_id)
    with transaction(conn):
        body = svc.explain_run(conn, resolved, limit=limit)
    if not body["explanations"]:
        raise HTTPException(status_code=404,
                            detail=f"no scored tickets for run {resolved}")
    return body


@router.get("/run/{run_id}/shap")
def run_shap(run_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """The SHAP second opinion for a whole run, or an honest refusal.

    Never a 500 and never a silent empty body: when ``scikit-learn``/``shap`` are
    not installed, or the cohort is too small for a surrogate to mean anything,
    the response says ``available: false`` and names the reason. The exact
    decomposition is unaffected either way, which the payload also states.
    """
    resolved = _resolve_run(conn, run_id)
    return svc.shap_surrogate(conn, resolved)


@router.get("/{ticket_id}")
def explain(ticket_id: str, request: Request,
            run_id: Optional[str] = Query(None, description="a specific run; "
                                                            "defaults to the "
                                                            "newest score"),
            include_shap: bool = Query(False, description="attach the SHAP "
                                                         "surrogate for this "
                                                         "ticket's cohort"),
            conn: sqlite3.Connection = Depends(get_db)):
    """The full explanation for one ticket, officer and citizen versions both.

    A ticket that exists but has never been scored is not an error: it gets
    ``scored: false`` and a sentence saying so in both languages, because "we
    have not assessed your complaint yet" is itself an answer the citizen is
    owed. Only an unknown ticket id is a 404.
    """
    resolved = _resolve_run(conn, run_id) if run_id else None
    with transaction(conn):
        body = svc.explain_ticket(conn, ticket_id, run_id=resolved,
                                  include_shap=include_shap, persist=True)
    if body is None:
        raise HTTPException(status_code=404, detail=f"no ticket {ticket_id}")
    body["requested_by"] = _actor(request)
    return body


@router.get("/{ticket_id}/citizen")
def citizen(ticket_id: str,
            lang: str = Query("en", pattern="^(en|mr)$"),
            run_id: Optional[str] = Query(None),
            conn: sqlite3.Connection = Depends(get_db)):
    """Just the paragraph that goes out to the citizen, in one language.

    This is the endpoint the WhatsApp track calls, so it is deliberately small
    and carries ``translation_status`` alongside the text: Marathi here is
    machine-drafted and awaiting council review, and any transport that forwards
    it should be able to see that without reading this docstring.
    """
    resolved = _resolve_run(conn, run_id) if run_id else None
    with transaction(conn):
        body = svc.explain_ticket(conn, ticket_id, run_id=resolved,
                                  persist=True)
    if body is None:
        raise HTTPException(status_code=404, detail=f"no ticket {ticket_id}")
    key = "citizen_message_mr" if lang == "mr" else "citizen_message_en"
    messages = body.get("citizen_messages") or {}
    detail = messages.get(lang) or {}
    return {
        "ticket_id": body["ticket_id"],
        "ref_no": body.get("ref_no"),
        "language": lang,
        "message": body.get(key),
        "outcome_sentence": detail.get("outcome_sentence"),
        "next_step": detail.get("next_step"),
        "translation_status": detail.get("translation_status")
                              or body.get("translation_status"),
        "scored": body.get("scored"),
        "decision": body.get("decision"),
        "reason_code": body.get("reason_code"),
        "run_id": body.get("run_id"),
        "dispatch_date": body.get("dispatch_date"),
    }


@router.get("/{ticket_id}/history")
def history(ticket_id: str, conn: sqlite3.Connection = Depends(get_db)):
    """Every explanation ever stored for this ticket, oldest first.

    What an RTS appeal actually tests is not today's explanation but whether the
    platform said the same thing on each earlier occasion, so nothing here is
    ever rewritten -- a re-score appends.
    """
    rows = svc.explanation_history(conn, ticket_id)
    return {"ticket_id": ticket_id, "count": len(rows), "explanations": rows}
