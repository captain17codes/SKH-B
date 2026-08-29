"""Per-department view of today's scheduled work -- and an honest blank where the
headcount should be.

This module exists because `/staff-allocation` was the one screen with nothing
behind it. The Stitch design asks for crew manifests, man-hours deployed and live
deployment; this backend has no crew, roster or attendance table, and the source
dataset explicitly refuses to supply one -- `runtime_fields_required.
do_not_prepopulate_without_authoritative_data` lists "live headcount", "vehicles
available today", "current shift attendance" and "exact dispatch cost".

So this answers the question it *can* answer. Join today's scheduled tickets to
the 15-row `incident_compatibility_matrix`, and report per department: which
tickets land on it, the union of the roles those tickets require, the summed
hours, and the ticket count. Headcount stays `null` with
`headcount_status: "operator_entered_not_yet_verified"` until an officer records a
real number, exactly as ward population already works.

Two refusals are deliberate:

* **No staffing shortfall is computed.** Hours-per-department against a headcount
  we do not have would be a made-up number wearing a percentage sign, and this is
  the specific failure the whole project is built to avoid.
* **A ticket whose category has no matrix row is not dropped.** It comes back
  under `unmapped`, naming the category, because "we scheduled work we cannot
  assign to a department" is a finding an officer needs, not a rounding error.

Headcount is stored in `app_meta` under `staff_headcount:<DEPARTMENT_ID>` rather
than in a new table: seven operator-entered integers do not justify a schema
change, and `app_meta` is already the key/value store for exactly this.
"""
from __future__ import annotations

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (civic_date, dumps, execute, loads,  # noqa: E402
                      query_all, utcnow_iso)
from domain.reference import get_reference  # noqa: E402
from services import prioritisation as triage  # noqa: E402

HEADCOUNT_KEY_PREFIX = "staff_headcount:"

STATUS_UNVERIFIED = "operator_entered_not_yet_verified"
STATUS_NOT_ENTERED = "not_entered"

HEADCOUNT_CAVEAT = (
    "Headcount is not in any dataset this platform holds. The source workforce "
    "matrix lists live headcount, vehicles available today and current shift "
    "attendance under do_not_prepopulate_without_authoritative_data, so it stays "
    "null until an officer records it. A null here means 'not entered', never zero."
)


def _headcount_key(department_id: str) -> str:
    return f"{HEADCOUNT_KEY_PREFIX}{str(department_id).strip().upper()}"


def read_headcounts(conn) -> dict[str, dict]:
    """Every headcount an officer has recorded, keyed by department_id."""
    rows = query_all(conn, "SELECT key, value FROM app_meta WHERE key LIKE ?",
                     (f"{HEADCOUNT_KEY_PREFIX}%",))
    out: dict[str, dict] = {}
    for row in rows:
        entry = loads(row["value"], {}) or {}
        out[row["key"][len(HEADCOUNT_KEY_PREFIX):]] = entry
    return out


