"""Ticket ingestion, scoring and read models.

This is the module the routers delegate to. It is deliberately importable
without FastAPI so the whole ingest path can be exercised from a script.

What happens to one incoming report, in order:

1. the free-text category is mapped to a canonical incident type from the
   council's SLA matrix (the React form still posts ``pothole``, ``sanitation``
   and friends, and those slugs keep working);
2. the ward is resolved -- or honestly recorded as unresolved;
3. **two** deadlines are computed and never merged: the operational response
   target in minutes, and, only when the category maps to a notified Right to
   Service entry, the statutory limit in days;
4. photos are hashed, then the report is compared against the recent window --
   duplicate, recurrence or genuinely new;
5. cost is estimated with per-line provenance, unknown lines staying NULL;
6. the four criteria are derived as fuzzy intervals whose width is the
   platform's admission of what it does not know, and stored per criterion.

Ranking itself is *not* done here. Scoring one ticket in isolation would be a
severity label; the whole point is that a ticket's position depends on what else
is competing for the same crew today, which is the triage service's job.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

try:
    from config import settings
    from database import (dumps, execute, loads, new_id, parse_iso, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.costing import estimate_cost
    from domain.criteria import CRITERIA, derive_criteria
    from domain.reference import get_reference
    from services import dedup, wards
    from services.imaging import ImageUnreadable, hash_pair_from_bytes
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings
    from database import (dumps, execute, loads, new_id, parse_iso, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.costing import estimate_cost
    from domain.criteria import CRITERIA, derive_criteria
    from domain.reference import get_reference
    from services import dedup, wards
    from services.imaging import ImageUnreadable, hash_pair_from_bytes

OPEN_STATUSES = ("open", "scored", "scheduled", "deferred", "dispatched")


ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}


def generate_ref_no(conn, when: str | None = None) -> str:
    """Human-quotable reference: ``KMC-20260829-0007``.

    Citizens read this number out on the phone, so it has to be short and
    date-ordered rather than a UUID.
    """
    day = (parse_iso(when) or utcnow()).strftime("%Y%m%d")
    row = query_one(conn, "SELECT COUNT(*) AS n FROM tickets WHERE ref_no LIKE ?",
                    (f"KMC-{day}-%",))
    seq = int(row["n"] if row else 0) + 1
    for _ in range(50):
        candidate = f"KMC-{day}-{seq:04d}"
        if not query_one(conn, "SELECT 1 FROM tickets WHERE ref_no = ?",
                         (candidate,)):
            return candidate
        seq += 1
    return f"KMC-{day}-{new_id()[:6].upper()}"


def compute_deadlines(spec, reported_at: str) -> dict:
    """The two clocks, kept apart.

    Collapsing them is the single most tempting mistake in this domain: an
    operational target of 60 *minutes* and a statutory Right to Service limit of
    7 *days* answer different questions and breaching them has different
    consequences. A category with no published target gets NULL, not a guess.
    """
    start = parse_iso(reported_at) or utcnow()
    out: dict[str, Any] = {
        "operational_target_minutes": spec.response_target_minutes,
        "operational_deadline_at": None,
        "is_statutory_rts": 1 if spec.is_statutory_rts else 0,
        "rts_service_id": spec.related_rts_service_id,
        "rts_time_limit_days": spec.related_rts_days,
        "rts_deadline_at": None,
    }
    if spec.response_target_minutes is not None:
        out["operational_deadline_at"] = (
            start + timedelta(minutes=float(spec.response_target_minutes))
        ).isoformat().replace("+00:00", "Z")
    if spec.related_rts_days:
        out["rts_deadline_at"] = (
            start + timedelta(days=int(spec.related_rts_days))
        ).isoformat().replace("+00:00", "Z")
    return out


def _safe_name(filename: str | None) -> str:
    stem = Path(str(filename or "photo.jpg")).name
    cleaned = "".join(ch for ch in stem if ch.isalnum() or ch in "._-")
    return cleaned[-80:] or "photo.jpg"


def save_media(conn, ticket_id: str, uploads: list[dict]) -> dict:
    """Persist uploaded photos and their perceptual hashes.

    A photo that cannot be decoded is still stored with ``phash = NULL``. Losing
    the file because the hash failed would destroy the only evidence attached to
    a citizen's complaint; a NULL hash simply means this report cannot take part
    in image-based deduplication, and that is recorded.
    """
    saved, warnings, hashes = [], [], []
    limit_bytes = int(settings.MAX_UPLOAD_SIZE_MB) * 1024 * 1024
    target_dir = Path(settings.UPLOAD_DIR) / ticket_id
    for upload in uploads or []:
        content = upload.get("content") or b""
        name = _safe_name(upload.get("filename"))
        if not content:
            warnings.append(f"{name}: empty upload ignored")
            continue
        if len(content) > limit_bytes:
            warnings.append(f"{name}: larger than {settings.MAX_UPLOAD_SIZE_MB} MB, rejected")
            continue
        suffix = Path(name).suffix.lower()
        if suffix and suffix not in ALLOWED_IMAGE_SUFFIXES:
            warnings.append(f"{name}: unsupported image type {suffix}, rejected")
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{new_id()[:8]}_{name}"
        path.write_bytes(content)
        info: dict[str, Any] = {"phash": None, "ahash": None, "hash_bits": None}
        try:
            info = hash_pair_from_bytes(content)
            hashes.append(info["phash"])
        except ImageUnreadable as exc:
            warnings.append(f"{name}: stored but not hashable ({exc})")
        execute(conn,
                "INSERT INTO ticket_media(id, ticket_id, file_path, media_type,"
                " phash, phash_bits, size_bytes, created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (new_id(), ticket_id, str(path), "image", info.get("phash"),
                 info.get("hash_bits"), len(content), utcnow_iso()))
        saved.append({"file_path": str(path), "phash": info.get("phash"),
                      "size_bytes": len(content)})
    return {"saved": saved, "phash_list": hashes, "warnings": warnings}


def persist_criteria(conn, ticket_id: str, derived: dict) -> None:
    """Write one row per criterion, replacing any previous derivation.

    Overwriting is correct here because the *current* criteria are a function of
    the current facts; the historical record that matters for an audit is the
    score snapshot taken at each prioritisation run, which is append-only.
    """
    now = utcnow_iso()
    for name in CRITERIA:
        part = derived["scores"][name]
        execute(conn,
                "INSERT INTO ticket_criteria_scores(id, ticket_id, criterion,"
                " tfn_lower, tfn_modal, tfn_upper, confidence, source,"
                " evidence, created_at) VALUES(?,?,?,?,?,?,?,?,?,?)"
                " ON CONFLICT(ticket_id, criterion) DO UPDATE SET"
                " tfn_lower=excluded.tfn_lower, tfn_modal=excluded.tfn_modal,"
                " tfn_upper=excluded.tfn_upper, confidence=excluded.confidence,"
                " source=excluded.source, evidence=excluded.evidence,"
                " created_at=excluded.created_at",
                (new_id(), ticket_id, name, part["tfn_lower"], part["tfn_modal"],
                 part["tfn_upper"], part["confidence"], part["source"],
                 dumps(part["evidence"]), now))


def _apply_derivation(conn, ticket_id: str, derived: dict) -> None:
    """Copy the derivation summary onto the ticket row for cheap querying."""
    cost = derived["cost_estimate"]
    spec = get_reference().incident(derived["incident_type"])
    spec_roles = list(spec.required_roles) or None
    execute(conn,
            "UPDATE tickets SET category = ?, department_id = ?,"
            " priority_floor = ?, estimated_cost_inr = ?, cost_status = ?,"
            " cost_confidence = ?, cost_breakdown = ?, estimated_hours = ?,"
            " required_roles = COALESCE(?, required_roles),"
            " candidate_equipment = ?, criteria_flags = ?,"
            " overall_confidence = ?, external_handoff = ?, updated_at = ?"
            " WHERE id = ?",
            (derived["incident_type"], derived["department_id"],
             derived["priority_floor"], cost.get("estimated_cost_inr"),
             cost.get("cost_status"), cost.get("cost_confidence"),
             dumps(cost), cost.get("estimated_hours"),
             dumps(spec_roles) if spec_roles else None,
             dumps(cost.get("equipment_plan")), dumps(derived["flags"]),
             derived["overall_confidence"],
             dumps(derived["external_handoff"]) or None,
             utcnow_iso(), ticket_id))
    persist_criteria(conn, ticket_id, derived)


def derive_for_ticket(conn, ticket: dict) -> dict:
    """Derive criteria for a stored ticket, pulling its ward context along."""
    ward = wards.get_ward(conn, ticket.get("ward_id"))
    stats = wards.ward_stats(conn)
    payload = dict(ticket)
    payload["cost_inputs"] = loads(ticket.get("cost_inputs")) or None
    cost = estimate_cost(ticket.get("category"), payload["cost_inputs"])
    return derive_criteria(payload, ward=ward, ward_stats=stats,
                           cost_estimate=cost)


def rescore_ticket(conn, ticket_id: str) -> dict:
    """Re-derive after a fact changed (cost entered, condition confirmed)."""
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not row:
        return {"updated": False, "reason": "ticket not found"}
    derived = derive_for_ticket(conn, dict(row))
    _apply_derivation(conn, ticket_id, derived)
    return {"updated": True, "ticket_id": ticket_id,
            "overall_confidence": derived["overall_confidence"],
            "flags": derived["flags"],
            "priority_floor": derived["priority_floor"],
            "priority_floor_reason": derived["priority_floor_reason"],
            "cost_status": derived["cost_estimate"]["cost_status"]}


TRUTHY = {"1", "true", "yes", "y", "on", "confirmed"}


def _as_bool(value: Any) -> int:
    """Only an explicit affirmative counts.

    These flags escalate a ticket's priority floor, so an absent or unparseable
    value must read as "not confirmed" rather than as False-ish noise that later
    gets treated as a confirmation.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    return 1 if str(value).strip().lower() in TRUTHY else 0


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    return None if number is None else int(number)


