"""
Derivation of the four decision criteria for one ticket.

C1 Infrastructural Criticality   (benefit)
C2 Public Safety & Health Risk   (benefit)
C3 Socio-Spatial Equity          (benefit)
C4 Resource Requirement          (cost)

Each criterion is produced as a triangular fuzzy number (TFN) plus a confidence
in [0, 1]. Confidence controls the *width* of the TFN, which is the mechanism
that lets the platform reason with incomplete data instead of refusing to: a
fact we know well becomes a narrow interval that moves the ranking, a fact we do
not know becomes a wide interval that mostly cancels out and is reported as
unverified rather than assumed.

Nothing here is a per-category constant table. C1 is derived from the council's
own published response target for the category, C2 from the published priority
floors and sensitive-site rules, C3 from ward data (or an explicit gap), C4 from
the costing module.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

try:
    from config import settings
    from domain.costing import estimate_cost
    from domain.reference import ReferenceData, get_reference
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings
    from domain.costing import estimate_cost
    from domain.reference import ReferenceData, get_reference


CRITERIA = ["C1_infra", "C2_safety", "C3_equity", "C4_cost"]
CRITERIA_TYPES = {"C1_infra": "benefit", "C2_safety": "benefit",
                  "C3_equity": "benefit", "C4_cost": "cost"}

# Maximum total width of a TFN at zero confidence.
MAX_TFN_SPREAD = 0.60

# C1 anchors: the council's own published operational response target is the best
# available published proxy for how critical it considers a category. Tighter
# target -> higher infrastructural criticality. Interpolated in log-minutes so
# 30 vs 60 minutes matters more than 1400 vs 1440.
TARGET_CRITICALITY_ANCHORS = [
    (0.0, 1.00),
    (30.0, 0.92),
    (60.0, 0.85),
    (120.0, 0.75),
    (180.0, 0.68),
    (240.0, 0.62),
    (1440.0, 0.35),
]

# Baseline public-health/safety exposure per category, used only when the SLA
# matrix declares no priority floor. Ordered by the health pathway each category
# opens (waterborne > vector > accumulation > amenity).
SAFETY_BASELINE = {
    "stp_treatment_quality_alert": 0.72,
    "water_leakage": 0.50,
    "water_distribution_failure": 0.62,
    "pump_or_electrical_failure": 0.55,
    "flood_related_waste_accumulation": 0.66,
    "heavy_silt_or_flood_debris": 0.64,
    "drain_blockage": 0.58,
    "mosquito_or_vector_control": 0.60,
    "missed_waste_collection": 0.45,
    "road_damage": 0.50,
    "stp_inlet_blockage": 0.52,
    "stp_aeration_failure": 0.52,
    "stp_sludge_handling_issue": 0.48,
    "street_light_fault": 0.40,
    "general_infrastructure": 0.42,
    "unclassified": 0.35,
}

SENSITIVE_SITE_WEIGHT = {
    "hospital": 0.10,
    "school": 0.06,
    "market": 0.05,
    "dense_population_zone": 0.05,
}

# Population above which the affected-population signal saturates. Kopargaon is
# ~65,273 people across the council area, so a single incident affecting 5,000
# residents is already a large share of one ward.
POPULATION_SATURATION = 5000.0


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def make_tfn(center: float, confidence: float, skew: float = 0.0,
             max_spread: float = MAX_TFN_SPREAD) -> tuple[float, float, float]:
    """Triangular fuzzy number whose width encodes ignorance.

    ``confidence`` 1.0 gives a crisp point; 0.0 gives the widest admissible
    interval. ``skew`` in [-1, 1] biases the width upward (+) or downward (-),
    used when a known value is structurally an under-estimate, e.g. a partial
    cost that is missing its labour line.
    """
    confidence = clamp(confidence)
    skew = max(-1.0, min(1.0, skew))
    half = (1.0 - confidence) * max_spread / 2.0
    modal = clamp(center)
    lower = clamp(modal - half * (1.0 - skew))
    upper = clamp(modal + half * (1.0 + skew))
    # Keep a hair of width so the TOPSIS vertex distance never degenerates.
    if upper - lower < 1e-6:
        lower = clamp(modal - 1e-3)
        upper = clamp(modal + 1e-3)
    return (round(lower, 6), round(modal, 6), round(upper, 6))


def _interp_anchors(x: float,
                    anchors: list[tuple[float, float]]) -> float:
    """Piecewise-linear interpolation in log10(x + 1) space."""
    lx = math.log10(x + 1.0)
    pts = [(math.log10(a + 1.0), v) for a, v in anchors]
    if lx <= pts[0][0]:
        return pts[0][1]
    if lx >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= lx <= x1:
            if x1 == x0:
                return y1
            t = (lx - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return pts[-1][1]


def resolve_priority_floor(spec, ticket: dict) -> tuple[str | None, str | None]:
    """Normalise the dataset's priority_floor, including the conditional one.

    ``flood_road_blockage`` carries the floor
    ``critical_if_people_or_critical_facilities_isolated`` -- a condition, not a
    verdict. It only becomes critical when the operator or reporter actually
    flags isolation, otherwise it stays high and the reason says why.
    """
    floor = (spec.priority_floor or "").strip()
    if not floor:
        return None, None
    low = floor.lower()
    if low == "critical":
        return "critical", f"dataset priority_floor=critical for {spec.incident_type}"
    if low.startswith("critical_if"):
        isolated = bool(ticket.get("access_isolated")
                        or ticket.get("critical_facility_isolated"))
        if isolated:
            return "critical", ("conditional floor met: access or critical "
                                "facility reported isolated")
        return "high", ("conditional floor not confirmed "
                        f"({floor}); held at high pending operator confirmation")
    if low == "high":
        return "high", f"dataset priority_floor=HIGH for {spec.incident_type}"
    return low, f"dataset priority_floor={floor}"


def _sensitive_boost(ticket: dict) -> tuple[float, str | None]:
    site = (ticket.get("sensitive_site") or "").strip().lower()
    if not site:
        return 0.0, None
    return SENSITIVE_SITE_WEIGHT.get(site, 0.03), site


def _population_signal(ticket: dict, ward: dict | None) -> tuple[float, bool]:
    """0..1 share-of-population signal, plus whether it was actually known."""
    pop = ticket.get("affected_population")
    if pop is None:
        return 0.0, False
    pop = max(0.0, float(pop))
    ward_pop = (ward or {}).get("population")
    if ward_pop:
        return clamp(pop / float(ward_pop)), True
    return clamp(math.log10(1.0 + pop) /
                 math.log10(1.0 + POPULATION_SATURATION)), True


def _c1_infra(ticket: dict, spec) -> dict:
    evidence: dict[str, Any] = {}
    target = spec.response_target_minutes
    if target is not None:
        center = _interp_anchors(target, TARGET_CRITICALITY_ANCHORS)
        confidence = 0.85
        evidence["response_target_minutes"] = target
        evidence["basis"] = "derived_from_published_operational_response_target"
        evidence["target_provenance"] = spec.target_provenance
    else:
        center, confidence = 0.50, 0.28
        evidence["basis"] = "no_published_response_target_for_this_category"
    boost, site = _sensitive_boost(ticket)
    if site:
        center += boost * 0.8
        evidence["sensitive_site"] = site
    if ticket.get("blocks_major_road"):
        center += 0.08
        evidence["blocks_major_road"] = True
    if spec.is_statutory_rts or (spec.related_rts_days or 99) <= 3:
        center += 0.05
        evidence["statutory_link"] = (spec.related_rts_service_id
                                      or "is_statutory_rts")
    if spec.department_id is None and spec.external_handoff:
        evidence["external_handoff"] = list(spec.external_handoff)
    return {"center": clamp(center), "confidence": confidence,
            "evidence": evidence,
            "source": "derived_from_kopargaon_sla_matrix"}


def _c2_safety(ticket: dict, spec, ward: dict | None,
               floor: str | None, floor_reason: str | None) -> dict:
    evidence: dict[str, Any] = {}
    if floor == "critical":
        center, confidence = 0.97, 0.90
        evidence["priority_floor"] = "critical"
    elif floor == "high":
        center, confidence = 0.80, 0.80
        evidence["priority_floor"] = "high"
    else:
        center = SAFETY_BASELINE.get(spec.incident_type, 0.45)
        confidence = 0.60
        evidence["priority_floor"] = None
        evidence["baseline_for_category"] = center
    if floor_reason:
        evidence["floor_reason"] = floor_reason

    boost, site = _sensitive_boost(ticket)
    if site:
        center += boost
        evidence["sensitive_site"] = site
        confidence = min(0.92, confidence + 0.05)

    pop_signal, pop_known = _population_signal(ticket, ward)
    if pop_known:
        center += 0.12 * pop_signal
        evidence["affected_population"] = ticket.get("affected_population")
        evidence["population_signal"] = round(pop_signal, 4)
    else:
        confidence -= 0.15
        evidence["affected_population"] = None

    # Duration *of the disruption itself* (e.g. 30 hours without water). This is
    # not the same thing as how long the ticket has been open, which the SLA
    # urgency bonus handles separately -- counting it twice would inflate safety.
    duration = ticket.get("duration_hours")
    if duration is not None and spec.response_target_minutes:
        ratio = float(duration) * 60.0 / max(spec.response_target_minutes, 1.0)
        center += 0.10 * clamp(ratio / 4.0)
        evidence["duration_hours"] = float(duration)
    return {"center": clamp(center), "confidence": clamp(confidence),
            "evidence": evidence,
            "source": "derived_from_priority_floors_and_sensitive_sites"}


def _c3_equity(ticket: dict, ward: dict | None,
               ward_stats: dict | None) -> dict:
    """Socio-spatial equity.

    No Kopargaon dataset contains a ward master list, ward populations or any
    equity index, so this criterion is the platform's honest-ignorance case:

      * verified equity_index      -> narrow interval, high confidence
      * population + area only     -> density proxy, medium-low confidence
      * nothing                    -> wide interval, flagged unverified

    A wide interval still participates in TOPSIS; it just cannot dominate the
    ranking, which is the correct behaviour for a number nobody has verified.
    """
    evidence: dict[str, Any] = {"ward_id": (ward or {}).get("id")}
    if not ward:
        evidence["basis"] = "no_ward_resolved_for_this_ticket"
        return {"center": 0.5, "confidence": 0.10, "evidence": evidence,
                "source": "unverified_no_ward_data",
                "flags": ["equity_unverified"]}

    evidence["ward_name"] = ward.get("name")
    index = ward.get("equity_index")
    confidence_label = (ward.get("data_confidence") or "unverified").lower()
    if index is not None:
        confidence = {"verified": 0.88, "operator_entered": 0.62}.get(
            confidence_label, 0.40)
        evidence["basis"] = "ward_equity_index"
        evidence["equity_index"] = float(index)
        evidence["ward_data_confidence"] = confidence_label
        return {"center": clamp(float(index)), "confidence": confidence,
                "evidence": evidence, "source": f"ward_equity_index:{confidence_label}",
                "flags": [] if confidence_label == "verified"
                         else ["equity_operator_entered"]}

    pop, area = ward.get("population"), ward.get("area_sq_km")
    densities = (ward_stats or {}).get("densities") or []
    if pop and area:
        density = float(pop) / max(float(area), 1e-6)
        evidence["basis"] = "population_density_proxy"
        evidence["density_per_sq_km"] = round(density, 2)
        if len(densities) >= 3:
            rank = sum(1 for d in densities if d <= density) / len(densities)
        else:
            rank = clamp(density / 12000.0)
        evidence["density_percentile"] = round(rank, 4)
        return {"center": clamp(0.25 + 0.5 * rank), "confidence": 0.45,
                "evidence": evidence, "source": "density_proxy_no_equity_index",
                "flags": ["equity_proxy_from_density", "equity_index_absent"]}

    evidence["basis"] = "ward_exists_but_population_and_equity_index_unknown"
    return {"center": 0.5, "confidence": 0.12, "evidence": evidence,
            "source": "unverified_ward_attributes",
            "flags": ["equity_unverified"]}


def _c4_cost(cost_estimate: dict) -> dict:
    """Resource requirement -- the only *cost* criterion, so a higher value must
    push the closeness coefficient down.

    Blends money (60%) with crew hours (40%) because the council is constrained
    by both, and the knapsack enforces both separately afterwards.
    """
    budget_ref = max(settings.DEFAULT_DAILY_BUDGET, 1.0)
    hours_ref = max(settings.DEFAULT_DAILY_WORKFORCE_HOURS, 1.0)
    hours = float(cost_estimate.get("estimated_hours") or 0.0)
    hours_norm = clamp(hours / hours_ref)
    evidence: dict[str, Any] = {
        "estimated_hours": hours,
        "hours_normaliser": hours_ref,
        "hours_provenance": cost_estimate.get("hours_provenance"),
        "cost_status": cost_estimate.get("cost_status"),
        "cost_method": cost_estimate.get("cost_method"),
    }
    cost = cost_estimate.get("estimated_cost_inr")
    partial = cost_estimate.get("partial_cost_inr")

    if cost is not None:
        cost_norm = clamp(float(cost) / budget_ref)
        center = 0.6 * cost_norm + 0.4 * hours_norm
        confidence = 0.80 if cost_estimate.get(
            "cost_confidence") == "verified_reference" else 0.70
        evidence["estimated_cost_inr"] = float(cost)
        evidence["basis"] = "verified_and_operator_cost_lines"
        return {"center": clamp(center), "confidence": confidence,
                "evidence": evidence, "source": "cost_complete", "flags": []}

    if partial:
        cost_norm = clamp(float(partial) / budget_ref)
        center = 0.6 * cost_norm + 0.4 * hours_norm
        evidence["partial_cost_inr"] = float(partial)
        evidence["missing_inputs"] = cost_estimate.get("missing_inputs")
        evidence["basis"] = "partial_verified_machine_cost_only"
        # A partial cost is structurally an under-estimate, so the interval is
        # skewed upward rather than centred.
        return {"center": clamp(center), "confidence": 0.38, "skew": 0.6,
                "evidence": evidence, "source": "cost_incomplete_partial",
                "flags": ["cost_incomplete"]}

    evidence["basis"] = "crew_hours_only_no_verified_or_entered_cost"
    evidence["missing_inputs"] = cost_estimate.get("missing_inputs")
    return {"center": clamp(hours_norm), "confidence": 0.26, "skew": 0.7,
            "evidence": evidence, "source": "cost_unknown",
            "flags": ["cost_incomplete", "cost_unknown"]}


def derive_criteria(ticket: dict,
                    ward: dict | None = None,
                    ward_stats: dict | None = None,
                    ref: ReferenceData | None = None,
                    cost_estimate: dict | None = None) -> dict:
    """Derive C1..C4 for one ticket as TFNs with per-criterion provenance.

    ``ticket`` is a plain dict (DB row or request payload). Recognised optional
    keys: ``category`` / ``incident_type``, ``sensitive_site``,
    ``affected_population``, ``duration_hours``, ``blocks_major_road``,
    ``access_isolated`` / ``critical_facility_isolated``.

    The return value is shaped for direct persistence into
    ``ticket_criteria_scores`` and for the explanation endpoint: every criterion
    carries the interval, the confidence that produced its width, a machine
    source tag and the evidence dict that a human can audit.
    """
    ref = ref or get_reference()
    category = (ticket.get("incident_type") or ticket.get("category")
                or "unclassified")
    canonical = ref.canonical_category(category)
    spec = ref.incident(canonical)

    if cost_estimate is None:
        cost_estimate = estimate_cost(canonical,
                                      ticket.get("cost_inputs"), ref)

    floor, floor_reason = resolve_priority_floor(spec, ticket)

    raw = {
        "C1_infra": _c1_infra(ticket, spec),
        "C2_safety": _c2_safety(ticket, spec, ward, floor, floor_reason),
        "C3_equity": _c3_equity(ticket, ward, ward_stats),
        "C4_cost": _c4_cost(cost_estimate),
    }

    scores: dict[str, dict] = {}
    flags: list[str] = []
    confidences: list[float] = []
    for name in CRITERIA:
        part = raw[name]
        tfn = make_tfn(part["center"], part["confidence"],
                       part.get("skew", 0.0))
        confidences.append(float(part["confidence"]))
        scores[name] = {
            "criterion": name,
            "type": CRITERIA_TYPES[name],
            "tfn": list(tfn),
            "tfn_lower": tfn[0],
            "tfn_modal": tfn[1],
            "tfn_upper": tfn[2],
            "confidence": round(clamp(float(part["confidence"])), 4),
            "source": part.get("source", "derived"),
            "evidence": part.get("evidence", {}),
        }
        for flag in part.get("flags", []) or []:
            if flag not in flags:
                flags.append(flag)

    overall = round(sum(confidences) / len(confidences), 4)
    if overall < 0.45 and "low_overall_confidence" not in flags:
        flags.append("low_overall_confidence")

    return {
        "incident_type": canonical,
        "requested_category": category,
        "department_id": spec.department_id,
        "scores": scores,
        "priority_floor": floor,
        "priority_floor_reason": floor_reason,
        "response_target_minutes": spec.response_target_minutes,
        "target_provenance": spec.target_provenance,
        "is_statutory_rts": spec.is_statutory_rts,
        "rts_service_id": spec.related_rts_service_id,
        "rts_time_limit_days": spec.related_rts_days,
        "external_handoff": list(spec.external_handoff),
        "cost_estimate": cost_estimate,
        "overall_confidence": overall,
        "flags": flags,
        "method": "confidence_weighted_triangular_fuzzy_numbers",
    }


def criteria_matrix(derived: list[dict]) -> dict:
    """Pack many ``derive_criteria`` results into the engine's matrix format.

    ``run_prioritization`` expects ``criteria_config['names'|'types']`` and one
    row of TFNs per alternative, so this is the single place that decides column
    order. Keeping it here means the engine never has to know about tickets.
    """
    rows = []
    for item in derived:
        rows.append([item["scores"][name]["tfn"] for name in CRITERIA])
    return {
        "names": list(CRITERIA),
        "types": [CRITERIA_TYPES[name] for name in CRITERIA],
        "matrix": rows,
    }


if __name__ == "__main__":  # pragma: no cover
    import json

    samples = [
        {"category": "water_quality", "sensitive_site": "hospital",
         "affected_population": 2400, "duration_hours": 6},
        {"category": "drainage", "affected_population": None},
        {"category": "waterlogging", "access_isolated": True,
         "blocks_major_road": True},
        {"category": "streetlight"},
    ]
    derived = [derive_criteria(t) for t in samples]
    for t, d in zip(samples, derived):
        print(f"\n=== {t['category']} -> {d['incident_type']} "
              f"(floor={d['priority_floor']}, conf={d['overall_confidence']})")
        for name in CRITERIA:
            s = d["scores"][name]
            print(f"  {name:10s} {s['tfn']}  conf={s['confidence']:.2f}  "
                  f"{s['source']}")
        print("  flags:", d["flags"])
    print("\nmatrix:", json.dumps(criteria_matrix(derived)["types"]))
