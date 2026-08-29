"""One day's triage run: rank the queue, plan the work, record why.

This is the module the whole brief turns on. Everything upstream of it produces
facts about single tickets; everything downstream reads a decision. Here the two
meet: several complaints compete for the same rupees and the same crew-hours, and
somebody has to choose and be able to defend the choice afterwards.

The sequence, and why each step is separate:

1. **Capacity is looked up, never assumed.** A run reads ``daily_capacity`` for
   the date (ward-specific row first, council-wide row next) and only falls back
   to the configured default if the council has entered nothing. The manifest
   records which of the three it used, because "we planned against a guess" is a
   fact a judge or an auditor is entitled to see.
2. **Criteria come from the database, not from this run.** Each ticket's C1..C4
   TFNs were derived at ingest with per-criterion evidence. A ticket missing them
   is re-derived once; a ticket that still has none is reported, not silently
   ranked as zero.
3. **Fuzzy TOPSIS produces a clean CCi** in [0, 1] from criteria and the active
   weight version alone. That number is stored as ``cci_base`` and is the only
   value the explainability endpoint decomposes, because it is the only one whose
   decomposition is exact.
4. **Urgency adjustments are applied to the *gap*, not to the score.** Repeat
   reports and a running statutory clock both raise a ticket, but neither may push
   it past a ticket that already matches the ideal profile. See
   :func:`priority_value` -- this is the deliberate part.
5. **Allocation is a two-constraint knapsack, not the ranked list.** The rank
   answers "which matters more"; the knapsack answers "what can we actually do
   today". They differ, and the difference is the point: the top-ranked ticket
   may cost the whole day and strand three near-equal ones.
6. **Everything is written append-only.** ``ticket_scores`` gains a row per
   ticket per run, ``dispatch_manifests`` one row per run, and
   ``dispatch_manifest_items`` the per-ticket decision with a reason code. A
   manifest from last Tuesday stays explainable under Tuesday's weight version
   even after the panel re-derives.

Nothing here mutates a criterion or a cost. If a number looks wrong, the fix is
upstream, and this run can be repeated to show the difference.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

if __name__ == "__main__":  # pragma: no cover
    # The self-test must never touch working data, and the database path is read
    # once when ``config`` is imported -- so it has to be redirected before any
    # first-party import below runs, not inside the test block at the bottom.
    import os
    import shutil
    import tempfile

    _SCRATCH = Path(tempfile.gettempdir()) / "crpp_triage_selftest"
    shutil.rmtree(_SCRATCH, ignore_errors=True)
    (_SCRATCH / "uploads").mkdir(parents=True, exist_ok=True)
    os.environ["CRPP_DB_PATH"] = str(_SCRATCH / "selftest.db")
    os.environ["UPLOAD_DIR"] = str(_SCRATCH / "uploads")

try:
    from config import settings
    from database import (civic_date, dumps, execute, insert, new_id, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.costing import COST_COMPLETE
    from domain.criteria import CRITERIA, CRITERIA_TYPES
    from services import dedup
    from services import tickets as ticket_service
    from services import weights as weight_service
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings
    from database import (civic_date, dumps, execute, insert, new_id, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.costing import COST_COMPLETE
    from domain.criteria import CRITERIA, CRITERIA_TYPES
    from services import dedup
    from services import tickets as ticket_service
    from services import weights as weight_service

try:
    from track1_engine.allocation import REASON_TEXT, allocate
    from track1_engine.prioritization import run_prioritization
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from track1_engine.allocation import REASON_TEXT, allocate
    from track1_engine.prioritization import run_prioritization


# How much of a ticket's remaining distance to the ideal profile repeat reports
# may close, at the community multiplier's ceiling. Deliberately below 1.0: many
# people reporting the same pothole is strong evidence that it matters, and it is
# still not evidence that it matters more than a live electrical wire.
COMMUNITY_MAX_GAP_SHARE = 0.30

# Statuses the SLA view returns that we treat as urgent. The vocabulary is the
# reference dataset's own (sla_status_logic), not one invented here: OVERDUE and
# RTS_LIMIT_REACHED are breaches, AT_RISK is the halfway warning, and
# IMMEDIATE_HANDOFF (a 0-minute target, i.e. 108/112) is breached the moment it
# is logged because any delay at all is too much.
SLA_BREACHED = ("OVERDUE", "IMMEDIATE_HANDOFF", "RTS_LIMIT_REACHED")
SLA_AT_RISK = ("AT_RISK",)

CAPACITY_SOURCE_WARD = "daily_capacity_ward_row"
CAPACITY_SOURCE_COUNCIL = "daily_capacity_council_row"
CAPACITY_SOURCE_DEFAULT = "configured_default_not_entered_by_council"


def _f(value: Any, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def today_iso() -> str:
    """The council's own calendar date, not UTC's.

    Thin wrapper over ``database.civic_date`` so the whole service layer agrees
    on what "today" means: the dispatch date on a manifest, the reference number
    on a citizen's receipt and the capacity row an officer signed for all have
    to name the same day.
    """
    return civic_date()


def resolve_capacity(conn, dispatch_date: str, ward_id: str | None = None,
                     *, budget: float | None = None,
                     workforce: float | None = None) -> dict:
    """Today's money and crew-hours, and an honest account of where they came from.

    Explicit arguments win (an officer running a what-if), then a ward row for
    the date, then the council-wide row, then the configured default. The default
    is a stand-in for a number the council has not entered, so it is labelled as
    such and ``verified`` stays False -- a plan built on it is still a real plan,
    but nobody should read its rupee figure as authoritative.
    """
    row = None
    source = CAPACITY_SOURCE_DEFAULT
    if ward_id:
        row = query_one(conn, "SELECT * FROM daily_capacity WHERE "
                              "capacity_date = ? AND ward_id = ?",
                        (dispatch_date, ward_id))
        if row is not None:
            source = CAPACITY_SOURCE_WARD
    if row is None:
        row = query_one(conn, "SELECT * FROM daily_capacity WHERE "
                              "capacity_date = ? AND ward_id IS NULL",
                        (dispatch_date,))
        if row is not None:
            source = CAPACITY_SOURCE_COUNCIL

    stored_budget = _f(row["budget_inr"], 0.0) if row is not None else 0.0
    stored_hours = _f(row["workforce_hours"], 0.0) if row is not None else 0.0
    if row is not None and (stored_budget <= 0 or stored_hours <= 0):
        # A row exists but one axis is blank; fill only the blank axis so the
        # entered number is never overwritten by a default.
        source = f"{source}_partial_filled_from_default"

    resolved_budget = (budget if budget is not None
                       else stored_budget or settings.DEFAULT_DAILY_BUDGET)
    resolved_hours = (workforce if workforce is not None
                      else stored_hours or settings.DEFAULT_DAILY_WORKFORCE_HOURS)
    if budget is not None or workforce is not None:
        source = f"{source}_overridden_by_caller"

    resources = []
    if row is not None:
        resources = [dict(r) for r in query_all(
            conn, "SELECT * FROM capacity_resources WHERE capacity_id = ? "
                  "ORDER BY resource_type", (row["id"],))]

    return {
        "capacity_date": dispatch_date,
        "ward_id": ward_id,
        "budget_inr": round(_f(resolved_budget), 2),
        "workforce_hours": round(_f(resolved_hours), 2),
        "source": source,
        "verified": bool(row is not None and row["verified_by"]),
        "verified_by": row["verified_by"] if row is not None else None,
        "capacity_id": row["id"] if row is not None else None,
        "note": (row["note"] if row is not None else
                 "no daily_capacity row for this date; used the configured "
                 "default so the run could proceed"),
        "resources": resources,
    }


def priority_value(cci_base: float, community_multiplier: float,
                   sla: dict | None) -> dict:
    """Fold repeat-report evidence and the statutory clock into one dispatch value.

    Both signals are applied to the *remaining gap* between the ticket's CCi and
    a perfect 1.0, never as a multiplier on the score and never as a raw addition:

        gap        = 1 - cci_base
        community  = COMMUNITY_MAX_GAP_SHARE x (m - 1) / (cap - 1)
        clock      = SLA_BREACH_BONUS | SLA_AT_RISK_BONUS | 0
        closed     = 1 - (1 - community)(1 - clock)
        value      = cci_base + gap x closed

    Three properties this buys, each of which a naive version loses:

    * **It stays in [0, 1).** ``cci_base * 3.0`` leaves the scale entirely and
      ``cci_base + 0.35`` can exceed 1, so neither number is comparable across
      runs or reportable to a citizen.
    * **It cannot reorder the top.** A ticket already at the ideal profile has no
      gap, so no amount of repeat reporting overtakes it. Volume is evidence, not
      a veto: twenty reports of a pothole must not outrank one live wire.
    * **It never saturates into a tie.** Clamping at 1.0 would make every urgent
      ticket equal, which is exactly the information the knapsack needs. The
      transform is strictly increasing in both signals, so the ordering survives.

    The two config numbers read as sentences: ``SLA_BREACH_BONUS = 0.35`` means a
    breached operational deadline closes 35% of a ticket's remaining distance to
    the ideal.
    """
    base = max(0.0, min(1.0, _f(cci_base)))
    cap = max(1.0 + 1e-9, _f(settings.COMMUNITY_MULTIPLIER_CAP, 3.0))
    multiplier = max(1.0, min(cap, _f(community_multiplier, 1.0)))
    community_share = COMMUNITY_MAX_GAP_SHARE * (multiplier - 1.0) / (cap - 1.0)

    status = (sla or {}).get("operational_status") or ""
    rts_status = (sla or {}).get("rts_status") or ""
    if status in SLA_BREACHED or rts_status in SLA_BREACHED:
        clock_share, clock_reason = settings.SLA_BREACH_BONUS, "deadline_breached"
    elif status in SLA_AT_RISK or rts_status in SLA_AT_RISK:
        clock_share, clock_reason = settings.SLA_AT_RISK_BONUS, "deadline_at_risk"
    else:
        clock_share, clock_reason = 0.0, "within_deadline"
    clock_share = max(0.0, min(1.0, _f(clock_share)))

    gap = 1.0 - base
    closed = 1.0 - (1.0 - community_share) * (1.0 - clock_share)
    value = base + gap * closed
    return {
        "value": round(value, 6),
        "cci_base": round(base, 6),
        "community_multiplier": round(multiplier, 4),
        "community_uplift": round(gap * community_share, 6),
        "sla_bonus": round(gap * closed - gap * community_share, 6),
        "sla_reason": clock_reason,
        "gap_closed_fraction": round(closed, 6),
    }

def load_criteria(conn, ticket_id: str) -> dict:
    """The stored C1..C4 TFNs for one ticket, keyed by criterion name."""
    rows = query_all(conn, "SELECT * FROM ticket_criteria_scores WHERE "
                           "ticket_id = ?", (ticket_id,))
    return {r["criterion"]: dict(r) for r in rows}


def build_candidates(conn, queue: Sequence[dict], *, now: Any = None,
                     rescore_missing: bool = True) -> tuple[list[dict], list[dict]]:
    """Turn ticket rows into engine input. Returns (candidates, skipped).

    A ticket is skipped only when it has no criteria at all and re-deriving fails
    -- that is a data problem to surface, not a zero to rank. Everything else,
    including a ticket whose cost nobody has estimated, stays in the run: the
    allocator has an explicit reason code for un-costed work, and dropping it here
    would make it invisible instead of deferred.
    """
    moment = now or utcnow()
    candidates: list[dict] = []
    skipped: list[dict] = []

    for row in queue:
        ticket = dict(row)
        criteria = load_criteria(conn, ticket["id"])
        if len(criteria) < len(CRITERIA) and rescore_missing:
            try:
                ticket_service.rescore_ticket(conn, ticket["id"])
            except Exception as exc:  # noqa: BLE001 - one bad row must not stop the run
                skipped.append({"id": ticket["id"], "ref_no": ticket.get("ref_no"),
                                "reason": f"rescore failed: "
                                          f"{type(exc).__name__}: {exc}"})
                continue
            criteria = load_criteria(conn, ticket["id"])
        missing = [name for name in CRITERIA if name not in criteria]
        if missing:
            skipped.append({"id": ticket["id"], "ref_no": ticket.get("ref_no"),
                            "reason": f"no derived scores for {', '.join(missing)}"})
            continue

        sla = ticket_service.sla_view(ticket, moment)
        cost_known = (ticket.get("cost_status") == COST_COMPLETE
                      and ticket.get("estimated_cost_inr") is not None
                      and ticket.get("estimated_hours") is not None)
        floor = (ticket.get("priority_floor") or "").strip().lower()
        candidates.append({
            "id": ticket["id"],
            "scores": [[criteria[name]["tfn_lower"], criteria[name]["tfn_modal"],
                        criteria[name]["tfn_upper"]] for name in CRITERIA],
            "criteria_rows": criteria,
            "ticket": ticket,
            "sla": sla,
            "cost_known": cost_known,
            "budget_cost": _f(ticket.get("estimated_cost_inr")),
            "workforce_hours": _f(ticket.get("estimated_hours")),
            # Life-safety is a floor, not a bid. A critical ticket is committed
            # before the optimisation rather than entered into it, so it can never
            # be traded against a cheaper combination.
            "mandatory": bool(settings.CRITICAL_ALWAYS_ALLOCATE
                              and floor == "critical"),
            "priority_floor": ticket.get("priority_floor"),
        })
    return candidates, skipped

def rank(conn, candidates: Sequence[dict]) -> tuple[list[dict], dict, int]:
    """Fuzzy TOPSIS, then the gap-based urgency fold. Returns (ranked, weights, ver).

    Two orderings exist here and both are kept: ``topsis_rank`` is the pure
    criteria ranking, and ``rank`` is the dispatch ranking after repeat reports and
    the statutory clock. Storing both is what lets an officer answer "why is this
    above that when its CCi is lower" without re-running anything.
    """
    weight_map, version = weight_service.active_vector(conn)
    config = {
        "names": list(CRITERIA),
        "types": [CRITERIA_TYPES[name] for name in CRITERIA],
        "weights": weight_map,
    }
    scored = run_prioritization(
        [{"id": c["id"], "scores": c["scores"]} for c in candidates], config)
    by_id = {c["id"]: c for c in candidates}

    ranked: list[dict] = []
    for entry in scored:
        candidate = by_id[entry["id"]]
        adjusted = priority_value(entry["topsis_score"],
                                  candidate["ticket"].get("community_multiplier", 1.0),
                                  candidate["sla"])
        merged = dict(candidate)
        merged.update({
            "topsis_score": entry["topsis_score"],
            "topsis_rank": entry["rank"],
            "d_positive": entry["d_positive"],
            "d_negative": entry["d_negative"],
            "attribution": entry["attribution"],
            "normalisation_notes": entry["normalisation_notes"],
            "value": adjusted["value"],
            "adjustment": adjusted,
        })
        ranked.append(merged)

    # Deterministic: two runs over the same data must produce the same manifest,
    # so ties break on ticket id rather than on dict ordering.
    ranked.sort(key=lambda r: (-_f(r["value"]), str(r["id"])))
    for position, item in enumerate(ranked, start=1):
        item["rank"] = position
    return ranked, weight_map, version

def _persist(conn, *, run_id: str, dispatch_date: str, ward_id: str | None,
             capacity: dict, weight_version: int, ranked: Sequence[dict],
             plan: dict, skipped: Sequence[dict], actor: str | None,
             weight_map: dict | None = None) -> str:
    """Write the run: scores, manifest, per-ticket decisions, ticket snapshots.

    Append-only by construction. ``ticket_scores`` never updates an existing row,
    so the score a ticket had under weight version 3 survives version 4 and a
    manifest stays explainable under the weights that produced it.
    """
    now = utcnow_iso()
    decision_by_id = {d["id"]: d for d in plan["decisions"]}

    manifest_id = new_id()
    insert(conn, "dispatch_manifests", {
        "id": manifest_id, "run_id": run_id, "dispatch_date": dispatch_date,
        "ward_id": ward_id, "weight_version": weight_version,
        "budget_available": capacity["budget_inr"],
        "workforce_available": capacity["workforce_hours"],
        "budget_used": plan["budget_used"],
        "workforce_used": plan["workforce_used"],
        "total_candidates": len(ranked),
        "allocated_count": plan["allocated_count"],
        "deferred_count": plan["deferred_count"],
        "cost_incomplete_count": plan["cost_unknown_count"],
        "solver": plan["solver"], "objective_value": plan["objective_value"],
        "budget_outcome": plan["budget_outcome"], "created_by": actor,
        "notes": dumps({
            "capacity_source": capacity["source"],
            "capacity_verified": capacity["verified"],
            "capacity_verified_by": capacity.get("verified_by"),
            # The vector, not just the version number. A reader asking "why was
            # this ticket scheduled?" a year from now should not have to hope the
            # weights table still holds version 3 unchanged.
            "weights": dict(weight_map or {}),
            "solver_optimal": plan["optimal"],
            "states_explored": plan.get("states_explored"),
            "allocator_notes": plan.get("notes") or [],
            "normalisation_notes": (ranked[0]["normalisation_notes"]
                                   if ranked else []),
            "skipped": list(skipped),
        }),
        "created_at": now,
    })

    for item in ranked:
        decision = decision_by_id.get(item["id"], {})
        adjustment = item["adjustment"]
        insert(conn, "ticket_scores", {
            "id": new_id(), "ticket_id": item["id"], "run_id": run_id,
            "weight_version": weight_version,
            "cci": adjustment["value"], "cci_base": adjustment["cci_base"],
            "community_multiplier": adjustment["community_multiplier"],
            "sla_bonus": round(adjustment["community_uplift"]
                               + adjustment["sla_bonus"], 6),
            "rank_position": item["rank"],
            "d_positive": item["d_positive"], "d_negative": item["d_negative"],
            "criteria_snapshot": dumps({
                "criteria": {name: [row["tfn_lower"], row["tfn_modal"],
                                    row["tfn_upper"]]
                             for name, row in item["criteria_rows"].items()},
                "attribution": item["attribution"],
                "adjustment": adjustment,
                "topsis_rank": item["topsis_rank"],
                "sla": item["sla"],
            }),
            "created_at": now,
        })
        insert(conn, "dispatch_manifest_items", {
            "id": new_id(), "manifest_id": manifest_id, "ticket_id": item["id"],
            "decision": decision.get("decision", "deferred"),
            "rank_position": item["rank"], "cci": adjustment["value"],
            "cost_inr": (item["budget_cost"] if item["cost_known"] else None),
            "hours": (item["workforce_hours"] if item["cost_known"] else None),
            "cost_status": item["ticket"].get("cost_status"),
            "department_id": item["ticket"].get("department_id"),
            "required_roles": item["ticket"].get("required_roles"),
            "reason_code": decision.get("reason_code"),
            "reason_text": decision.get("reason_text"),
            "created_at": now,
        })
        execute(conn, "UPDATE tickets SET latest_cci = ?, latest_rank = ?, "
                      "latest_weight_version = ?, updated_at = ? WHERE id = ?",
                (adjustment["value"], item["rank"], weight_version, now,
                 item["id"]))
        target = ("scheduled" if decision.get("decision") == "allocated"
                  else "deferred")
        moved = ticket_service.update_status(
            conn, item["id"], target, actor=actor or "triage",
            note=decision.get("reason_text"))
        if not moved.get("updated"):
            # Already in the target state, or in a state the lifecycle will not
            # let a triage run leave (dispatched, resolved). Recorded, not forced.
            dedup.record_event(conn, item["id"], "triage_decision",
                               to_value=target, actor=actor or "triage",
                               note=f"{decision.get('reason_code')}: "
                                    f"{moved.get('reason')}")
    return manifest_id

def run_triage(conn, *, dispatch_date: str | None = None,
               ward_id: str | None = None, budget: float | None = None,
               workforce: float | None = None, actor: str | None = None,
               solver: str | None = None, dry_run: bool = False,
               now: Any = None) -> dict:
    """Rank the open queue, plan today's work, and record the reasoning.

    ``dry_run=True`` computes and returns the whole plan without writing anything,
    which is what "what would happen if we had another 50,000 rupees" needs. The
    only difference in the result is ``persisted: False`` and a null manifest id.
    """
    dispatch_date = dispatch_date or today_iso()
    capacity = resolve_capacity(conn, dispatch_date, ward_id,
                               budget=budget, workforce=workforce)
    queue = ticket_service.queue_for_prioritisation(conn, ward_id)

    if not queue:
        return {
            "run_id": None, "manifest_id": None, "dispatch_date": dispatch_date,
            "ward_id": ward_id, "capacity": capacity, "weight_version": None,
            "candidates": 0, "allocated": [], "deferred": [], "skipped": [],
            "plan": None, "persisted": False,
            "message": "nothing is competing for today's capacity: no open, "
                       "scored or deferred tickets in scope",
        }

    candidates, skipped = build_candidates(conn, queue, now=now)
    if not candidates:
        return {
            "run_id": None, "manifest_id": None, "dispatch_date": dispatch_date,
            "ward_id": ward_id, "capacity": capacity, "weight_version": None,
            "candidates": 0, "allocated": [], "deferred": [],
            "skipped": skipped, "plan": None, "persisted": False,
            "message": f"{len(queue)} tickets are open but none carry derived "
                       f"criteria scores, so none can be ranked honestly",
        }

    ranked, weight_map, weight_version = rank(conn, candidates)
    plan = allocate(
        [{"id": item["id"], "budget_cost": item["budget_cost"],
          "workforce_hours": item["workforce_hours"],
          "cost_known": item["cost_known"], "mandatory": item["mandatory"],
          "value": item["value"]} for item in ranked],
        capacity["budget_inr"], capacity["workforce_hours"],
        value_key="value", solver=solver or settings.KNAPSACK_SOLVER)

    run_id = new_id()
    manifest_id = None
    if not dry_run:
        manifest_id = _persist(
            conn, run_id=run_id, dispatch_date=dispatch_date, ward_id=ward_id,
            capacity=capacity, weight_version=weight_version, ranked=ranked,
            plan=plan, skipped=skipped, actor=actor, weight_map=weight_map)

    decision_by_id = {d["id"]: d for d in plan["decisions"]}
    rows = [_decision_view(item, decision_by_id.get(item["id"], {}))
            for item in ranked]
    return {
        "run_id": run_id if not dry_run else None,
        "manifest_id": manifest_id,
        "dispatch_date": dispatch_date,
        "ward_id": ward_id,
        "capacity": capacity,
        "weight_version": weight_version,
        "weights": weight_map,
        "candidates": len(ranked),
        "allocated": [r for r in rows if r["decision"] == "allocated"],
        "deferred": [r for r in rows if r["decision"] != "allocated"],
        "skipped": skipped,
        "plan": {k: v for k, v in plan.items() if k != "decisions"},
        "persisted": not dry_run,
        "message": _run_summary(plan, capacity, weight_version, len(skipped)),
    }


def _run_summary(plan: dict, capacity: dict, weight_version: int,
                 skipped: int) -> str:
    """One sentence an officer can read out, with the caveats attached."""
    parts = [
        f"{plan['allocated_count']} of "
        f"{plan['allocated_count'] + plan['deferred_count']} tickets scheduled "
        f"using INR {plan['budget_used']:.0f} of {capacity['budget_inr']:.0f} and "
        f"{plan['workforce_used']:.1f} of {capacity['workforce_hours']:.1f} "
        f"crew-hours",
        f"weights v{weight_version}",
        f"{plan['solver']}"
        + ("" if plan["optimal"] else " (near-optimal, beam-limited)"),
    ]
    if plan["mandatory_count"]:
        parts.append(f"{plan['mandatory_count']} committed on a safety or "
                     f"statutory floor before optimisation")
    if plan["cost_unknown_count"]:
        parts.append(f"{plan['cost_unknown_count']} held back for want of a cost "
                     f"estimate")
    if capacity["source"].startswith(CAPACITY_SOURCE_DEFAULT):
        parts.append("capacity is the configured default -- the council has not "
                     "entered today's figures")
    if skipped:
        parts.append(f"{skipped} tickets could not be scored")
    return "; ".join(parts) + "."


def _decision_view(item: dict, decision: dict) -> dict:
    """One row of the manifest, as the API and the dashboard want it."""
    ticket = item["ticket"]
    adjustment = item["adjustment"]
    return {
        "ticket_id": item["id"],
        "ref_no": ticket.get("ref_no"),
        "category": ticket.get("category"),
        "ward_id": ticket.get("ward_id"),
        "lat": ticket.get("lat"), "lon": ticket.get("lon"),
        "citizen_phone": ticket.get("citizen_phone"),
        "description": ticket.get("description"),
        "status": ticket.get("status"),
        "rank": item["rank"],
        "topsis_rank": item["topsis_rank"],
        "cci_score": adjustment["value"],
        "cci_base": adjustment["cci_base"],
        "community_multiplier": adjustment["community_multiplier"],
        "report_count": ticket.get("report_count"),
        "sla_reason": adjustment["sla_reason"],
        "sla": item["sla"],
        "priority_floor": item["priority_floor"],
        "mandatory": item["mandatory"],
        "cost_status": ticket.get("cost_status"),
        "cost_known": item["cost_known"],
        "estimated_cost_inr": (item["budget_cost"] if item["cost_known"]
                               else None),
        "estimated_hours": (item["workforce_hours"] if item["cost_known"]
                            else None),
        "decision": decision.get("decision", "deferred"),
        "reason_code": decision.get("reason_code"),
        "reason_text": decision.get("reason_text"),
        "top_driver": max(item["attribution"],
                          key=lambda a: a["contribution"])["criterion"]
        if item["attribution"] else None,
        "attribution": item["attribution"],
    }

def _manifest_row(conn, *, manifest_id: str | None = None,
                  run_id: str | None = None,
                  dispatch_date: str | None = None,
                  ward_id: str | None = None) -> Any:
    """Find one manifest by id, run id, or the latest for a date."""
    if manifest_id:
        return query_one(conn, "SELECT * FROM dispatch_manifests WHERE id = ?",
                         (manifest_id,))
    if run_id:
        return query_one(conn, "SELECT * FROM dispatch_manifests WHERE "
                               "run_id = ?", (run_id,))
    clauses, params = [], []
    if dispatch_date:
        clauses.append("dispatch_date = ?")
        params.append(dispatch_date)
    if ward_id:
        clauses.append("ward_id = ?")
        params.append(ward_id)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    # Several runs a day are normal (capacity changes, a re-run after a cost was
    # entered); the newest is the one in force.
    return query_one(conn, "SELECT * FROM dispatch_manifests" + where
                     + " ORDER BY created_at DESC, rowid DESC LIMIT 1",
                     tuple(params))


def get_manifest(conn, *, manifest_id: str | None = None,
                 run_id: str | None = None, dispatch_date: str | None = None,
                 ward_id: str | None = None) -> dict | None:
    """A stored manifest with its per-ticket decisions, joined to live ticket rows.

    Reads the *recorded* decision rather than recomputing it. A manifest is a
    historical document: if the weights changed this morning, yesterday's manifest
    must still show what was actually decided and under which weight version.
    """
    row = _manifest_row(conn, manifest_id=manifest_id, run_id=run_id,
                        dispatch_date=dispatch_date, ward_id=ward_id)
    if row is None:
        return None
    manifest = dict(row)
    from database import loads  # local import keeps the module's surface small
    manifest["notes"] = loads(manifest.get("notes"), {})

    items = query_all(conn,
                      "SELECT i.*, t.ref_no, t.category, t.description, "
                      "t.citizen_phone, t.ward_id, t.lat, t.lon, t.status, "
                      "t.community_multiplier, t.report_count, t.priority_floor, "
                      "s.cci_base, s.d_positive, s.d_negative, s.criteria_snapshot "
                      "FROM dispatch_manifest_items i "
                      "JOIN tickets t ON t.id = i.ticket_id "
                      "LEFT JOIN ticket_scores s ON s.ticket_id = i.ticket_id "
                      "AND s.run_id = ? "
                      "WHERE i.manifest_id = ? ORDER BY i.rank_position",
                      (manifest["run_id"], manifest["id"]))

    rows: list[dict] = []
    for item in items:
        entry = dict(item)
        snapshot = loads(entry.pop("criteria_snapshot", None), {}) or {}
        entry["attribution"] = snapshot.get("attribution", [])
        entry["adjustment"] = snapshot.get("adjustment", {})
        entry["sla"] = snapshot.get("sla", {})
        entry["topsis_rank"] = snapshot.get("topsis_rank")
        entry["cci_score"] = entry.pop("cci", None)
        entry["top_driver"] = (max(entry["attribution"],
                                   key=lambda a: a.get("contribution", 0.0)
                                   )["criterion"]
                               if entry["attribution"] else None)
        rows.append(entry)

    manifest["scheduled"] = [r for r in rows if r["decision"] == "allocated"]
    manifest["deferred"] = [r for r in rows if r["decision"] != "allocated"]
    manifest["items"] = rows
    return manifest


def list_manifests(conn, limit: int = 30, ward_id: str | None = None) -> list[dict]:
    """Recent runs, newest first. Enough to chart capacity against demand."""
    clause, params = "", []
    if ward_id:
        clause, params = " WHERE ward_id = ?", [ward_id]
    rows = query_all(conn, "SELECT id, run_id, dispatch_date, ward_id, "
                           "weight_version, budget_available, workforce_available, "
                           "budget_used, workforce_used, total_candidates, "
                           "allocated_count, deferred_count, "
                           "cost_incomplete_count, solver, objective_value, "
                           "budget_outcome, created_by, created_at "
                           "FROM dispatch_manifests" + clause
                     + " ORDER BY created_at DESC, rowid DESC LIMIT ?",
                     (*params, int(limit)))
    return [dict(r) for r in rows]


def current_priorities(conn, *, ward_id: str | None = None,
                       limit: int = 200) -> list[dict]:
    """The live queue in dispatch order, using each ticket's latest stored score.

    Unscored tickets sort last rather than being hidden: a ticket nobody has been
    able to score yet is still a citizen waiting, and a queue that quietly omits
    it is the failure mode this whole project exists to avoid.
    """
    clauses = ["is_duplicate = 0",
               "status IN ('open', 'scored', 'scheduled', 'deferred')"]
    params: list[Any] = []
    if ward_id:
        clauses.append("ward_id = ?")
        params.append(ward_id)
    rows = query_all(conn, "SELECT * FROM tickets WHERE "
                     + " AND ".join(clauses)
                     + " ORDER BY latest_cci IS NULL, latest_cci DESC, "
                       "reported_at LIMIT ?", (*params, int(limit)))
    return [dict(r) for r in rows]

def set_capacity(conn, *, capacity_date: str | None = None,
                 ward_id: str | None = None, budget_inr: float | None = None,
                 workforce_hours: float | None = None,
                 verified_by: str | None = None, note: str | None = None,
                 resources: Iterable[dict] | None = None,
                 actor: str | None = None) -> dict:
    """Record what the council actually has today. Upsert on (date, ward).

    ``verified_by`` is the difference between a number an officer stands behind and
    a number someone typed. It is stored, surfaced in every manifest built on it,
    and never inferred -- passing it means a named person is accountable for the
    figure.
    """
    capacity_date = capacity_date or today_iso()
    now = utcnow_iso()
    existing = query_one(conn, "SELECT * FROM daily_capacity WHERE "
                               "capacity_date = ? AND ward_id IS ?",
                         (capacity_date, ward_id))
    if existing is None:
        capacity_id = new_id()
        insert(conn, "daily_capacity", {
            "id": capacity_id, "capacity_date": capacity_date,
            "ward_id": ward_id, "budget_inr": budget_inr,
            "workforce_hours": workforce_hours, "verified_by": verified_by,
            "verified_at": now if verified_by else None,
            "source": "operator_entered", "note": note,
            "created_at": now, "updated_at": now,
        })
    else:
        capacity_id = existing["id"]
        changes = {"updated_at": now}
        if budget_inr is not None:
            changes["budget_inr"] = budget_inr
        if workforce_hours is not None:
            changes["workforce_hours"] = workforce_hours
        if note is not None:
            changes["note"] = note
        if verified_by:
            changes["verified_by"] = verified_by
            changes["verified_at"] = now
        sets = ", ".join(f"{k} = ?" for k in changes)
        execute(conn, f"UPDATE daily_capacity SET {sets} WHERE id = ?",
                (*changes.values(), capacity_id))

    for resource in resources or []:
        quantity = resource.get("available_now")
        execute(conn,
                "INSERT INTO capacity_resources(id, capacity_id, resource_type, "
                "display_name, available_now, quantity_known, hourly_rate_inr, "
                "rate_source, note) VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(capacity_id, resource_type) DO UPDATE SET "
                "display_name = excluded.display_name, "
                "available_now = excluded.available_now, "
                "quantity_known = excluded.quantity_known, "
                "hourly_rate_inr = excluded.hourly_rate_inr, "
                "rate_source = excluded.rate_source, note = excluded.note",
                (new_id(), capacity_id, resource["resource_type"],
                 resource.get("display_name"), quantity,
                 1 if quantity is not None else 0,
                 resource.get("hourly_rate_inr"), resource.get("rate_source"),
                 resource.get("note")))

    return resolve_capacity(conn, capacity_date, ward_id)
if __name__ == "__main__":  # pragma: no cover
    import json

    from database import get_conn, init_db

    init_db()

    # --- the urgency fold, checked directly -----------------------------------
    # Freshly logged tickets are all ON_TRACK with a multiplier of 1.0, so a
    # pipeline run never exercises this. These are the properties the fold is
    # supposed to guarantee, asserted rather than assumed.
    cap = settings.COMMUNITY_MULTIPLIER_CAP
    quiet = priority_value(0.50, 1.0, {"operational_status": "ON_TRACK"})
    crowded = priority_value(0.50, cap, {"operational_status": "ON_TRACK"})
    late = priority_value(0.50, 1.0, {"operational_status": "OVERDUE"})
    both = priority_value(0.50, cap, {"operational_status": "OVERDUE"})
    ideal_late = priority_value(1.0, cap, {"operational_status": "OVERDUE"})
    handoff = priority_value(0.50, 1.0,
                             {"operational_status": "IMMEDIATE_HANDOFF"})
    rts = priority_value(0.50, 1.0, {"operational_status": "ON_TRACK",
                                     "rts_status": "RTS_LIMIT_REACHED"})

    print("urgency fold on a CCi of 0.5000:")
    for label, out in (("nothing special", quiet),
                       (f"{cap:g}x repeat reports", crowded),
                       ("deadline breached", late),
                       ("both", both),
                       ("108/112 immediate handoff", handoff),
                       ("RTS statutory limit reached", rts)):
        print(f"   {label:<28} -> {out['value']:.4f}   ({out['sla_reason']})")

    assert quiet["value"] == 0.50, quiet
    assert crowded["value"] > quiet["value"] and crowded["value"] < 1.0
    assert late["value"] > quiet["value"]
    assert both["value"] > max(crowded["value"], late["value"]) < 1.0
    # A ticket already at the ideal profile has no gap, so volume and the clock
    # cannot lift it -- and equally cannot push it out of range.
    assert ideal_late["value"] == 1.0, ideal_late
    # Everything stays in range no matter how the signals combine.
    for m in (1.0, 1.5, cap, cap * 10):
        for status in ("ON_TRACK", "AT_RISK", "OVERDUE", "IMMEDIATE_HANDOFF",
                       "TARGET_UNDEFINED"):
            for base in (0.0, 0.25, 0.9999, 1.0):
                out = priority_value(base, m, {"operational_status": status})
                assert base <= out["value"] <= 1.0, (base, m, status, out)
    print("   bounded in [cci_base, 1], monotone in both signals  OK\n")

    with get_conn() as conn:
        made = []
        cases = [
            ("live electrical wire down across the lane", "road_damage",
             "Ward-4", 19.8811, 74.4785, {"sensitive_site": "hospital",
                                          "affected_population": 2400}),
            ("drain blocked, sewage on the street", "drain_blockage",
             "Ward-4", 19.8830, 74.4800, {"affected_population": 900}),
            ("pothole on the approach road", "road_damage",
             "Ward-9", 19.8600, 74.4700, {"affected_population": 200}),
            ("street light out near the school", "streetlight_failure",
             "Ward-9", 19.8620, 74.4720, {"sensitive_site": "school",
                                          "affected_population": 400}),
            ("water not coming since morning", "water_distribution_failure",
             "Ward-2", 19.8700, 74.4600, {"affected_population": 1500}),
        ]
        for i, (desc, category, ward, lat, lon, extra) in enumerate(cases):
            payload = {"citizen_phone": f"90000000{i:02d}", "category": category,
                       "description": desc, "ward_id": ward, "lat": lat,
                       "lon": lon, **extra}
            made.append(ticket_service.create_ticket(conn, payload, [],
                                                     actor="selftest"))
        print(f"ingested {len(made)} tickets\n")

        # Give three of them a real cost so the knapsack has something to weigh.
        # These are the fields the cost engine says only an operator can know --
        # a category with a "runtime" cost method stays COST_INCOMPLETE until a
        # human enters them, which is the behaviour being exercised here.
        for entry, cost, hours in zip(made, (18_000, 9_000, 4_500, None, None),
                                      (9.0, 5.0, 3.0, None, None)):
            if cost is None:
                continue
            ticket_service.update_cost_inputs(
                conn, entry["ticket_id"],
                {"runtime_material_cost": cost * 0.55,
                 "runtime_labour_cost": cost * 0.30,
                 "runtime_vehicle_cost": cost * 0.15,
                 "crew_hours": hours},
                actor="selftest")

        capacity = set_capacity(conn, budget_inr=25_000, workforce_hours=18,
                                verified_by="ward_engineer_selftest",
                                note="self-test figures",
                                resources=[{"resource_type": "jetting_machine",
                                            "available_now": 1,
                                            "hourly_rate_inr": 900.0,
                                            "rate_source": "selftest"}])
        print("capacity:", capacity["budget_inr"], "INR /",
              capacity["workforce_hours"], "h  source:", capacity["source"],
              " verified:", capacity["verified"])

        result = run_triage(conn, actor="selftest")
        print("\n" + result["message"] + "\n")
        print(f"{'rank':<5}{'ref':<18}{'CCi':<9}{'base':<9}{'x':<6}"
              f"{'decision':<11}reason")
        for row in sorted(result["allocated"] + result["deferred"],
                          key=lambda r: r["rank"]):
            print(f"{row['rank']:<5}{str(row['ref_no']):<18}"
                  f"{row['cci_score']:<9.4f}{row['cci_base']:<9.4f}"
                  f"{row['community_multiplier']:<6.2f}{row['decision']:<11}"
                  f"{row['reason_code']}")

        assert result["persisted"] and result["manifest_id"]
        assert result["candidates"] == len(made), (result["candidates"], len(made))

        # Every ticket must carry a reason. A queue position without a reason is
        # the thing that makes citizens distrust the queue.
        decided = result["allocated"] + result["deferred"]
        assert all(r["reason_code"] and r["reason_text"] for r in decided)
        assert len(decided) == result["candidates"]

        # The exact decomposition must still sum to the pure TOPSIS score. The
        # tolerance is 1e-5 rather than 1e-9 only because each contribution is
        # rounded to 6 decimals for storage; the underlying identity is exact.
        for row in decided:
            total = sum(a["contribution"] for a in row["attribution"])
            assert abs(total - row["cci_base"]) < 1e-5, (row["ref_no"], total,
                                                         row["cci_base"])
        print("\nattribution sums to cci_base for all "
              f"{len(decided)} tickets  OK")

        # Urgency folding must stay inside [0, 1) and never fall below the base.
        for row in decided:
            assert row["cci_base"] <= row["cci_score"] < 1.0, row
        print("priority value stays in [cci_base, 1) for all tickets  OK")

        stored = get_manifest(conn, manifest_id=result["manifest_id"])
        assert stored is not None
        assert len(stored["items"]) == result["candidates"]
        assert (len(stored["scheduled"]) == len(result["allocated"])), (
            len(stored["scheduled"]), len(result["allocated"]))
        print(f"stored manifest re-reads {len(stored['items'])} decisions, "
              f"{len(stored['scheduled'])} scheduled, solver "
              f"{stored['solver']}, outcome {stored['budget_outcome']}  OK")

        # Re-reading by date must find the same run.
        by_date = get_manifest(conn, dispatch_date=result["dispatch_date"])
        assert by_date and by_date["id"] == stored["id"]

        # A dry run must change nothing.
        before = query_one(conn, "SELECT COUNT(*) AS n FROM dispatch_manifests")["n"]
        what_if = run_triage(conn, budget=200_000, workforce=200,
                            actor="selftest", dry_run=True)
        after = query_one(conn, "SELECT COUNT(*) AS n FROM dispatch_manifests")["n"]
        assert before == after and not what_if["persisted"]
        print(f"\ndry run with INR 200000/200h -> "
              f"{what_if['plan']['allocated_count']} allocated "
              f"(vs {result['plan']['allocated_count']} at real capacity), "
              f"nothing written  OK")

        # Append-only history: a second real run adds rows, never replaces them.
        second = run_triage(conn, actor="selftest")
        scores = query_one(conn, "SELECT COUNT(*) AS n, COUNT(DISTINCT run_id) "
                                 "AS runs FROM ticket_scores")
        assert scores["runs"] == 2, dict(scores)
        print(f"second run: {scores['n']} score rows across {scores['runs']} "
              f"runs, history intact  OK")

        priorities = current_priorities(conn)
        assert len(priorities) == len(made)
        print(f"\nlive queue: {len(priorities)} tickets, top is "
              f"{priorities[0]['ref_no']} at CCi "
              f"{priorities[0]['latest_cci']:.4f} ({priorities[0]['status']})")

        print("\ncapacity provenance recorded in the manifest:")
        print("   " + json.dumps({k: stored["notes"].get(k) for k in
                                  ("capacity_source", "capacity_verified",
                                   "solver_optimal")}))
        print("\nself-test passed.")