def create_ticket(conn, payload: dict, uploads: list[dict] | None = None,
                  actor: str | None = None) -> dict:
    """Ingest one citizen report and return what the submitter should be told.

    The ticket row is written *before* dedup and criteria run. That ordering is
    deliberate: if hashing or scoring fails, the citizen's report still exists
    with a reference number. A report that is lost because the scorer crashed is
    a far worse failure than a report that is temporarily unscored.
    """
    ref = get_reference()
    raw_category = (payload.get("category") or payload.get("incident_type")
                    or "unclassified")
    category = ref.canonical_category(raw_category)
    spec = ref.incident(category)

    lat, lon = _as_float(payload.get("lat")), _as_float(payload.get("lon"))
    ward_info = wards.resolve_ward(conn, payload.get("ward_id")
                                   or payload.get("ward"), lat, lon, actor)
    reported_at = payload.get("reported_at") or utcnow_iso()
    deadlines = compute_deadlines(spec, reported_at)

    ticket_id = new_id()
    ref_no = generate_ref_no(conn, reported_at)
    now = utcnow_iso()
    execute(conn,
            "INSERT INTO tickets(id, ref_no, citizen_id, citizen_phone, channel,"
            " category, description, lat, lon, ward_id, landmark,"
            " sensitive_site, affected_population, duration_hours, status,"
            " department_id, reported_at, operational_target_minutes,"
            " operational_deadline_at, is_statutory_rts, rts_service_id,"
            " rts_time_limit_days, rts_deadline_at, external_handoff,"
            " blocks_major_road, access_isolated, critical_facility_isolated,"
            " cost_inputs, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ticket_id, ref_no, payload.get("citizen_id"),
             payload.get("citizen_phone"), payload.get("channel") or "web",
             category, payload.get("description"), lat, lon,
             ward_info["ward_id"], payload.get("landmark"),
             payload.get("sensitive_site"),
             _as_int(payload.get("affected_population")),
             _as_float(payload.get("duration_hours")), "open",
             spec.department_id, reported_at,
             deadlines["operational_target_minutes"],
             deadlines["operational_deadline_at"], deadlines["is_statutory_rts"],
             deadlines["rts_service_id"], deadlines["rts_time_limit_days"],
             deadlines["rts_deadline_at"],
             dumps(list(spec.external_handoff)) if spec.external_handoff else None,
             _as_bool(payload.get("blocks_major_road")),
             _as_bool(payload.get("access_isolated")),
             _as_bool(payload.get("critical_facility_isolated")),
             dumps(payload.get("cost_inputs")) if payload.get("cost_inputs") else None,
             now, now))
    dedup.record_event(conn, ticket_id, "created", to_value="open", actor=actor,
                       note=f"reported as '{raw_category}' -> {category}; "
                            f"ward {ward_info['method']}")
    return _finish_ingest(conn, ticket_id, ref_no, str(raw_category), category,
                          ward_info, uploads, actor, reported_at)