def set_headcount(conn, department_id: str, headcount: int, *,
                  verified_by: str | None = None, note: str | None = None) -> dict:
    """Record an officer-entered headcount for one department.

    Refuses an unknown department rather than creating a row for a typo, and
    refuses a negative number. Zero is allowed and meaningful -- "this department
    has nobody on shift today" is a real answer, and a different one from null.
    """
    ref = get_reference()
    known = {str(k).upper() for k in ref.departments}
    dept = str(department_id).strip().upper()
    if dept not in known:
        return {"stored": False,
                "reason": f"{department_id!r} is not one of the "
                          f"{len(known)} departments in the workforce matrix",
                "known_departments": sorted(known)}
    if headcount is None or int(headcount) < 0:
        return {"stored": False,
                "reason": "headcount must be zero or more; use null (by not "
                          "recording one) to mean 'not entered'"}

    entry = {
        "headcount": int(headcount),
        "headcount_status": STATUS_UNVERIFIED,
        "verified_by": verified_by,
        "recorded_at": utcnow_iso(),
        "note": note,
    }
    execute(conn, "INSERT INTO app_meta(key, value) VALUES(?, ?) "
                  "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (_headcount_key(dept), dumps(entry)))
    return {"stored": True, "department_id": dept, **entry}


def _matrix_rows() -> dict[str, dict]:
    """`incident_compatibility_matrix` keyed by incident_type.

    Read from the raw dataset rather than from `IncidentSpec`, because "has a row
    in the matrix" is exactly the question `unmapped` answers, and `IncidentSpec`
    back-fills roles from the cost rules -- which would hide the gap.
    """
    raw = get_reference().raw.get("workforce", {})
    return {row["incident_type"]: row
            for row in raw.get("incident_compatibility_matrix", [])
            if row.get("incident_type")}


def plan(conn, *, dispatch_date: str | None = None,
         manifest_id: str | None = None) -> dict:
    """Today's scheduled work grouped by the department that would perform it.

    Reads the *recorded* manifest, not a fresh computation: this is the crew view
    of a decision already taken, and it must not silently disagree with the
    allocation page. Returns `manifest_found: False` with an empty plan when no
    manifest exists for the date -- "triage has not been run yet" is a normal
    state, not a fault.
    """
    date = dispatch_date or civic_date()
    manifest = triage.get_manifest(conn, manifest_id=manifest_id,
                                   dispatch_date=None if manifest_id else date)
    ref = get_reference()
    matrix = _matrix_rows()
    recorded = read_headcounts(conn)

    if manifest is None:
        return {
            "dispatch_date": date, "manifest_found": False, "manifest_id": None,
            "scheduled_tickets": 0, "total_hours": 0.0,
            "departments": [], "unmapped": [],
            "headcount_caveat": HEADCOUNT_CAVEAT,
            "message": (f"no dispatch manifest exists for {date}, so there is no "
                        f"scheduled work to assign to a department yet"),
        }

    groups: dict[str, dict] = {}
    unmapped: dict[str, dict] = {}

    for item in manifest["scheduled"]:
        category = ref.canonical_category(item.get("category"))
        row = matrix.get(category)
        hours = float(item.get("hours") or 0.0)
        entry = {
            "ticket_id": item["ticket_id"],
            "ref_no": item.get("ref_no"),
            "category": category,
            "ward_id": item.get("ward_id"),
            "rank_position": item.get("rank_position"),
            "cci_score": item.get("cci_score"),
            "hours_estimate": float(item["hours"]) if item.get("hours") is not None
                              else None,
            "cost_inr": item.get("cost_inr"),
            "cost_status": item.get("cost_status"),
            "required_roles": (list(row.get("required_roles") or []) if row
                               else loads(item.get("required_roles"), []) or []),
            "priority_notes": (row or {}).get("priority_notes"),
        }

        if row is None:
            bucket = unmapped.setdefault(category, {
                "category": category,
                "reason": "no row in incident_compatibility_matrix",
                "department_id_from_manifest": item.get("department_id"),
                "tickets": [], "ticket_count": 0, "total_hours": 0.0,
            })
            bucket["tickets"].append(entry)
            bucket["ticket_count"] += 1
            bucket["total_hours"] = round(bucket["total_hours"] + hours, 2)
            continue

        dept_id = row.get("department_id") or item.get("department_id") or "UNKNOWN"
        group = groups.setdefault(dept_id, {
            "department_id": dept_id,
            "department_name": (ref.departments.get(dept_id, {}) or {}).get("name"),
            "capabilities": list((ref.departments.get(dept_id, {}) or {})
                                 .get("capabilities") or []),
            "roster_roles": list((ref.departments.get(dept_id, {}) or {})
                                 .get("roles") or []),
            "required_roles": [],
            "optional_roles": [],
            "ticket_count": 0,
            "total_hours": 0.0,
            "hours_known_for": 0,
            "hours_unknown_for": 0,
            "total_cost_inr": 0.0,
            "categories": [],
            "tickets": [],
        })
        group["tickets"].append(entry)
        group["ticket_count"] += 1
        group["total_hours"] = round(group["total_hours"] + hours, 2)
        if item.get("hours") is None:
            group["hours_unknown_for"] += 1
        else:
            group["hours_known_for"] += 1
        if item.get("cost_inr") is not None:
            group["total_cost_inr"] = round(
                group["total_cost_inr"] + float(item["cost_inr"]), 2)
        for role in entry["required_roles"]:
            if role not in group["required_roles"]:
                group["required_roles"].append(role)
        for role in (row.get("optional_roles") or []):
            if role not in group["optional_roles"]:
                group["optional_roles"].append(role)
        if category not in group["categories"]:
            group["categories"].append(category)

    departments = []
    for dept_id, group in groups.items():
        entry = recorded.get(dept_id) or {}
        headcount = entry.get("headcount")
        departments.append({
            **group,
            "headcount": headcount,
            "headcount_status": (entry.get("headcount_status") if headcount
                                 is not None else STATUS_NOT_ENTERED),
            "headcount_verified_by": entry.get("verified_by"),
            "headcount_recorded_at": entry.get("recorded_at"),
            # Deliberately absent: any shortfall, utilisation or coverage
            # percentage. See HEADCOUNT_CAVEAT -- there is no denominator.
            "roles_needed_count": len(group["required_roles"]),
        })
    departments.sort(key=lambda d: (-d["total_hours"], d["department_id"]))

    total_hours = round(sum(d["total_hours"] for d in departments)
                        + sum(u["total_hours"] for u in unmapped.values()), 2)
    scheduled = len(manifest["scheduled"])

    return {
        "dispatch_date": manifest.get("dispatch_date", date),
        "manifest_found": True,
        "manifest_id": manifest["id"],
        "run_id": manifest.get("run_id"),
        "solver": manifest.get("solver"),
        "budget_outcome": manifest.get("budget_outcome"),
        "workforce_cap_hours": manifest.get("workforce_available"),
        "workforce_used_hours": manifest.get("workforce_used"),
        "scheduled_tickets": scheduled,
        "total_hours": total_hours,
        "departments": departments,
        "department_count": len(departments),
        "unmapped": sorted(unmapped.values(), key=lambda u: u["category"]),
        "unmapped_ticket_count": sum(u["ticket_count"]
                                     for u in unmapped.values()),
        "matrix_rows": len(matrix),
        "known_departments": [
            {"department_id": did, "name": (row or {}).get("name")}
            for did, row in sorted(ref.departments.items())
        ],
        "headcount_caveat": HEADCOUNT_CAVEAT,
        "message": (f"{scheduled} scheduled ticket(s) for "
                    f"{manifest.get('dispatch_date', date)} across "
                    f"{len(departments)} department(s), {total_hours} crew-hour(s) "
                    f"of estimated work"),
    }
