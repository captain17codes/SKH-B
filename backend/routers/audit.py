"""Audit-chain HTTP surface: what `/compliance` reads.

Everything here is a read except nothing -- there is no write endpoint, by
design. Audit rows are written only as a side effect of the act being audited, in
the same transaction. An endpoint that let a caller append an arbitrary audit row
would make the log a place where anyone can put anything, which is the opposite
of the property the chain exists to provide.

`verify` returns 200 on a broken chain. That is deliberate: a tampered log is a
finding for an officer to read, not a server fault, and a 500 would tell the UI
to render an error page instead of the one thing it most needs to display.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from services import audit as svc  # noqa: E402

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/verify")
def verify(conn: sqlite3.Connection = Depends(get_db)):
    """Recompute the whole chain and report the first entry that breaks it.

    On success: `ok: true`, the entry count, and `tip_hash`. On tamper:
    `ok: false`, `first_broken_seq`, and a `break_type` of `content` (a row was
    edited) or `link` (a row was inserted or removed). Both carry a `reason`
    written to be read aloud.
    """
    return svc.verify(conn)


@router.get("/stats")
def stats(conn: sqlite3.Connection = Depends(get_db)):
    """Entry counts per action and the chain's time span."""
    return svc.stats(conn)


@router.get("/recent")
def recent(limit: int = Query(50, ge=1, le=500),
           action: Optional[str] = Query(None, description="filter to one "
                                                          "action, e.g. triage.run"),
           conn: sqlite3.Connection = Depends(get_db)):
    """Newest entries first. An empty list is a normal answer on a fresh install."""
    entries = svc.recent(conn, limit, action=action)
    return {"count": len(entries), "limit": limit, "action": action,
            "entries": entries}


@router.get("/entity/{entity_type}/{entity_id}")
def entity_history(entity_type: str, entity_id: str,
                   limit: int = Query(200, ge=1, le=1000),
                   conn: sqlite3.Connection = Depends(get_db)):
    """Everything recorded against one thing, oldest first.

    Returns an empty list rather than 404 for a thing with no entries yet: "this
    ticket has no audit history" is a true and useful answer, and a 404 would
    make the UI render it as a fault.
    """
    entries = svc.for_entity(conn, entity_type, entity_id, limit)
    return {"entity_type": entity_type, "entity_id": entity_id,
            "count": len(entries), "entries": entries,
            "known_entity_types": [svc.ENTITY_TICKET, svc.ENTITY_MANIFEST,
                                   svc.ENTITY_WEIGHTS, svc.ENTITY_EXPLANATION]}


@router.get("/export")
def export(ticket_id: str = Query(..., description="ticket id or ref_no"),
           limit: int = Query(500, ge=1, le=2000),
           conn: sqlite3.Connection = Depends(get_db)):
    """Every entry mentioning one ticket, for an RTS reply or an appeal.

    Accepts a ref_no as well as an id, because that is what a citizen quotes.
    404s only when no such ticket exists -- a real ticket with no entries yet
    returns an empty export, which is a different and honest answer.
    """
    result = svc.export_for_ticket(conn, ticket_id, limit)
    if not result["ticket_found"]:
        raise HTTPException(status_code=404,
                            detail=f"no ticket matches {ticket_id!r} by id or "
                                   f"ref_no, so there is nothing to export")
    return result