def _finish_ingest(conn, ticket_id: str, ref_no: str, raw_category: str,
                   category: str, ward_info: dict, uploads: list[dict] | None,
                   actor: str | None, reported_at: str) -> dict:
    """Hash media, run dedup, derive criteria, and build the ingest response."""
    media = save_media(conn, ticket_id, uploads or [])
    row = dict(query_one(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,)))
    candidate = dict(row)
    candidate["phash_list"] = media["phash_list"]
    verdict = dedup.find_duplicate(conn, candidate)

    dedup_action: dict[str, Any] = {"decision": verdict["decision"]}
    if verdict["decision"] == "duplicate" and verdict["parent_id"]:
        dedup_action.update(dedup.apply_duplicate(conn, verdict["parent_id"],
                                                  ticket_id, verdict["match"],
                                                  actor))
    elif verdict["decision"] == "recurrence" and verdict["parent_id"]:
        dedup_action.update(dedup.link_recurrence(conn, verdict["parent_id"],
                                                  ticket_id, verdict["match"],
                                                  actor))

    row = dict(query_one(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,)))
    derived = derive_for_ticket(conn, row)
    _apply_derivation(conn, ticket_id, derived)
    row = dict(query_one(conn, "SELECT * FROM tickets WHERE id = ?", (ticket_id,)))

    is_duplicate = bool(row["is_duplicate"])
    if is_duplicate:
        parent = query_one(conn, "SELECT ref_no FROM tickets WHERE id = ?",
                           (row["duplicate_of_id"],))
        message = (f"Thank you. This matches an existing report "
                   f"{(parent or {})['ref_no'] if parent else ''}, so it has been "
                   f"added to it. That report now carries more community weight. "
                   f"Your reference number is {ref_no}.")
    elif verdict["decision"] == "recurrence":
        message = (f"Thank you. This issue was reported and closed before, so it "
                   f"has been logged as a repeat occurrence and flagged for "
                   f"review. Your reference number is {ref_no}.")
    else:
        message = (f"Thank you. Your report is registered as {ref_no} and will be "
                   f"ranked against today's other work.")

    return {
        "id": ticket_id,
        "ticket_id": ticket_id,
        "ref_no": ref_no,
        "message": message,
        "is_duplicate": is_duplicate,
        "status": row["status"],
        "reported_category": raw_category,
        "category": category,
        "department_id": row["department_id"],
        "ward": ward_info,
        "sla": sla_view(row),
        "dedup": {**verdict, "action": dedup_action},
        "cost": derived["cost_estimate"],
        "criteria": derived["scores"],
        "criteria_flags": derived["flags"],
        "overall_confidence": derived["overall_confidence"],
        "priority_floor": derived["priority_floor"],
        "priority_floor_reason": derived["priority_floor_reason"],
        "media": media,
    }


