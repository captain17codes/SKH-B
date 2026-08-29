"""Duplicate report detection and the community-weight it produces.

Why this is not a one-liner: in a municipal system a false merge is worse than
a missed one. Merging two complaints deletes one citizen's report from the
queue, so every merge here has to clear *two independent* pieces of evidence --
a perceptual image match or a strong text match, **and** physical proximity --
and it records why it fired so an officer can undo it.

Three real distinctions the previous implementation collapsed:

* ``is_duplicate()`` returned ``(False, None)``, which is truthy as a tuple, so
  every photo ticket was flagged a duplicate. Everything here returns a dict
  with an explicit ``decision`` key instead of a bare tuple.
* proximity was ignored entirely, so the same pothole photo forwarded from
  another ward merged two unrelated complaints.
* a new report about an **already resolved** ticket is a *recurrence*, not a
  duplicate: the work was done and has failed again. It must stay a separate
  ticket, linked, not folded into a closed one.
"""
from __future__ import annotations

import math
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

try:
    from config import settings
    from database import (dumps, execute, new_id, parse_iso, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.reference import ReferenceData, get_reference
    from services.imaging import hamming_hex, similarity
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings
    from database import (dumps, execute, new_id, parse_iso, query_all,
                          query_one, utcnow, utcnow_iso)
    from domain.reference import ReferenceData, get_reference
    from services.imaging import hamming_hex, similarity

EARTH_RADIUS_M = 6_371_008.8

# Statuses where a fresh report means "it came back", not "same thing again".
CLOSED_STATUSES = ("resolved", "closed", "rejected", "verified_closed")

# Hindi/Marathi/English filler that carries no locating information.
STOPWORDS = {
    "the", "and", "is", "in", "at", "of", "a", "an", "to", "for", "on", "near",
    "please", "kindly", "sir", "madam", "there", "very", "has", "have", "been",
    "this", "that", "with", "from", "our", "my", "we", "it", "are", "was",
    "ahe", "aahe", "nahi", "kripaya", "hai", "hain", "nahin", "karo", "kara",
}


def haversine_meters(lat1: float | None, lon1: float | None,
                     lat2: float | None, lon2: float | None) -> float | None:
    """Great-circle distance in metres, or None if any coordinate is missing.

    None is a first-class answer here: "we do not know how far apart these are"
    must not be silently read as "they are at the same place".
    """
    if None in (lat1, lon1, lat2, lon2):
        return None
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = p2 - p1
    dl = math.radians(float(lon2) - float(lon1))
    h = (math.sin(dp / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2)
    return round(2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h))), 2)


def community_multiplier(report_count: int) -> float:
    """Weight for "many people reported this", capped.

    Uncapped, a single viral complaint would outrank a hospital water failure
    that only one person bothered to report, which is exactly the populism trap
    the brief warns about. The cap is the guard.
    """
    count = max(1, int(report_count or 1))
    raw = 1.0 + settings.COMMUNITY_MULTIPLIER_STEP * (count - 1)
    return round(min(raw, settings.COMMUNITY_MULTIPLIER_CAP), 4)


