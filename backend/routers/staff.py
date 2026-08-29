"""Staff allocation: today's scheduled work per department, and a blank headcount.

The page this serves shows crew manifests and man-hours. It cannot show live
deployment, because no dataset here holds a roster or an attendance sheet -- see
`services/staff.py` for why that blank is deliberate rather than unfinished.

`PUT /headcount` is the only write, and it is an operator claim, not a fact: the
stored row keeps `headcount_status: operator_entered_not_yet_verified` and the
name of whoever entered it, so a reviewer can see the number's provenance rather
than inheriting it as ground truth.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, transaction  # noqa: E402
from services import staff as svc  # noqa: E402

router = APIRouter(prefix="/api/staff", tags=["staff"])


def _actor(request: Request) -> str:
    """Whoever is making the claim, or an honest stand-in for 'we do not know'."""
    user = getattr(getattr(request, "state", None), "user", None)
    if isinstance(user, dict):
        return str(user.get("username") or user.get("id") or "authenticated_user")
    client = getattr(getattr(request, "client", None), "host", None) or "unknown"
    return f"anonymous_{client}"


@router.get("/plan")
def get_plan(dispatch_date: Optional[str] = Query(
                 None, description="YYYY-MM-DD in the council's timezone; "
                                   "defaults to today"),
             manifest_id: Optional[str] = Query(
                 None, description="a specific manifest, overriding the date"),
             conn: sqlite3.Connection = Depends(get_db)):
    """Scheduled tickets grouped by the department that would perform them.

    Returns 200 with `manifest_found: false` and empty groups when triage has not
    been run for the date -- that is a normal morning state, and a 404 would make
    the page render it as a failure.

    Read `headcount: null` as "not entered", never as zero, and note that no
    shortfall or utilisation figure is returned: there is no verified denominator
    to compute one from.
    """
    return svc.plan(conn, dispatch_date=dispatch_date, manifest_id=manifest_id)


@router.put("/headcount")
def put_headcount(request: Request,
                  department_id: str = Body(..., embed=True),
                  headcount: int = Body(..., embed=True),
                  note: Optional[str] = Body(None, embed=True),
                  conn: sqlite3.Connection = Depends(get_db)):
    """Record an officer-entered headcount for one department.

    Zero is accepted and is not the same as null: "nobody is on shift today" is a
    real answer. 400 on an unknown department rather than storing a typo, and on a
    negative number.
    """
    with transaction(conn):
        result = svc.set_headcount(conn, department_id, headcount,
                                   verified_by=_actor(request), note=note)
    if not result.get("stored"):
        raise HTTPException(status_code=400, detail=result)
    return result


@router.get("/headcount")
def get_headcount(conn: sqlite3.Connection = Depends(get_db)):
    """Every headcount recorded so far, plus which departments still have none."""
    recorded = svc.read_headcounts(conn)
    from domain.reference import get_reference

    departments = get_reference().departments
    return {
        "recorded": [{"department_id": did, **entry}
                     for did, entry in sorted(recorded.items())],
        "not_entered": sorted(did for did in departments if did not in recorded),
        "headcount_status_meaning": {
            svc.STATUS_UNVERIFIED: "an officer typed this; nobody has checked it "
                                   "against an attendance record",
            svc.STATUS_NOT_ENTERED: "no number has been recorded; treat as unknown",
        },
        "caveat": svc.HEADCOUNT_CAVEAT,
    }