def sla_view(row: dict, now: Any = None) -> dict:
    """Both clocks for one ticket, each with the number behind the verdict."""
    ref = get_reference()
    moment = now or utcnow()
    started = parse_iso(row.get("reported_at")) or moment
    elapsed_minutes = max(0.0, (moment - started).total_seconds() / 60.0)
    target = row.get("operational_target_minutes")
    op_status = ref.operational_sla_status(elapsed_minutes, target)
    rts_days_elapsed = elapsed_minutes / 1440.0
    rts = ref.rts_status(rts_days_elapsed if row.get("rts_time_limit_days")
                         else None, row.get("rts_time_limit_days"))
    remaining = (None if target is None
                 else round(float(target) - elapsed_minutes, 1))
    return {
        "elapsed_minutes": round(elapsed_minutes, 1),
        "operational_target_minutes": target,
        "operational_deadline_at": row.get("operational_deadline_at"),
        "operational_status": op_status,
        "minutes_remaining": remaining,
        "operational_note": ("no published response target for this category"
                             if target is None else None),
        "is_statutory_rts": bool(row.get("is_statutory_rts")),
        "rts_service_id": row.get("rts_service_id"),
        "rts_time_limit_days": row.get("rts_time_limit_days"),
        "rts_deadline_at": row.get("rts_deadline_at"),
        "rts_status": rts,
        "days_elapsed": round(rts_days_elapsed, 2),
    }