def _tokens(text: str | None) -> set[str]:
    if not text:
        return set()
    words = re.findall(r"[\wऀ-ॿ]+", str(text).lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def text_similarity(a: str | None, b: str | None) -> float:
    """Jaccard overlap of content words. 0.0 when either side is empty."""
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return round(len(ta & tb) / len(ta | tb), 4)


def resolve_root(conn, ticket_id: str | None, max_depth: int = 8) -> str | None:
    """Follow ``duplicate_of_id`` to the surviving parent.

    Depth-capped and cycle-guarded: a bad merge chain must degrade to "attach to
    the last sane ticket", never to an infinite loop inside an ingest request.
    """
    seen: set[str] = set()
    current = ticket_id
    for _ in range(max_depth):
        if not current or current in seen:
            break
        seen.add(current)
        row = query_one(conn, "SELECT duplicate_of_id FROM tickets WHERE id = ?",
                        (current,))
        if not row or not row["duplicate_of_id"]:
            return current
        current = row["duplicate_of_id"]
    return current


def _candidate_rows(conn, since_iso: str, exclude_id: str | None) -> list[dict]:
    """Open tickets in the window, each with its best image hashes attached.

    Duplicates are excluded as candidates (we always compare against the
    surviving parent) but closed tickets are kept, because they are needed to
    detect a recurrence.
    """
    sql = """
        SELECT t.id, t.ref_no, t.category, t.description, t.lat, t.lon,
               t.ward_id, t.status, t.reported_at, t.report_count,
               t.community_multiplier, t.department_id, t.is_duplicate,
               t.duplicate_of_id, t.resolved_at, t.citizen_phone,
               (SELECT GROUP_CONCAT(m.phash)
                  FROM ticket_media m
                 WHERE m.ticket_id = t.id AND m.phash IS NOT NULL) AS phashes
          FROM tickets t
         WHERE t.reported_at >= ?
           AND t.is_duplicate = 0
    """
    params: list[Any] = [since_iso]
    if exclude_id:
        sql += " AND t.id <> ?"
        params.append(exclude_id)
    sql += " ORDER BY t.reported_at DESC LIMIT 500"
    rows = query_all(conn, sql, tuple(params))
    out = []
    for row in rows:
        item = dict(row)
        item["phash_list"] = [h for h in (item.pop("phashes") or "").split(",")
                              if h]
        out.append(item)
    return out


def _best_hash_distance(new_hashes: list[str],
                        old_hashes: list[str]) -> int | None:
    best = None
    for a in new_hashes or []:
        for b in old_hashes or []:
            d = hamming_hex(a, b)
            if d is not None and (best is None or d < best):
                best = d
    return best


def _hours_apart(a: str | None, b: str | None) -> float | None:
    ta, tb = parse_iso(a), parse_iso(b)
    if not ta or not tb:
        return None
    return abs((ta - tb).total_seconds()) / 3600.0


def evaluate_pair(new: dict, old: dict, ref: ReferenceData) -> dict:
    """Compare one incoming report against one existing ticket.

    Returns a verdict dict always -- ``matched`` False carries the reason it did
    not match, which is what makes a near-miss auditable instead of invisible.
    """
    cat_new = ref.canonical_category(new.get("category"))
    cat_old = ref.canonical_category(old.get("category"))
    same_category = cat_new == cat_old
    same_dept = (ref.incident(cat_new).department_id
                 == ref.incident(cat_old).department_id)
    hash_dist = _best_hash_distance(new.get("phash_list") or [],
                                    old.get("phash_list") or [])
    geo = haversine_meters(new.get("lat"), new.get("lon"),
                           old.get("lat"), old.get("lon"))
    same_ward = bool(new.get("ward_id") and old.get("ward_id")
                     and new["ward_id"] == old["ward_id"])
    sim = text_similarity(new.get("description"), old.get("description"))
    gap_hours = _hours_apart(new.get("reported_at"), old.get("reported_at"))

    verdict: dict[str, Any] = {
        "ticket_id": old.get("id"),
        "ref_no": old.get("ref_no"),
        "status": old.get("status"),
        "category": cat_old,
        "hash_distance": hash_dist,
        "hash_similarity": None,
        "distance_meters": geo,
        "same_ward": same_ward,
        "text_similarity": sim,
        "hours_apart": None if gap_hours is None else round(gap_hours, 2),
        "matched": False,
        "basis": None,
        "confidence": None,
        "reason": None,
    }
    if hash_dist is not None:
        verdict["hash_similarity"] = round(1.0 - hash_dist / 64.0, 4)
    return _apply_match_rules(verdict, new, old, same_category, same_dept,
                              same_ward, hash_dist, geo, sim, gap_hours)


def _apply_match_rules(verdict: dict, new: dict, old: dict,
                       same_category: bool, same_dept: bool, same_ward: bool,
                       hash_dist: int | None, geo: float | None,
                       sim: float, gap_hours: float | None) -> dict:
    """The merge policy, isolated so it can be unit-tested and quoted verbatim.

    Every accepting branch needs an identity signal *and* a location signal.
    """
    photo_max = int(settings.DEDUPE_HAMMING_THRESHOLD)
    photo_strict = max(2, photo_max // 2)
    radius = float(settings.DEDUPE_RADIUS_METERS)
    text_radius = float(settings.DEDUPE_TEXT_RADIUS_METERS)

    # A -- same reporter, same category, minutes apart: an accidental resubmit.
    phone = (new.get("citizen_phone") or "").strip()
    if (phone and phone == (old.get("citizen_phone") or "").strip()
            and same_category and gap_hours is not None and gap_hours <= 2.0):
        verdict.update(matched=True, basis="same_reporter_resubmission",
                       confidence="high",
                       reason="identical reporter and category within 2 hours")
        return verdict

    # B -- perceptual image match plus proximity.
    if hash_dist is not None and hash_dist <= photo_max:
        if not (same_category or (hash_dist <= photo_strict and same_dept)):
            verdict["reason"] = ("image matched but the reported categories "
                                 "are unrelated; kept separate")
            return verdict
        if geo is not None:
            if geo <= radius:
                strong = hash_dist <= photo_strict and geo <= radius / 3.0
                verdict.update(
                    matched=True, basis="perceptual_image_match",
                    confidence="high" if strong else "medium",
                    reason=(f"pHash distance {hash_dist} <= {photo_max} and "
                            f"{geo:.0f} m apart <= {radius:.0f} m"))
                return verdict
            verdict["reason"] = (f"image matched but {geo:.0f} m apart exceeds "
                                 f"the {radius:.0f} m radius")
            return verdict
        if same_ward and hash_dist <= photo_strict:
            verdict.update(
                matched=True, basis="perceptual_image_match_ward_only",
                confidence="medium",
                reason=(f"no GPS on one report; pHash distance {hash_dist} <= "
                        f"{photo_strict} and both in the same ward"))
            return verdict
        verdict["reason"] = ("image matched but neither GPS nor a shared ward "
                             "confirms it is the same place")
        return verdict

    # C -- text and tight proximity, for reports with no usable photo.
    if same_category and sim >= 0.55:
        if geo is not None and geo <= text_radius:
            verdict.update(
                matched=True, basis="text_and_proximity_match",
                confidence="medium" if (sim >= 0.7 and geo <= 25) else "low",
                reason=(f"description overlap {sim:.2f} and {geo:.0f} m apart "
                        f"<= {text_radius:.0f} m"))
            return verdict
        if geo is None and same_ward and sim >= 0.75:
            verdict.update(
                matched=True, basis="text_match_ward_only", confidence="low",
                reason=(f"no GPS; description overlap {sim:.2f} within the "
                        "same ward"))
            return verdict
        verdict["reason"] = ("descriptions are similar but the location "
                             "evidence is too weak to merge")
        return verdict

    verdict["reason"] = "no image, text or reporter evidence of a duplicate"
    return verdict


_CONF_ORDER = {"high": 0, "medium": 1, "low": 2, None: 3}


def _rank_key(v: dict) -> tuple:
    """Open tickets first, then strongest evidence.

    Open-before-closed matters: if a live ticket and a closed one both match, the
    live one is the real parent and the closed one is just history.
    """
    return (
        1 if (v.get("status") or "") in CLOSED_STATUSES else 0,
        _CONF_ORDER.get(v.get("confidence"), 3),
        v["hash_distance"] if v.get("hash_distance") is not None else 999,
        v["distance_meters"] if v.get("distance_meters") is not None else 1e9,
        -float(v.get("text_similarity") or 0.0),
    )


def find_duplicate(conn, candidate: dict,
                   ref: ReferenceData | None = None,
                   window_hours: int | None = None) -> dict:
    """Decide whether an incoming report is new, a duplicate, or a recurrence.

    ``candidate`` keys used: ``id`` (to exclude itself), ``category``,
    ``description``, ``lat``, ``lon``, ``ward_id``, ``citizen_phone``,
    ``reported_at``, ``phash_list``.
    """
    ref = ref or get_reference()
    hours = int(window_hours or settings.DEDUPE_WINDOW_HOURS)
    anchor = parse_iso(candidate.get("reported_at")) or utcnow()
    since_iso = (anchor - timedelta(hours=hours)).isoformat().replace(
        "+00:00", "Z")

    rows = _candidate_rows(conn, since_iso, candidate.get("id"))
    matches, near_misses = [], []
    for row in rows:
        verdict = evaluate_pair(candidate, row, ref)
        if verdict["matched"]:
            matches.append(verdict)
        elif (verdict["hash_distance"] is not None
              or float(verdict["text_similarity"] or 0) >= 0.4):
            near_misses.append(verdict)

    matches.sort(key=_rank_key)
    near_misses.sort(key=_rank_key)
    policy = {
        "hamming_threshold": int(settings.DEDUPE_HAMMING_THRESHOLD),
        "geo_radius_meters": float(settings.DEDUPE_RADIUS_METERS),
        "text_radius_meters": float(settings.DEDUPE_TEXT_RADIUS_METERS),
        "window_hours": hours,
        "multiplier_step": float(settings.COMMUNITY_MULTIPLIER_STEP),
        "multiplier_cap": float(settings.COMMUNITY_MULTIPLIER_CAP),
        "provenance": "operator_tunable_no_published_municipal_standard",
    }
    result = {
        "decision": "unique",
        "parent_id": None,
        "match": None,
        "matches": matches[:5],
        "near_misses": near_misses[:3],
        "compared_against": len(rows),
        "policy": policy,
    }
    if not matches:
        result["reason"] = (near_misses[0]["reason"] if near_misses
                            else "no comparable report in the window")
        return result

    best = matches[0]
    closed = (best.get("status") or "") in CLOSED_STATUSES
    result["decision"] = "recurrence" if closed else "duplicate"
    result["parent_id"] = best["ticket_id"]
    result["match"] = best
    result["reason"] = (
        f"same issue reported again after {best['ref_no'] or best['ticket_id']} "
        f"was {best.get('status')}: {best['reason']}" if closed
        else best["reason"])
    return result


def record_event(conn, ticket_id: str, event: str, *, to_value: str | None = None,
                 from_value: str | None = None, actor: str | None = None,
                 note: str | None = None) -> None:
    execute(conn,
            "INSERT INTO ticket_events(id, ticket_id, event, from_value, "
            "to_value, actor, note, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (new_id(), ticket_id, event, from_value, to_value,
             actor or "system", note, utcnow_iso()))


def apply_duplicate(conn, parent_id: str, child_id: str,
                    verdict: dict | None = None,
                    actor: str | None = None) -> dict:
    """Fold ``child_id`` into the surviving parent and raise its community weight.

    The child row is kept, never deleted: the citizen who filed it still has a
    reference number, still gets notified, and an officer can unmerge it.
    """
    root = resolve_root(conn, parent_id)
    if not root or root == child_id:
        return {"applied": False,
                "reason": "resolved parent is the ticket itself"}
    parent = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (root,))
    child = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (child_id,))
    if not parent or not child:
        return {"applied": False, "reason": "parent or child ticket missing"}

    # Anything that had pointed at the child now points at the surviving parent,
    # so no report is orphaned behind a two-step chain.
    execute(conn, "UPDATE tickets SET duplicate_of_id = ?, updated_at = ? "
                  "WHERE duplicate_of_id = ?", (root, utcnow_iso(), child_id))

    transferred = max(1, int(child["report_count"] or 1))
    new_count = int(parent["report_count"] or 1) + transferred
    multiplier = community_multiplier(new_count)
    execute(conn,
            "UPDATE tickets SET report_count = ?, community_multiplier = ?, "
            "updated_at = ? WHERE id = ?",
            (new_count, multiplier, utcnow_iso(), root))
    execute(conn,
            "UPDATE tickets SET is_duplicate = 1, duplicate_of_id = ?, "
            "community_multiplier = 1.0, dedup_evidence = ?, "
            "status = 'deduped', updated_at = ? WHERE id = ?",
            (root, dumps(verdict) if verdict else None, utcnow_iso(), child_id))

    basis = (verdict or {}).get("basis") or "operator_merge"
    record_event(conn, child_id, "duplicate_merged", to_value=root,
                 from_value=child["status"], actor=actor,
                 note=(verdict or {}).get("reason") or basis)
    record_event(conn, root, "duplicate_report_received", to_value=child_id,
                 actor=actor,
                 note=f"report_count={new_count}, multiplier={multiplier}")
    return {"applied": True, "parent_id": root, "child_id": child_id,
            "report_count": new_count, "community_multiplier": multiplier,
            "basis": basis}


