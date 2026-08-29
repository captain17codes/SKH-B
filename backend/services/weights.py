"""Versioned criteria weights: derive, store, activate, compare.

The gate lives here rather than in ``domain.ahp`` because refusing to *use* a set
of weights is a policy decision, while computing them is arithmetic. A panel is
always allowed to see what their inconsistent judgements would produce; they are
not allowed to prioritise real work with it.

Three rules this module exists to enforce:

* **Nothing is overwritten.** ``criteria_weights`` is append-only; activating a
  new version deactivates the previous one but leaves it readable, so a manifest
  produced last Tuesday can still be explained with Tuesday's weights.
* **CR >= 0.10 cannot become active.** ``save`` will store a failed derivation
  (it is evidence of what the panel said) but ``activate`` refuses it, and
  ``derive_and_save`` reports the refusal instead of silently falling back.
* **There is always exactly one active row.** The engine must never have to guess
  which weights are current, so ``get_active`` seeds the declared default on
  first call rather than returning None and letting the caller invent something.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    from database import dumps, execute, loads, query_all, query_one, utcnow_iso
    from domain import ahp
    from domain.criteria import CRITERIA, CRITERIA_TYPES
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from database import dumps, execute, loads, query_all, query_one, utcnow_iso
    from domain import ahp
    from domain.criteria import CRITERIA, CRITERIA_TYPES


def _row_to_dict(row: Any) -> dict:
    """Inflate the JSON columns so callers never parse them by hand."""
    out = dict(row)
    for key in ("criteria", "criteria_types", "pairwise_matrix",
                "fuzzy_weights", "crisp_weights"):
        out[key] = loads(out.get(key))
    out["cr_passed"] = bool(out.get("cr_passed"))
    out["is_active"] = bool(out.get("is_active"))
    return out


def save(conn, derivation: dict, *, label: str | None = None,
         created_by: str | None = None, note: str | None = None,
         activate: bool = False) -> dict:
    """Append one weight version. Returns the stored row.

    ``activate=True`` is a request, not a guarantee: if the derivation failed the
    consistency gate the row is still written but stays inactive, and the caller
    is told why in ``activation``.
    """
    check = derivation.get("consistency", {})
    passed = bool(derivation.get("cr_passed", check.get("passed", False)))
    now = utcnow_iso()
    execute(conn,
            "INSERT INTO criteria_weights(label, criteria, criteria_types,"
            " pairwise_matrix, fuzzy_weights, crisp_weights, consistency_ratio,"
            " cr_threshold, cr_passed, method, is_active, created_by, note,"
            " created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (label or derivation.get("label") or "unlabelled",
             dumps(derivation.get("criteria") or CRITERIA),
             dumps(derivation.get("criteria_types")
                   or [CRITERIA_TYPES[c] for c in CRITERIA]),
             dumps(derivation.get("pairwise_matrix")),
             dumps(derivation["fuzzy_weights"]),
             dumps(derivation["crisp_weights"]),
             check.get("consistency_ratio"),
             check.get("threshold", ahp.CR_THRESHOLD),
             1 if passed else 0,
             derivation.get("method", "buckley_geometric_mean"),
             0, created_by,
             note or derivation.get("note"), now))
    version = int(query_one(conn, "SELECT MAX(version) AS v FROM criteria_weights")["v"])
    stored = get_version(conn, version) or {}
    if activate:
        stored["activation"] = activate_version(conn, version, created_by)
    else:
        stored["activation"] = {"activated": False,
                               "reason": "stored without activation"}
    return stored


def activate_version(conn, version: int, actor: str | None = None) -> dict:
    """Make one stored version the live one, refusing inconsistent judgements."""
    row = query_one(conn, "SELECT * FROM criteria_weights WHERE version = ?",
                    (version,))
    if not row:
        return {"activated": False, "reason": f"version {version} does not exist"}
    if not row["cr_passed"]:
        return {
            "activated": False,
            "version": version,
            "consistency_ratio": row["consistency_ratio"],
            "threshold": row["cr_threshold"],
            "reason": (f"consistency ratio {row['consistency_ratio']} is not below "
                       f"{row['cr_threshold']}; the pairwise judgements contradict "
                       "each other, so weights derived from them cannot be used to "
                       "rank citizens' work. Revisit the flagged comparison and "
                       "resubmit."),
        }
    execute(conn, "UPDATE criteria_weights SET is_active = 0 WHERE is_active = 1")
    execute(conn, "UPDATE criteria_weights SET is_active = 1 WHERE version = ?",
            (version,))
    return {"activated": True, "version": version, "actor": actor,
            "consistency_ratio": row["consistency_ratio"]}


def get_version(conn, version: int) -> dict | None:
    row = query_one(conn, "SELECT * FROM criteria_weights WHERE version = ?",
                    (version,))
    return _row_to_dict(row) if row else None


def get_active(conn, seed_if_missing: bool = True) -> dict:
    """The weights the engine must use. Seeds the declared default on first call.

    Returning None here would push the decision "what weights should I use?" into
    the scorer, which is exactly where an undocumented constant would end up.
    """
    row = query_one(conn, "SELECT * FROM criteria_weights WHERE is_active = 1 "
                          "ORDER BY version DESC LIMIT 1")
    if row:
        return _row_to_dict(row)
    if not seed_if_missing:
        return {}
    seeded = save(conn, ahp.default_derivation(),
                  label="seed_v1_published_priority_floors",
                  created_by="system_default", activate=True)
    return get_active(conn, seed_if_missing=False) or seeded


def active_vector(conn) -> tuple[dict[str, float], int]:
    """``({criterion: weight}, version)`` -- what TOPSIS multiplies."""
    active = get_active(conn)
    weights = {k: float(v) for k, v in (active.get("crisp_weights") or {}).items()}
    missing = [c for c in CRITERIA if c not in weights]
    if missing:
        # A stored vector that no longer covers the criteria list would silently
        # drop a criterion from every ranking; fall back to the declared default.
        default = ahp.default_derivation()
        weights = {k: float(v) for k, v in default["crisp_weights"].items()}
        return weights, int(active.get("version") or 0)
    return weights, int(active.get("version") or 0)


def list_versions(conn, limit: int = 50) -> list[dict]:
    rows = query_all(conn, "SELECT * FROM criteria_weights ORDER BY version DESC "
                           "LIMIT ?", (int(limit),))
    return [_row_to_dict(r) for r in rows]


def derive_and_save(conn, judgements: dict | Iterable[dict] | None = None,
                    matrix: Sequence[Sequence[Sequence[float]]] | None = None,
                    *, label: str | None = None, created_by: str | None = None,
                    note: str | None = None, activate: bool = True,
                    criteria: Sequence[str] | None = None) -> dict:
    """Panel submits comparisons; we derive, gate, store and report.

    The response deliberately contains both the weights and the reason they were
    or were not adopted, so the UI can show a panel the consequence of their own
    judgements in one round trip.
    """
    derivation = ahp.derive(judgements=judgements, matrix=matrix,
                            criteria=criteria)
    stored = save(conn, derivation, label=label, created_by=created_by,
                  note=note, activate=activate)
    return {
        "version": stored.get("version"),
        "crisp_weights": derivation["crisp_weights"],
        "fuzzy_weights": derivation["fuzzy_weights"],
        "consistency": derivation["consistency"],
        "cr_passed": derivation["cr_passed"],
        "activation": stored.get("activation"),
        "active_version": get_active(conn).get("version"),
        "method": derivation["method"],
        "scale": {label_: list(tfn)
                  for label_, tfn in ahp.LINGUISTIC_SCALE.items()},
    }


def compare_versions(conn, left: int, right: int) -> dict:
    """Per-criterion difference between two weight sets.

    Used when someone asks "would last month's weights have scheduled this
    ticket?" -- a question the platform should be able to answer rather than
    deflect.
    """
    a, b = get_version(conn, left), get_version(conn, right)
    if not a or not b:
        return {"error": "one or both versions do not exist"}
    names = sorted(set(a["crisp_weights"]) | set(b["crisp_weights"]))
    delta = {n: round(float(b["crisp_weights"].get(n, 0.0))
                      - float(a["crisp_weights"].get(n, 0.0)), 6)
             for n in names}
    shifted = max(delta, key=lambda n: abs(delta[n])) if delta else None
    return {"from_version": left, "to_version": right,
            "from_weights": a["crisp_weights"], "to_weights": b["crisp_weights"],
            "delta": delta, "largest_shift": shifted,
            "from_cr": a["consistency_ratio"], "to_cr": b["consistency_ratio"]}


def explain_active(conn) -> dict:
    """Plain-language account of the live weights, for the audit trail and UI."""
    active = get_active(conn)
    weights = active.get("crisp_weights") or {}
    order = sorted(weights, key=lambda k: -float(weights[k]))
    readable = {"C1_infra": "infrastructural criticality",
                "C2_safety": "public safety and health risk",
                "C3_equity": "socio-spatial equity",
                "C4_cost": "resource requirement"}
    ranked = ", ".join(f"{readable.get(n, n)} {float(weights[n]):.0%}"
                       for n in order)
    return {
        "version": active.get("version"),
        "label": active.get("label"),
        "weights": weights,
        "fuzzy_weights": active.get("fuzzy_weights"),
        "consistency_ratio": active.get("consistency_ratio"),
        "cr_threshold": active.get("cr_threshold"),
        "created_by": active.get("created_by"),
        "created_at": active.get("created_at"),
        "note": active.get("note"),
        "summary": (f"Weights version {active.get('version')} are in force: "
                    f"{ranked}. They were derived by fuzzy AHP (Buckley geometric "
                    f"mean) from pairwise judgements whose consistency ratio is "
                    f"{active.get('consistency_ratio')}, below the 0.10 limit."),
        "criteria_types": {c: CRITERIA_TYPES[c] for c in CRITERIA},
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    from database import get_conn, init_db

    init_db()
    with get_conn() as c:
        c.execute("DELETE FROM criteria_weights")
        print("active (seeds):", json.dumps(active_vector(c)))
        print("explain:", explain_active(c)["summary"])

        good = derive_and_save(c, {
            "C2_safety vs C1_infra": "moderate",
            "C2_safety vs C3_equity": "moderate_to_strong",
            "C2_safety vs C4_cost": "strong",
            "C1_infra vs C3_equity": "equal_to_moderate",
            "C1_infra vs C4_cost": "moderate",
            "C3_equity vs C4_cost": "equal_to_moderate",
        }, label="engineering_panel_dry_run", created_by="selftest")
        print("panel v", good["version"], "CR", good["consistency"]["consistency_ratio"],
              "->", good["activation"])
        print("weights:", json.dumps(good["crisp_weights"]))

        bad = derive_and_save(c, {
            "C2_safety vs C1_infra": "moderate",
            "C2_safety vs C3_equity": "inverse_strong",
            "C2_safety vs C4_cost": "strong",
            "C1_infra vs C3_equity": "equal_to_moderate",
            "C1_infra vs C4_cost": "moderate",
            "C3_equity vs C4_cost": "very_strong",
        }, label="contradictory_panel", created_by="selftest")
        print("bad v", bad["version"], "CR", bad["consistency"]["consistency_ratio"])
        print("refused:", bad["activation"]["activated"], "-",
              bad["activation"]["reason"][:90], "...")
        print("still active:", active_vector(c)[1], "(inconsistent set rejected)")
        print("compare:", json.dumps(compare_versions(
            c, good["version"], bad["version"])["delta"]))
        print("versions:", [(v["version"], v["label"], v["is_active"])
                            for v in list_versions(c)])