PUBLIC_COLUMNS = (
    "id", "ref_no", "citizen_phone", "channel", "category", "description",
    "lat", "lon", "ward_id", "landmark", "sensitive_site",
    "affected_population", "duration_hours", "status", "priority_floor",
    "department_id", "assigned_team", "reported_at", "acknowledged_at",
    "operational_target_minutes", "operational_deadline_at",
    "is_statutory_rts", "rts_service_id", "rts_time_limit_days",
    "rts_deadline_at", "is_duplicate", "duplicate_of_id", "recurrence_of_id",
    "community_multiplier", "report_count", "estimated_cost_inr",
    "cost_status", "cost_confidence", "estimated_hours", "latest_cci",
    "latest_rank", "latest_weight_version", "escalation_level", "resolved_at",
    "overall_confidence", "blocks_major_road", "access_isolated",
    "critical_facility_isolated", "created_at", "updated_at",
)

JSON_COLUMNS = ("cost_breakdown", "required_roles", "candidate_equipment",
                "criteria_flags", "external_handoff", "dedup_evidence",
                "cost_inputs")


def to_public(row: dict, include_json: bool = False) -> dict:
    """Read model for the API.

    ``cci_score`` is an alias of ``latest_cci``: the existing dashboard reads
    ``cci_score``, and renaming a field the frontend already ships would be a
    self-inflicted integration bug.
    """
    out = {key: row.get(key) for key in PUBLIC_COLUMNS if key in row}
    out["is_duplicate"] = bool(row.get("is_duplicate"))
    out["is_statutory_rts"] = bool(row.get("is_statutory_rts"))
    out["cci_score"] = row.get("latest_cci")
    out["sla"] = sla_view(row)
    if include_json:
        for key in JSON_COLUMNS:
            if key in row:
                out[key] = loads(row.get(key))
    else:
        out["criteria_flags"] = loads(row.get("criteria_flags")) or []
    return out


def list_tickets(conn, *, status: str | None = None, ward_id: str | None = None,
                 category: str | None = None, include_duplicates: bool = False,
                 sla: str | None = None, limit: int = 200,
                 offset: int = 0) -> dict:
    """Filtered queue. Duplicates are hidden by default -- they are not work."""
    clauses, params = [], []
    if status and status != "all":
        clauses.append("status = ?")
        params.append(status)
    if ward_id:
        clauses.append("ward_id = ?")
        params.append(ward_id)
    if category:
        clauses.append("category = ?")
        params.append(get_reference().canonical_category(category))
    if not include_duplicates:
        clauses.append("is_duplicate = 0")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    total = query_one(conn, f"SELECT COUNT(*) AS n FROM tickets{where}",
                      tuple(params))
    rows = query_all(conn,
                     f"SELECT * FROM tickets{where} ORDER BY "
                     "latest_cci DESC NULLS LAST, reported_at DESC "
                     "LIMIT ? OFFSET ?",
                     (*params, int(limit), int(offset)))
    items = [to_public(dict(r)) for r in rows]
    if sla:
        wanted = sla.upper()
        items = [t for t in items if t["sla"]["operational_status"] == wanted]
    return {"total": int(total["n"] if total else 0), "count": len(items),
            "items": items}