def link_recurrence(conn, parent_id: str, child_id: str,
                    verdict: dict | None = None,
                    actor: str | None = None) -> dict:
    """Link a repeat report to the closed ticket it repeats -- without merging.

    A recurrence is evidence that the earlier repair failed, so it must keep its
    own place in the queue. The link is what lets the triage engine see "third
    time in this ward this month" instead of a fresh, isolated complaint.
    """
    root = resolve_root(conn, parent_id)
    if not root or root == child_id:
        return {"applied": False, "reason": "no distinct earlier ticket"}
    execute(conn,
            "UPDATE tickets SET recurrence_of_id = ?, dedup_evidence = ?, "
            "updated_at = ? WHERE id = ?",
            (root, dumps(verdict) if verdict else None, utcnow_iso(), child_id))
    record_event(conn, child_id, "recurrence_linked", to_value=root, actor=actor,
                 note=(verdict or {}).get("reason"))
    record_event(conn, root, "recurrence_reported", to_value=child_id,
                 actor=actor,
                 note="a new report matches this closed ticket")
    return {"applied": True, "recurrence_of_id": root, "child_id": child_id}


def unmerge(conn, child_id: str, actor: str | None = None,
            note: str | None = None) -> dict:
    """Operator override: detach a wrongly merged report.

    The machine's merge is a recommendation, not a verdict; without a reversible
    path the dedup step would be a silent data-loss mechanism.
    """
    child = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (child_id,))
    if not child:
        return {"applied": False, "reason": "ticket not found"}
    parent_id = child["duplicate_of_id"]
    if not child["is_duplicate"] or not parent_id:
        return {"applied": False, "reason": "ticket is not marked a duplicate"}
    parent = query_one(conn, "SELECT * FROM tickets WHERE id = ?", (parent_id,))
    if parent:
        new_count = max(1, int(parent["report_count"] or 1) - 1)
        execute(conn,
                "UPDATE tickets SET report_count = ?, community_multiplier = ?, "
                "updated_at = ? WHERE id = ?",
                (new_count, community_multiplier(new_count), utcnow_iso(),
                 parent_id))
        record_event(conn, parent_id, "duplicate_unmerged", to_value=child_id,
                     actor=actor, note=note)
    # The merge event recorded the status the ticket had before it was folded
    # in, so an undo restores that rather than guessing.
    prior = query_one(conn, "SELECT from_value FROM ticket_events WHERE "
                            "ticket_id = ? AND event = 'duplicate_merged' "
                            "ORDER BY created_at DESC LIMIT 1", (child_id,))
    restore = (prior["from_value"] if prior and prior["from_value"] else "open")
    execute(conn,
            "UPDATE tickets SET is_duplicate = 0, duplicate_of_id = NULL, "
            "status = CASE WHEN status = 'deduped' THEN ? ELSE status END, "
            "updated_at = ? WHERE id = ?", (restore, utcnow_iso(), child_id))
    record_event(conn, child_id, "duplicate_unmerged", from_value=parent_id,
                 actor=actor, note=note)
    return {"applied": True, "child_id": child_id,
            "detached_from": parent_id}


