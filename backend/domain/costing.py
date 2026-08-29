"""
Response cost and effort estimation.

Two hard rules from ``kopargaon_water_waste_operational_rules_cost_matrix_v1``:

* only the eight accepted-L1 hourly machine rates are verified money; water and
  waste have **no** verified unit rate in accessible public records;
* if a required cost is unknown the line is ``null`` and the ticket is flagged
  ``COST_INCOMPLETE`` -- never zero. Zero means a verified zero.

So this module produces a partial cost with per-line provenance, and the triage
engine decides what to do with an incomplete one (it does not silently drop it).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from domain.reference import ReferenceData, get_reference
except ImportError:  # pragma: no cover
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from domain.reference import ReferenceData, get_reference


# Machine hours and crew hours are an operational *assumption*, not a sourced
# fact: the tenders prove which machines are used, never for how long. Every
# line produced from this table is stamped
# provenance='policy_assumption_editable_by_operator'.
DEFAULT_RESPONSE_PLANS: dict[str, dict[str, Any]] = {
    "drain_blockage": {"equipment": {"JCB_3DX": 2.0}, "crew_hours": 4.0},
    "heavy_silt_or_flood_debris": {
        "equipment": {"POCLAIN_210": 3.0, "DUMPER_6W": 3.0}, "crew_hours": 6.0},
    "flood_road_blockage": {
        "equipment": {"JCB_3DX": 3.0, "DUMPER_10W": 3.0}, "crew_hours": 6.0},
    "flood_related_waste_accumulation": {
        "equipment": {"TRACTOR_TROLLEY_4W": 4.0}, "crew_hours": 6.0},
    "missed_waste_collection": {"equipment": {}, "crew_hours": 3.0},
    "waste_overflow_near_sensitive_site": {
        "equipment": {"TRACTOR_TROLLEY_4W": 2.0}, "crew_hours": 4.0},
    "road_damage": {"equipment": {"JCB_3DX": 2.0}, "crew_hours": 5.0},
    "water_leakage": {"equipment": {}, "crew_hours": 4.0},
    "water_quality_alert": {"equipment": {}, "crew_hours": 3.0},
    "major_water_distribution_failure": {
        "equipment": {"JCB_3DX": 2.0}, "crew_hours": 8.0},
    "water_distribution_failure": {"equipment": {}, "crew_hours": 6.0},
    "pump_or_electrical_failure": {"equipment": {}, "crew_hours": 4.0},
    "mosquito_or_vector_control": {"equipment": {}, "crew_hours": 3.0},
}

DEFAULT_RESPONSE_PLANS.update({
    "stp_inlet_blockage": {"equipment": {}, "crew_hours": 4.0},
    "stp_aeration_failure": {"equipment": {}, "crew_hours": 5.0},
    "stp_treatment_quality_alert": {"equipment": {}, "crew_hours": 3.0},
    "stp_sludge_handling_issue": {
        "equipment": {"DUMPER_6W": 2.0}, "crew_hours": 4.0},
    "street_light_fault": {"equipment": {}, "crew_hours": 2.0},
    "general_infrastructure": {"equipment": {}, "crew_hours": 4.0},
    "unclassified": {"equipment": {}, "crew_hours": 2.0},
    # Life-safety categories are external handoffs; municipal cost is not the
    # decision variable and must not be invented.
    "medical_emergency": {"equipment": {}, "crew_hours": 0.0},
    "fire_or_immediate_life_safety": {"equipment": {}, "crew_hours": 1.0},
})

# Operator-entered money fields. Recognised on the cost PATCH endpoint.
RUNTIME_COST_FIELDS = (
    "runtime_vehicle_cost",
    "runtime_labour_cost",
    "runtime_material_cost",
    "other_cost",
)

COST_COMPLETE = "COST_COMPLETE"
COST_INCOMPLETE = "COST_INCOMPLETE"


def response_plan(category: str, ref: ReferenceData | None = None) -> dict:
    """Equipment hours + crew hours assumed for one incident category."""
    ref = ref or get_reference()
    key = ref.canonical_category(category)
    plan = DEFAULT_RESPONSE_PLANS.get(key)
    if plan is None:
        return {"equipment": {}, "crew_hours": 4.0,
                "provenance": "generic_fallback_no_plan_for_category"}
    return {
        "equipment": dict(plan["equipment"]),
        "crew_hours": float(plan["crew_hours"]),
        "provenance": "policy_assumption_editable_by_operator",
    }


def estimate_cost(category: str,
                  operator_inputs: dict | None = None,
                  ref: ReferenceData | None = None) -> dict:
    """Estimate the response cost for one ticket.

    Returns a dict with:
      ``estimated_cost_inr``  float or None (None => unknown, never 0)
      ``cost_status``         COST_COMPLETE | COST_INCOMPLETE
      ``cost_confidence``     verified_reference | mixed | operator_entered | none
      ``estimated_hours``     crew hours used as the workforce constraint
      ``line_items``          per-line amount + source + confidence
      ``missing_inputs``      which required cost inputs are still unknown
    """
    ref = ref or get_reference()
    spec = ref.incident(category)
    inputs = dict(operator_inputs or {})
    plan = response_plan(category, ref)

    equipment_hours = inputs.get("equipment_hours") or plan["equipment"]
    crew_hours = inputs.get("crew_hours")
    crew_hours = float(crew_hours) if crew_hours is not None else plan["crew_hours"]

    line_items: list[dict] = []
    machine_total = 0.0
    machine_unknown = False

    for code, hours in (equipment_hours or {}).items():
        code = str(code).upper()
        hours = float(hours or 0.0)
        rate = ref.equipment_rate(code)
        entry = ref.equipment_rates.get(code, {})
        amount = None if rate is None else round(rate * hours, 2)
        if amount is None:
            machine_unknown = True
        else:
            machine_total += amount
        line_items.append({
            "item": entry.get("display_name") or code,
            "resource_code": code,
            "hours": hours,
            "rate_inr_per_hour": rate,
            "amount_inr": amount,
            "source": ("accepted_L1_financial_bid_" + str(entry.get("tender_id"))
                       if rate is not None else "no_verified_unit_rate"),
            "confidence": entry.get("confidence") if rate is not None else "none",
            "hours_provenance": plan["provenance"],
        })

    runtime_total = 0.0
    runtime_entered = False
    for field_name in RUNTIME_COST_FIELDS:
        value = inputs.get(field_name)
        if value is None:
            line_items.append({
                "item": field_name,
                "amount_inr": None,
                "source": "operator_entered_required",
                "confidence": "none",
            })
            continue
        runtime_entered = True
        runtime_total += float(value)
        line_items.append({
            "item": field_name,
            "amount_inr": round(float(value), 2),
            "source": "operator_entered",
            "confidence": "operator_verified",
            "note": inputs.get(f"{field_name}_note"),
        })

    # Which of the dataset's declared required inputs are still unknown.
    missing = [f for f in RUNTIME_COST_FIELDS if inputs.get(f) is None]
    declared_required = list(spec.required_cost_inputs)

    # Any cost_method mentioning "runtime" means the dataset itself says part of
    # the money can only come from an operator. drain_blockage, for instance, is
    # "reference_machine_rate_plus_runtime_labour_materials": the machine line is
    # verified, the labour and materials are not, so the total stays unknown.
    method = spec.cost_method or "runtime_input"
    needs_runtime = "runtime" in method
    complete = (not machine_unknown) and (runtime_entered or not needs_runtime)
    # A category with no verified rate and no operator money is simply unknown.
    if not equipment_hours and not runtime_entered:
        complete = False

    total = machine_total + runtime_total
    has_any_money = (machine_total > 0) or runtime_entered

    if complete:
        status, confidence = COST_COMPLETE, (
            "verified_reference" if not runtime_entered else "mixed")
        estimated: float | None = round(total, 2)
    else:
        status = COST_INCOMPLETE
        confidence = "partial_reference" if machine_total > 0 else "none"
        # Partial money is still reported as partial_cost_inr, but the headline
        # estimate stays None so nothing downstream treats it as the real cost.
        estimated = None
    return {
        "estimated_cost_inr": estimated,
        "partial_cost_inr": round(total, 2) if has_any_money else None,
        "cost_status": status,
        "cost_confidence": confidence,
        "estimated_hours": round(crew_hours, 2),
        "hours_provenance": plan["provenance"],
        "cost_method": spec.cost_method,
        "line_items": line_items,
        "missing_inputs": missing,
        "declared_required_inputs": declared_required,
        "equipment_plan": {k.upper(): float(v)
                           for k, v in (equipment_hours or {}).items()},
        "formula": "estimated_response_cost = reference_machine_cost + "
                   "runtime_vehicle_cost + runtime_labour_cost + "
                   "runtime_material_cost + other_cost",
    }


def cost_for_allocation(estimate: dict, fallback_ceiling: float) -> float:
    """The number the knapsack actually spends.

    An unknown cost cannot be 0 (that would let it win every budget contest) and
    it cannot be infinity (that would silently drop it forever). We charge the
    partial known cost plus a conservative reserve up to ``fallback_ceiling``,
    and the ticket is reported as FEASIBLE_BUT_COST_INCOMPLETE so a human sees
    that the number is a reserve, not a price.
    """
    if estimate.get("estimated_cost_inr") is not None:
        return float(estimate["estimated_cost_inr"])
    partial = estimate.get("partial_cost_inr") or 0.0
    return float(max(partial, fallback_ceiling))