def get_ticket(conn, ticket_id: str) -> dict | None:
    """Full detail: criteria with evidence, media, timeline, dedup cluster."""
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ? OR ref_no = ?",
                    (ticket_id, ticket_id))
    if not row:
        return None
    row = dict(row)
    detail = to_public(row, include_json=True)
    criteria = {}
    for score in query_all(conn, "SELECT * FROM ticket_criteria_scores WHERE "
                                 "ticket_id = ?", (row["id"],)):
        criteria[score["criterion"]] = {
            "tfn": [score["tfn_lower"], score["tfn_modal"], score["tfn_upper"]],
            "confidence": score["confidence"],
            "source": score["source"],
            "evidence": loads(score["evidence"]),
        }
    detail["criteria"] = criteria
    detail["media"] = [
        {"id": m["id"], "file_path": m["file_path"], "phash": m["phash"],
         "size_bytes": m["size_bytes"]}
        for m in query_all(conn, "SELECT * FROM ticket_media WHERE ticket_id = ?",
                           (row["id"],))]
    detail["events"] = [dict(e) for e in query_all(
        conn, "SELECT event, from_value, to_value, actor, note, created_at "
              "FROM ticket_events WHERE ticket_id = ? ORDER BY created_at",
        (row["id"],))]
    detail["cluster"] = dedup.duplicate_cluster(conn, row["id"])
    detail["score_history"] = [dict(s) for s in query_all(
        conn, "SELECT run_id, cci, cci_base, community_multiplier, sla_bonus, "
              "rank_position, weight_version, created_at FROM ticket_scores "
              "WHERE ticket_id = ? ORDER BY created_at DESC LIMIT 20",
        (row["id"],))]
    return detail


COST_INPUT_FIELDS = ("runtime_vehicle_cost", "runtime_labour_cost",
                     "runtime_material_cost", "other_cost", "crew_hours",
                     "equipment_hours")

CONDITION_FIELDS = ("blocks_major_road", "access_isolated",
                    "critical_facility_isolated")


def update_cost_inputs(conn, ticket_id: str, inputs: dict,
                       actor: str | None = None) -> dict:
    """Record the money only a human can know, then re-derive C4.

    Water and waste work has no verified unit rate in the accessible public
    records, so an operator filling these fields is how a ticket moves from
    COST_INCOMPLETE to a real number. The entered values are stored so the
    estimate can always be reproduced.
    """
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ? OR ref_no = ?",
                    (ticket_id, ticket_id))
    if not row:
        return {"updated": False, "reason": "ticket not found"}
    merged = loads(row["cost_inputs"]) or {}
    accepted = {}
    for field in COST_INPUT_FIELDS:
        if field in inputs and inputs[field] is not None:
            value = inputs[field]
            if field == "equipment_hours" and isinstance(value, dict):
                merged[field] = {str(k).upper(): float(v)
                                 for k, v in value.items()}
            else:
                merged[field] = float(value)
            accepted[field] = merged[field]
        note_key = f"{field}_note"
        if inputs.get(note_key):
            merged[note_key] = str(inputs[note_key])
    if not accepted:
        return {"updated": False, "reason": "no recognised cost fields supplied"}
    before = row["cost_status"]
    execute(conn, "UPDATE tickets SET cost_inputs = ?, updated_at = ? WHERE id = ?",
            (dumps(merged), utcnow_iso(), row["id"]))
    result = rescore_ticket(conn, row["id"])
    after = query_one(conn, "SELECT cost_status, estimated_cost_inr FROM tickets "
                            "WHERE id = ?", (row["id"],))
    dedup.record_event(conn, row["id"], "cost_inputs_entered",
                       from_value=before, to_value=after["cost_status"],
                       actor=actor, note=dumps(accepted))
    return {"updated": True, "ticket_id": row["id"], "accepted": accepted,
            "cost_status_before": before,
            "cost_status": after["cost_status"],
            "estimated_cost_inr": after["estimated_cost_inr"],
            "rescore": result}