def duplicate_cluster(conn, ticket_id: str) -> dict:
    """The parent plus every report folded into it, for the UI and the audit."""
    root = resolve_root(conn, ticket_id) or ticket_id
    parent = query_one(conn, "SELECT id, ref_no, category, status, report_count,"
                             " community_multiplier, reported_at FROM tickets "
                             "WHERE id = ?", (root,))
    children = query_all(conn,
                         "SELECT id, ref_no, citizen_phone, reported_at, "
                         "dedup_evidence FROM tickets WHERE duplicate_of_id = ? "
                         "ORDER BY reported_at", (root,))
    recurrences = query_all(conn,
                            "SELECT id, ref_no, reported_at FROM tickets "
                            "WHERE recurrence_of_id = ? ORDER BY reported_at",
                            (root,))
    return {
        "parent": dict(parent) if parent else None,
        "duplicates": [dict(r) for r in children],
        "recurrences": [dict(r) for r in recurrences],
        "community_multiplier": (parent["community_multiplier"]
                                 if parent else 1.0),
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    from database import get_conn, init_db

    init_db()
    with get_conn() as c:
        for table in ("ticket_events", "ticket_media", "tickets"):
            c.execute(f"DELETE FROM {table}")
        for w in ("W1", "W2", "W3", "W4", "W5"):
            execute(c, "INSERT OR IGNORE INTO wards(id, name, data_confidence, "
                       "created_at, updated_at) VALUES(?,?,?,?,?)",
                    (w, f"Ward-{w[1:]}", "unverified", utcnow_iso(),
                     utcnow_iso()))

        def add(tid, cat, desc, lat, lon, ward, phash=None, status="open",
                phone=None, when="2026-08-29T08:00:00Z"):
            execute(c, "INSERT INTO tickets(id, ref_no, category, description, "
                       "lat, lon, ward_id, status, citizen_phone, reported_at, "
                       "created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (tid, tid.upper(), cat, desc, lat, lon, ward, status, phone,
                     when, when, when))
            if phash:
                execute(c, "INSERT INTO ticket_media(id, ticket_id, phash, "
                           "media_type, created_at) VALUES(?,?,?,?,?)",
                        (new_id(), tid, phash, "image", when))

        add("t1", "drainage", "Drain overflowing near Nagar Road bus stop",
            19.8811, 74.4785, "W1", "c66dd4e321d6f222")
        add("t2", "pothole", "Big pothole on the highway service road",
            19.8901, 74.4900, "W2", "c1fc0067f17156da")
        add("t3", "drainage", "Drain water on road, resolved last week",
            19.8700, 74.4600, "W3", None, status="resolved")

        cases = [
            ("same photo, 40 m away",
             {"category": "drainage", "description": "Drain overflow again",
              "lat": 19.8814, "lon": 74.4786, "ward_id": "W1",
              "reported_at": "2026-08-29T10:00:00Z",
              "phash_list": ["c66fd4e32156f222"]}),
            ("same photo, 4 km away",
             {"category": "drainage", "description": "Drain overflow",
              "lat": 19.9200, "lon": 74.5100, "ward_id": "W5",
              "reported_at": "2026-08-29T10:00:00Z",
              "phash_list": ["c66fd4e32156f222"]}),
            ("no photo, similar text 30 m away",
             {"category": "sanitation",
              "description": "drain overflowing near nagar road bus stop",
              "lat": 19.8813, "lon": 74.4786, "ward_id": "W1",
              "reported_at": "2026-08-29T11:00:00Z", "phash_list": []}),
            ("matches a resolved ticket",
             {"category": "drainage",
              "description": "Drain water on road resolved last week again",
              "lat": 19.8701, "lon": 74.4600, "ward_id": "W3",
              "reported_at": "2026-08-29T12:00:00Z", "phash_list": []}),
            ("genuinely new",
             {"category": "streetlight", "description": "Street light not working",
              "lat": 19.8500, "lon": 74.4300, "ward_id": "W4",
              "reported_at": "2026-08-29T12:00:00Z", "phash_list": []}),
        ]
        for label, cand in cases:
            res = find_duplicate(c, cand)
            print(f"\n{label}: {res['decision']} parent={res['parent_id']}")
            print("  reason:", res["reason"])

        res = find_duplicate(c, cases[0][1])
        print("\napply:", json.dumps(apply_duplicate(c, res["parent_id"], "t2",
                                                     res["match"])))
        print("cluster:", json.dumps(duplicate_cluster(c, "t2"))[:200])
        print("unmerge:", json.dumps(unmerge(c, "t2", actor="officer")))
        print("multiplier ladder:",
              [community_multiplier(n) for n in (1, 2, 3, 5, 20)])
