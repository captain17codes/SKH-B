"""Ward resolution and ward-level statistics.

No accessible Kopargaon dataset contains a ward master list, ward populations,
ward boundaries or any equity index -- the council's published material covers
tenders, service standards and contacts, not spatial demographics. So this
module is built around that gap rather than pretending it does not exist:

* a ward referenced by a citizen report is created on demand, marked
  ``data_confidence='unverified'``, and says so in ``source_note``;
* population, area and equity index stay NULL until a human enters them, which
  is exactly what makes ``C3_equity`` fall back to a wide fuzzy interval instead
  of a fabricated number;
* ``upsert_ward`` / ``load_wards`` accept the real dataset the moment the
  council provides it, with no code change anywhere else.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

try:
    from database import execute, new_id, query_all, query_one, utcnow_iso
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database import execute, new_id, query_all, query_one, utcnow_iso

CONFIDENCE_LEVELS = ("verified", "operator_entered", "unverified")

# Kopargaon Municipal Council: ~65,273 residents over ~10.56 sq km. Used only to
# sanity-check operator input, never to invent a per-ward figure.
COUNCIL_POPULATION = 65_273
COUNCIL_AREA_SQ_KM = 10.56


def _norm_label(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").strip().lower())


def _ward_no_from_label(value: str | None) -> str | None:
    """Pull a ward number out of 'Ward-7', 'ward 7', 'W7', 'प्रभाग ७' or '7'."""
    if value is None:
        return None
    digits = re.findall(r"\d+", str(value))
    return digits[0] if digits else None


def get_ward(conn, identifier: str | None) -> dict | None:
    """Look a ward up by id, ward_no or name. Never creates anything."""
    if not identifier:
        return None
    ident = str(identifier).strip()
    row = query_one(conn, "SELECT * FROM wards WHERE id = ?", (ident,))
    if row:
        return dict(row)
    number = _ward_no_from_label(ident)
    if number:
        row = query_one(conn, "SELECT * FROM wards WHERE ward_no = ?", (number,))
        if row:
            return dict(row)
    target = _norm_label(ident)
    for candidate in query_all(conn, "SELECT * FROM wards"):
        if _norm_label(candidate["name"]) == target:
            return dict(candidate)
        if _norm_label(candidate["id"]) == target:
            return dict(candidate)
    return None


def ensure_ward(conn, identifier: str | None,
                actor: str | None = None) -> dict | None:
    """Return the ward, creating an explicitly unverified stub if it is new.

    Refusing to create it would drop the only location signal a citizen gave us;
    inventing its population would corrupt the equity criterion. A stub does
    neither: it stores the label, flags itself unverified, and leaves every
    demographic field NULL.
    """
    if not identifier or not str(identifier).strip():
        return None
    existing = get_ward(conn, identifier)
    if existing:
        return existing
    label = str(identifier).strip()
    number = _ward_no_from_label(label)
    ward_id = f"W{number}" if number else f"W-{_norm_label(label)[:12] or new_id()[:8]}"
    if get_ward(conn, ward_id):
        return get_ward(conn, ward_id)
    name = label if not number or not label.isdigit() else f"Ward-{number}"
    now = utcnow_iso()
    execute(conn,
            "INSERT INTO wards(id, ward_no, name, data_confidence, source_note,"
            " created_at, updated_at) VALUES(?,?,?,?,?,?,?)",
            (ward_id, number, name, "unverified",
             "auto-created from a citizen report; not verified against a ward "
             "master list. population/area/equity_index remain unknown.",
             now, now))
    return get_ward(conn, ward_id)


def nearest_ward(conn, lat: float | None,
                 lon: float | None) -> tuple[dict | None, float | None]:
    """Closest ward by stored centroid. Only usable once centroids exist."""
    if lat is None or lon is None:
        return None, None
    rows = query_all(conn, "SELECT * FROM wards WHERE centroid_lat IS NOT NULL "
                           "AND centroid_lon IS NOT NULL AND is_active = 1")
    best, best_d = None, None
    for row in rows:
        dlat = math.radians(float(row["centroid_lat"]) - float(lat))
        dlon = math.radians(float(row["centroid_lon"]) - float(lon))
        mid = math.radians((float(row["centroid_lat"]) + float(lat)) / 2)
        d = 6_371_008.8 * math.hypot(dlat, dlon * math.cos(mid))
        if best_d is None or d < best_d:
            best, best_d = dict(row), d
    return best, (None if best_d is None else round(best_d, 1))


def resolve_ward(conn, ward_hint: str | None = None,
                 lat: float | None = None, lon: float | None = None,
                 actor: str | None = None) -> dict:
    """Decide which ward a report belongs to, and say how that was decided.

    Order of trust: an explicit ward the reporter chose, then a centroid match
    if the council has loaded centroids, then nothing. "Nothing" is a valid
    outcome and is reported, not papered over.
    """
    if ward_hint:
        ward = ensure_ward(conn, ward_hint, actor)
        if ward:
            return {"ward": ward, "ward_id": ward["id"],
                    "method": "reported_by_citizen",
                    "confidence": ward["data_confidence"]}
    ward, distance = nearest_ward(conn, lat, lon)
    if ward:
        return {"ward": ward, "ward_id": ward["id"],
                "method": "nearest_ward_centroid",
                "distance_meters": distance,
                "confidence": ward["data_confidence"]}
    return {"ward": None, "ward_id": None, "method": "unresolved",
            "confidence": None,
            "note": "no ward given by the reporter and no ward centroids loaded"}


def ward_stats(conn) -> dict:
    """Population densities across wards, for the equity percentile.

    Returned even when only a couple of wards have data -- ``_c3_equity`` needs
    at least three to use a percentile and falls back to an absolute scale
    otherwise, so the count is part of the answer.
    """
    rows = query_all(conn, "SELECT id, population, area_sq_km, equity_index "
                           "FROM wards WHERE is_active = 1")
    densities, with_pop, with_index = [], 0, 0
    for row in rows:
        if row["equity_index"] is not None:
            with_index += 1
        if row["population"] and row["area_sq_km"]:
            with_pop += 1
            densities.append(float(row["population"]) / float(row["area_sq_km"]))
    densities.sort()
    return {
        "densities": densities,
        "ward_count": len(rows),
        "with_population_and_area": with_pop,
        "with_equity_index": with_index,
        "usable_for_percentile": len(densities) >= 3,
    }


WARD_FIELDS = ("ward_no", "name", "population", "households", "area_sq_km",
               "centroid_lat", "centroid_lon", "equity_index",
               "flood_exposure", "data_confidence", "source_note", "is_active")


def upsert_ward(conn, payload: dict, actor: str | None = None) -> dict:
    """Create or update one ward from operator input or a real dataset.

    ``data_confidence`` defaults to ``operator_entered`` rather than
    ``verified``: a number typed into a form is better than nothing and worse
    than a published figure, and the equity criterion widens its interval
    accordingly.
    """
    ident = payload.get("id") or payload.get("ward_id") or payload.get("name")
    existing = get_ward(conn, ident)
    now = utcnow_iso()
    values: dict[str, Any] = {}
    for field in WARD_FIELDS:
        if field in payload and payload[field] is not None:
            values[field] = payload[field]
    if "equity_index" in values:
        values["equity_index"] = max(0.0, min(1.0, float(values["equity_index"])))
    values.setdefault("data_confidence", "operator_entered")
    if values["data_confidence"] not in CONFIDENCE_LEVELS:
        values["data_confidence"] = "operator_entered"
    values.setdefault("source_note", f"entered by {actor or 'operator'}")

    if existing:
        sets = ", ".join(f"{k} = ?" for k in values)
        execute(conn, f"UPDATE wards SET {sets}, updated_at = ? WHERE id = ?",
                (*values.values(), now, existing["id"]))
        return get_ward(conn, existing["id"]) or existing

    ward_id = str(payload.get("id") or payload.get("ward_id")
                  or (f"W{_ward_no_from_label(str(ident))}"
                      if _ward_no_from_label(str(ident)) else new_id()))
    values.setdefault("name", str(ident or ward_id))
    values.setdefault("ward_no", _ward_no_from_label(str(ident)))
    cols = ", ".join(["id", *values.keys(), "created_at", "updated_at"])
    marks = ", ".join(["?"] * (len(values) + 3))
    execute(conn, f"INSERT INTO wards({cols}) VALUES({marks})",
            (ward_id, *values.values(), now, now))
    return get_ward(conn, ward_id) or {"id": ward_id, **values}


def list_wards(conn, include_inactive: bool = False) -> list[dict]:
    sql = "SELECT * FROM wards"
    if not include_inactive:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY CAST(IFNULL(ward_no, '999') AS INTEGER), name"
    return [dict(r) for r in query_all(conn, sql)]


def load_wards(conn, path: str | Path, actor: str = "dataset_import") -> dict:
    """Bulk-load the ward master list once the council supplies it.

    Accepts either a bare JSON list or ``{"wards": [...]}``. Every row keeps the
    confidence it declares, so a partially verified dataset stays partially
    verified instead of being promoted wholesale.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("wards") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ValueError("ward file must be a list or {'wards': [...]}")
    loaded = [upsert_ward(conn, row, actor)["id"] for row in rows]
    return {"loaded": len(loaded), "ward_ids": loaded,
            "source": str(path), "actor": actor}