def confirm_conditions(conn, ticket_id: str, conditions: dict,
                       actor: str | None = None) -> dict:
    """Confirm or clear the escalating conditions, then re-derive.

    ``flood_road_blockage`` carries the conditional statutory floor
    ``critical_if_people_or_critical_facilities_isolated``. Treating that
    condition as automatically true would inflate every waterlogging report to
    critical; it becomes critical only when somebody confirms the isolation, and
    this is where that confirmation is recorded and attributed.
    """
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ? OR ref_no = ?",
                    (ticket_id, ticket_id))
    if not row:
        return {"updated": False, "reason": "ticket not found"}
    changes, params = [], []
    for field in CONDITION_FIELDS:
        if field in conditions:
            changes.append(f"{field} = ?")
            params.append(_as_bool(conditions[field]))
    for field in ("sensitive_site", "affected_population", "duration_hours",
                  "landmark"):
        if field in conditions:
            changes.append(f"{field} = ?")
            params.append(conditions[field])
    if not changes:
        return {"updated": False, "reason": "no recognised condition fields"}
    execute(conn, f"UPDATE tickets SET {', '.join(changes)}, updated_at = ? "
                  "WHERE id = ?", (*params, utcnow_iso(), row["id"]))
    before_floor = row["priority_floor"]
    result = rescore_ticket(conn, row["id"])
    after = query_one(conn, "SELECT priority_floor FROM tickets WHERE id = ?",
                      (row["id"],))
    dedup.record_event(conn, row["id"], "conditions_confirmed",
                       from_value=before_floor, to_value=after["priority_floor"],
                       actor=actor, note=dumps(conditions))
    return {"updated": True, "ticket_id": row["id"],
            "priority_floor_before": before_floor,
            "priority_floor": after["priority_floor"],
            "priority_floor_reason": result.get("priority_floor_reason"),
            "confirmed_by": actor, "rescore": result}


STATUS_FLOW = {
    "open": ("scored", "scheduled", "deferred", "deduped", "rejected"),
    "scored": ("scheduled", "deferred", "rejected"),
    "scheduled": ("dispatched", "deferred", "resolved"),
    "deferred": ("scheduled", "scored", "rejected"),
    "dispatched": ("resolved", "deferred"),
    "resolved": ("open",),        # reopened after a failed repair
    "deduped": ("open",),         # unmerged by an officer
    "rejected": ("open",),
}


def update_status(conn, ticket_id: str, status: str, actor: str | None = None,
                  note: str | None = None) -> dict:
    """Move a ticket through the lifecycle, refusing impossible jumps.

    An unconstrained status field is how audit trails become fiction: a ticket
    that goes straight from ``open`` to ``resolved`` with no dispatch cannot be
    explained to anyone later.
    """
    row = query_one(conn, "SELECT * FROM tickets WHERE id = ? OR ref_no = ?",
                    (ticket_id, ticket_id))
    if not row:
        return {"updated": False, "reason": "ticket not found"}
    current = row["status"]
    target = (status or "").strip().lower()
    if target == current:
        return {"updated": False, "reason": f"already {current}"}
    allowed = STATUS_FLOW.get(current, ())
    if target not in allowed:
        return {"updated": False, "reason": f"cannot move {current} -> {target}",
                "allowed": list(allowed)}
    now = utcnow_iso()
    extra, params = "", []
    if target == "resolved":
        extra, params = ", resolved_at = ?, closure_note = ?", [now, note]
    elif target == "dispatched" and not row["acknowledged_at"]:
        extra, params = ", acknowledged_at = ?", [now]
    execute(conn, f"UPDATE tickets SET status = ?{extra}, updated_at = ? "
                  "WHERE id = ?", (target, *params, now, row["id"]))
    dedup.record_event(conn, row["id"], "status_changed", from_value=current,
                       to_value=target, actor=actor, note=note)
    return {"updated": True, "ticket_id": row["id"], "from": current,
            "to": target}


def queue_for_prioritisation(conn, ward_id: str | None = None) -> list[dict]:
    """The tickets that are actually competing for today's resources.

    Excludes duplicates (folded into their parent, and their weight is already
    carried there) and anything already finished. This is the input the triage
    engine ranks.
    """
    clauses = ["is_duplicate = 0",
               "status IN ('open', 'scored', 'deferred')"]
    params: list[Any] = []
    if ward_id:
        clauses.append("ward_id = ?")
        params.append(ward_id)
    rows = query_all(conn, "SELECT * FROM tickets WHERE " + " AND ".join(clauses)
                     + " ORDER BY reported_at", tuple(params))
    return [dict(r) for r in rows]


if __name__ == "__main__":  # pragma: no cover
    import io
    import json
    import random

    from database import get_conn, init_db

    def photo(seed: int, jitter: int = 0, quality: int = 92) -> bytes:
        from PIL import Image
        random.seed(seed)
        img = Image.new("RGB", (200, 200))
        px = img.load()
        blocks = [[random.randint(0, 255) for _ in range(8)] for _ in range(8)]
        for y in range(200):
            for x in range(200):
                v = max(0, min(255, blocks[y * 8 // 200][x * 8 // 200] + jitter))
                px[x, y] = (v, v, v)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    init_db()
    with get_conn() as c:
        for table in ("ticket_criteria_scores", "ticket_events", "ticket_media",
                      "ticket_scores", "tickets"):
            c.execute(f"DELETE FROM {table}")

        first = create_ticket(c, {
            "citizen_phone": "9876543210", "category": "sanitation",
            "description": "Drain overflowing outside the civil hospital gate",
            "ward_id": "Ward-4", "lat": 19.8811, "lon": 74.4785,
            "sensitive_site": "hospital", "affected_population": 1800,
        }, [{"filename": "drain.jpg", "content": photo(11)}], actor="selftest")
        print("A", first["ref_no"], first["category"], first["dedup"]["decision"],
              "conf", first["overall_confidence"], first["cost"]["cost_status"])
        print("  sla:", first["sla"]["operational_status"],
              first["sla"]["operational_target_minutes"], "min target")

        second = create_ticket(c, {
            "citizen_phone": "9123456780", "category": "sanitation",
            "description": "Same drain overflowing near hospital",
            "ward_id": "Ward-4", "lat": 19.8812, "lon": 74.4786,
        }, [{"filename": "again.jpg", "content": photo(11, jitter=8, quality=45)}],
            actor="selftest")
        print("B", second["ref_no"], "duplicate?", second["is_duplicate"],
              "->", second["dedup"]["action"].get("community_multiplier"))
        print("  message:", second["message"])

        flood = create_ticket(c, {
            "citizen_phone": "9000000001", "category": "waterlogging",
            "description": "Water logged on the main approach road",
            "ward_id": "Ward-9", "lat": 19.8600, "lon": 74.4700,
        }, [], actor="selftest")
        print("C", flood["ref_no"], "floor", flood["priority_floor"], "-",
              flood["priority_floor_reason"])
        print("  after isolation confirmed:",
              confirm_conditions(c, flood["id"], {"access_isolated": True},
                                 actor="ward_officer")["priority_floor"])

        print("cost entry:", json.dumps(update_cost_inputs(
            c, first["id"], {"runtime_labour_cost": 1200,
                             "runtime_material_cost": 800,
                             "runtime_vehicle_cost": 0, "other_cost": 0},
            actor="ward_officer")["cost_status"]))
        print("status flow:", update_status(c, first["id"], "resolved"))
        print("queue size:", len(queue_for_prioritisation(c)))
        listing = list_tickets(c)
        print("list:", listing["total"], "->",
              [(t["ref_no"], t["status"], t["cci_score"]) for t in listing["items"]])
        detail = get_ticket(c, first["ref_no"])
        print("detail criteria:", {k: v["tfn"] for k, v in detail["criteria"].items()})
        print("events:", [e["event"] for e in detail["events"]])