def coverage(conn) -> dict:
    """What the council would have to fill in for equity to become verified."""
    stats = ward_stats(conn)
    return {
        "ward_count": stats["ward_count"],
        "with_population_and_area": stats["with_population_and_area"],
        "with_equity_index": stats["with_equity_index"],
        "council_totals_for_reference": {
            "population": COUNCIL_POPULATION,
            "area_sq_km": COUNCIL_AREA_SQ_KM,
            "source": "Kopargaon Municipal Council area figures",
        },
        "gap": ("no ward master list, ward population or equity index exists in "
                "the accessible datasets; C3_equity stays a wide fuzzy interval "
                "flagged equity_unverified until these are entered"),
    }


if __name__ == "__main__":  # pragma: no cover
    from database import get_conn, init_db

    init_db()
    with get_conn() as c:
        print("resolve 'Ward-7':", resolve_ward(c, "Ward-7")["ward_id"])
        print("resolve '3':", resolve_ward(c, "3")["ward_id"])
        print("resolve none:", resolve_ward(c, None)["method"])
        upsert_ward(c, {"id": "W7", "population": 6100, "area_sq_km": 0.82,
                        "data_confidence": "operator_entered"}, "selftest")
        print("stats:", ward_stats(c))
        print("coverage gap:", coverage(c)["with_population_and_area"])
        print("wards:", [w["id"] for w in list_wards(c)])
