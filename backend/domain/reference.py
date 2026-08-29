"""
Kopargaon civic reference data, loaded from the ``kopargaon_*.json`` datasets.

Design rule taken straight from those datasets: a tender or BOQ proves that a
resource *type* or role is used, never how many are available today. So this
module exposes verified facts (SLA targets, statutory RTS day limits, accepted
L1 hourly machine rates, department/role matrices, escalation ladder) and it
exposes the *gaps* just as explicitly. Anything not in the datasets is either an
operator input or a labelled policy value -- it is never fabricated here.

Loaded once and cached; call ``get_reference()``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from config import settings
except ImportError:  # pragma: no cover - direct execution / package import
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from config import settings


DATASET_FILES = {
    "sla": "kopargaon_civic_service_sla_escalation_matrix_v1.json",
    "workforce": "kopargaon_department_workforce_skill_matrix_v1.json",
    "cost": "kopargaon_water_waste_operational_rules_cost_matrix_v1.json",
    "capability": "kopargaon_civic_resource_capability_evidence_v1.json",
    "contacts": "kopargaon_civic_contacts_and_escalation_v1.json",
    # v2 supersedes v1 (STP record updated to the latest MPCB public record).
    "projects": "kopargaon_municipal_projects_management_pipeline_v2.json",
}

# Legacy category slugs the existing React form posts. Mapped to canonical
# incident types so the frontend never has to change. Values marked
# ``unsourced_local_extension`` have no response target in any dataset.
LEGACY_CATEGORY_MAP = {
    "pothole": "road_damage",
    "waterlogging": "flood_road_blockage",
    "sanitation": "drain_blockage",
    "water_quality": "water_quality_alert",
    "garbage": "missed_waste_collection",
    "streetlight": "street_light_fault",
    "infrastructure": "general_infrastructure",
    "other": "unclassified",
    "drainage": "drain_blockage",
    "water_leak": "water_leakage",
}

# Categories the UI can raise that the Kopargaon SLA matrix does not cover.
# They get a department (best available evidence) but NO response target, and
# they are flagged so the API can say "target not defined for this category"
# instead of quietly inventing 24 hours.
LOCAL_EXTENSION_CATEGORIES = {
    "street_light_fault": "CIVIL_PUBLIC_WORKS",
    "general_infrastructure": "CIVIL_PUBLIC_WORKS",
    "unclassified": None,
}

# SLA dataset writes departments as free text; the workforce dataset owns the
# canonical ids. Exact name matches are resolved automatically, these are the
# two that differ.
DEPARTMENT_TEXT_OVERRIDES = {
    "External emergency handoff": None,
    "Fire / emergency": "FIRE_RESPONSE",
    "Civil / Public Works + Disaster Response": "CIVIL_PUBLIC_WORKS",
}


@dataclass(frozen=True)
class IncidentSpec:
    """Everything the engine needs to know about one incident category."""

    incident_type: str
    department_id: str | None = None
    department_label: str | None = None
    # None means "no municipal response target is defined for this category".
    response_target_minutes: float | None = None
    target_provenance: str = "unsourced_local_extension"
    priority_floor: str | None = None
    is_statutory_rts: bool = False
    related_rts_service_id: str | None = None
    related_rts_days: int | None = None
    default_action: str | None = None
    external_handoff: tuple[str, ...] = ()
    sensitive_sites: tuple[str, ...] = ()
    required_roles: tuple[str, ...] = ()
    optional_roles: tuple[str, ...] = ()
    candidate_equipment: tuple[str, ...] = ()
    cost_method: str | None = None
    required_cost_inputs: tuple[str, ...] = ()
    priority_boost_conditions: tuple[str, ...] = ()
    gis_checks: tuple[str, ...] = ()
    note: str | None = None

    @property
    def has_response_target(self) -> bool:
        return self.response_target_minutes is not None


def _minutes(target: dict | None) -> float | None:
    """Normalise a ``response_target`` block to minutes. The dataset mixes
    minutes and hours; merging them silently would be a real bug."""
    if not target or target.get("value") is None:
        return None
    value = float(target["value"])
    unit = str(target.get("unit", "minutes")).lower()
    if unit.startswith("hour"):
        return value * 60.0
    if unit.startswith("day"):
        return value * 1440.0
    if unit.startswith("sec"):
        return value / 60.0
    return value


def _tuple(value: Any) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


class ReferenceData:
    """Parsed view over the six Kopargaon datasets."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.raw: dict[str, dict] = {}
        self.missing_files: list[str] = []
        for key, filename in DATASET_FILES.items():
            path = directory / filename
            if not path.is_file():
                self.missing_files.append(filename)
                self.raw[key] = {}
                continue
            self.raw[key] = json.loads(path.read_text(encoding="utf-8"))

        self.departments: dict[str, dict] = {}
        self.incidents: dict[str, IncidentSpec] = {}
        self.rts_services: dict[str, dict] = {}
        self.equipment_rates: dict[str, dict] = {}
        self.escalation_levels: list[dict] = []
        self.contacts: dict[str, dict] = {}
        self.routing_rules: dict[str, dict] = {}
        self._build()

    # -- build ------------------------------------------------------------
    def _build(self) -> None:
        self._build_departments()
        self._build_rts()
        self._build_rates()
        self._build_escalation()
        self._build_incidents()

    def _build_departments(self) -> None:
        for dept in self.raw["workforce"].get("departments", []):
            self.departments[dept["department_id"]] = {
                "department_id": dept["department_id"],
                "name": dept.get("name"),
                "capabilities": _tuple(dept.get("capabilities")),
                "roles": _tuple(dept.get("roles")),
                "evidence": dept.get("evidence"),
            }
        self._dept_by_name = {
            (d.get("name") or "").strip(): did
            for did, d in self.departments.items()
        }

    def _resolve_department(self, text: str | None) -> str | None:
        if not text:
            return None
        if text in DEPARTMENT_TEXT_OVERRIDES:
            return DEPARTMENT_TEXT_OVERRIDES[text]
        if text in self.departments:
            return text
        return self._dept_by_name.get(text.strip())

    def _build_rts(self) -> None:
        for svc in self.raw["sla"].get("official_rts_services", []):
            self.rts_services[svc["service_id"]] = svc

    def _build_rates(self) -> None:
        rates = (self.raw["cost"]
                 .get("waste_and_drain_operations", {})
                 .get("drain_desilting_reference_rates", {}))
        for item in rates.get("unit_rates", []):
            self.equipment_rates[item["resource_code"]] = {
                "resource_code": item["resource_code"],
                "display_name": item.get("display_name"),
                "unit": item.get("unit"),
                "rate_inr": item.get("reference_rate_inr"),
                "rate_source": item.get("rate_source"),
                "confidence": item.get("confidence"),
                "tender_id": rates.get("tender_id"),
            }

    def _build_escalation(self) -> None:
        engine = self.raw["sla"].get("escalation_engine", {})
        self.escalation_levels = list(engine.get("operational_escalation", []))
        self.rts_appeal_logic = engine.get("rts_appeal_logic", {})
        for contact in self.raw["contacts"].get("contacts", []):
            self.contacts[contact["contact_id"]] = contact
        for rule in self.raw["contacts"].get("routing_rules", []):
            self.routing_rules[rule["incident_type"]] = rule

    def _build_incidents(self) -> None:
        # 1. operational categories from the SLA matrix (the sourced targets)
        specs: dict[str, dict] = {}
        for row in self.raw["sla"].get("operational_incident_categories", []):
            itype = row["incident_type"]
            specs[itype] = {
                "incident_type": itype,
                "department_label": row.get("department_or_handoff"),
                "department_id": self._resolve_department(
                    row.get("department_or_handoff")),
                "response_target_minutes": _minutes(row.get("response_target")),
                "target_provenance": (
                    "kopargaon_sla_matrix_v1:"
                    f"{row.get('target_status', 'defined')}"),
                "priority_floor": row.get("priority_floor"),
                "is_statutory_rts": bool(row.get("is_statutory_rts")),
                "related_rts_service_id": row.get("official_related_service"),
                "related_rts_days": row.get("official_related_rts_days"),
                "default_action": row.get("default_action"),
                "sensitive_sites": _tuple(row.get("sensitive_sites")),
                "note": row.get("note"),
            }

        # 2. roles + equipment from the workforce compatibility matrix
        for row in self.raw["workforce"].get("incident_compatibility_matrix", []):
            itype = row["incident_type"]
            spec = specs.setdefault(itype, {"incident_type": itype})
            spec.setdefault("department_id", row.get("department_id"))
            spec["department_id"] = spec.get("department_id") or row.get(
                "department_id")
            spec["required_roles"] = _tuple(row.get("required_roles"))
            spec["optional_roles"] = _tuple(row.get("optional_roles"))
            spec["candidate_equipment"] = _tuple(row.get("optional_equipment"))
            spec["external_handoff"] = _tuple(row.get("external_handoff"))
            if row.get("notes"):
                spec.setdefault("note", row["notes"])

        # 3. cost method, GIS checks and priority boosts from the water/waste
        #    operational rules
        cost = self.raw["cost"]
        rule_sets = (
            cost.get("water_operations", {}).get("incident_rules", []),
            cost.get("waste_and_drain_operations", {}).get("incident_rules", []),
        )
        for rules in rule_sets:
            for row in rules:
                itype = row["incident_type"]
                spec = specs.setdefault(itype, {"incident_type": itype})
                spec["department_id"] = spec.get("department_id") or row.get(
                    "department")
                spec["cost_method"] = row.get("cost_method")
                spec["required_cost_inputs"] = _tuple(
                    row.get("required_cost_inputs"))
                spec["priority_boost_conditions"] = _tuple(
                    row.get("priority_boost_conditions"))
                spec["gis_checks"] = _tuple(row.get("gis_checks"))
                if row.get("candidate_equipment"):
                    spec["candidate_equipment"] = _tuple(
                        row["candidate_equipment"])
                if row.get("sensitive_sites"):
                    spec["sensitive_sites"] = _tuple(row["sensitive_sites"])
                # A HIGH floor declared in the cost rules must not be lost.
                if row.get("priority_floor") and not spec.get("priority_floor"):
                    spec["priority_floor"] = row["priority_floor"]
                if not spec.get("required_roles"):
                    spec["required_roles"] = _tuple(
                        row.get("minimum_capabilities"))
                if row.get("note"):
                    spec.setdefault("note", row["note"])

        # 4. UI categories with no dataset coverage -- department only, no target
        for itype, dept in LOCAL_EXTENSION_CATEGORIES.items():
            spec = specs.setdefault(itype, {"incident_type": itype})
            spec.setdefault("department_id", dept)
            spec.setdefault("target_provenance", "unsourced_local_extension")

        for itype, spec in specs.items():
            spec.pop("incident_type", None)
            self.incidents[itype] = IncidentSpec(incident_type=itype, **spec)

    # -- lookups ----------------------------------------------------------
    def canonical_category(self, category: str | None) -> str:
        """Accept either a canonical incident_type or a legacy UI slug."""
        if not category:
            return "unclassified"
        key = str(category).strip().lower().replace("-", "_").replace(" ", "_")
        if key in self.incidents:
            return key
        return LEGACY_CATEGORY_MAP.get(key, key)

    def incident(self, category: str | None) -> IncidentSpec:
        key = self.canonical_category(category)
        return self.incidents.get(key) or IncidentSpec(incident_type=key)

    def rts_service(self, service_id: str | None) -> dict | None:
        return self.rts_services.get(service_id) if service_id else None

    def equipment_rate(self, resource_code: str) -> float | None:
        """Verified accepted-L1 hourly rate, or None. Callers must treat None as
        COST_INCOMPLETE and never as zero."""
        entry = self.equipment_rates.get(str(resource_code).upper())
        return None if entry is None else entry.get("rate_inr")

    def routing_for(self, incident_type: str) -> dict | None:
        rule = self.routing_rules.get(incident_type)
        if not rule:
            return None
        out = dict(rule)
        out["primary"] = self.contacts.get(rule.get("primary_contact_id"))
        out["fallback"] = self.contacts.get(rule.get("fallback_contact_id"))
        return out

    def escalation_for(self, level: int) -> dict | None:
        for row in self.escalation_levels:
            if int(row.get("level", -1)) == int(level):
                return row
        return None

    # -- SLA status -------------------------------------------------------
    def operational_sla_status(self, elapsed_minutes: float | None,
                              target_minutes: float | None) -> str:
        """ON_TRACK / AT_RISK / OVERDUE exactly as sla_status_logic defines it.
        TARGET_UNDEFINED is returned rather than guessing when no target exists.
        """
        if target_minutes is None or elapsed_minutes is None:
            return "TARGET_UNDEFINED"
        if target_minutes <= 0:
            # 0-minute targets are immediate external handoffs (108/112).
            return "IMMEDIATE_HANDOFF"
        ratio = elapsed_minutes / target_minutes
        if ratio >= 1.0:
            return "OVERDUE"
        if ratio >= 0.5:
            return "AT_RISK"
        return "ON_TRACK"

    def rts_status(self, elapsed_days: float | None,
                   limit_days: int | None) -> str:
        if limit_days is None or elapsed_days is None:
            return "NOT_A_NOTIFIED_SERVICE"
        return ("RTS_LIMIT_REACHED" if elapsed_days >= limit_days
                else "WITHIN_RTS_TIME")

    # -- constants surfaced to the API ------------------------------------
    @property
    def notification_events(self) -> list[str]:
        return list(self.raw["sla"].get("notification_events", []))

    @property
    def budget_outcomes(self) -> list[str]:
        return list(self.raw["cost"].get("cost_engine", {})
                    .get("budget_outcomes", []))

    @property
    def cost_rules(self) -> list[str]:
        return list(self.raw["cost"].get("cost_engine", {}).get("rules", []))

    @property
    def sensitive_site_types(self) -> list[str]:
        seen: list[str] = []
        for spec in self.incidents.values():
            for site in spec.sensitive_sites:
                if site not in seen:
                    seen.append(site)
        return seen or ["hospital", "school", "market", "dense_population_zone"]

    @property
    def waste_baseline(self) -> dict:
        return dict(self.raw["cost"].get("waste_and_drain_operations", {})
                    .get("solid_waste_baseline", {}))

    @property
    def runtime_resource_types(self) -> list[dict]:
        return list(self.raw["capability"]
                    .get("recommended_runtime_resources", []))

    @property
    def project_pipeline(self) -> list[dict]:
        return list(self.raw["projects"].get("records", []))

    def public_contacts(self) -> list[dict]:
        """Official public helpline / office channels only. The source dataset
        already excludes personal officer mobile numbers, and nothing here adds
        any."""
        return [dict(c) for c in self.contacts.values()]

    # -- honest accounting of what is missing ------------------------------
    def data_gaps(self) -> dict:
        """What the platform does NOT know, and how it behaves anyway.

        Surfaced at ``GET /api/reference/gaps``. Every gap names the fallback so
        a reviewer can check that an unknown never silently becomes a zero.
        """
        no_target = sorted(k for k, v in self.incidents.items()
                           if not v.has_response_target)
        no_roles = sorted(k for k, v in self.incidents.items()
                          if not v.required_roles)
        return {
            "missing_dataset_files": list(self.missing_files),
            "verified": {
                "operational_response_targets": sum(
                    1 for v in self.incidents.values() if v.has_response_target),
                "statutory_rts_services": len(self.rts_services),
                "equipment_hourly_rates": len(self.equipment_rates),
                "departments": len(self.departments),
                "escalation_levels": len(self.escalation_levels),
            },
            "gaps": [
                {
                    "field": "ward_master_list",
                    "status": "absent_from_all_datasets",
                    "fallback": "operator-entered wards; population and "
                                "equity_index stay NULL with "
                                "data_confidence='unverified'",
                },
                {
                    "field": "ward_population_and_equity_index",
                    "status": "absent_from_all_datasets",
                    "fallback": "C3 Socio-Spatial Equity contributes as a wide "
                                "low-confidence fuzzy interval and the response "
                                "flags equity as unverified",
                },
                {
                    "field": "live_resource_quantities",
                    "status": "absent_by_design (tenders prove capability, not "
                              "availability)",
                    "fallback": "daily_capacity is operator-entered and stamped "
                                "with verified_by/verified_at",
                },
                {
                    "field": "water_and_waste_unit_rates",
                    "status": "no_verified_unit_rate_in_public_records",
                    "fallback": "cost stays NULL with COST_INCOMPLETE; only the "
                                "8 accepted-L1 machine rates are auto-costed",
                },
                {
                    "field": "ahp_pairwise_weights",
                    "status": "no_numeric_weights_in_any_dataset",
                    "fallback": "weights come from an operator pairwise matrix "
                                "that must pass CR < "
                                f"{settings.AHP_CR_THRESHOLD}; until then the "
                                "default weights are labelled unvalidated",
                },
                {
                    "field": "phash_threshold_and_geo_radius",
                    "status": "policy_value_not_a_civic_fact",
                    "fallback": "configurable; current values reported by "
                                "GET /api/reference/config",
                },
                {
                    "field": "marathi_message_templates",
                    "status": "absent (only English citizen texts exist)",
                    "fallback": "citizen_message_mr stays NULL until a reviewed "
                                "translation is supplied",
                },
                {
                    "field": "historical_complaint_resolution_dataset",
                    "status": "absent",
                    "fallback": "SHAP surrogate is fitted on the current scored "
                                "cohort only, and exact TOPSIS attribution is "
                                "used as the primary explanation",
                },
            ],
            "categories_without_response_target": no_target,
            "categories_without_role_matrix": no_roles,
        }
    # -- serialisation for the API ----------------------------------------
    def incident_catalogue(self) -> list[dict]:
        out = []
        for itype in sorted(self.incidents):
            spec = self.incidents[itype]
            out.append({
                "incident_type": spec.incident_type,
                "department_id": spec.department_id,
                "department_name": (self.departments.get(spec.department_id, {})
                                    .get("name") if spec.department_id else None),
                "response_target_minutes": spec.response_target_minutes,
                "target_provenance": spec.target_provenance,
                "priority_floor": spec.priority_floor,
                "is_statutory_rts": spec.is_statutory_rts,
                "related_rts_service_id": spec.related_rts_service_id,
                "related_rts_days": spec.related_rts_days,
                "required_roles": list(spec.required_roles),
                "optional_roles": list(spec.optional_roles),
                "candidate_equipment": list(spec.candidate_equipment),
                "sensitive_sites": list(spec.sensitive_sites),
                "cost_method": spec.cost_method,
                "required_cost_inputs": list(spec.required_cost_inputs),
                "priority_boost_conditions": list(spec.priority_boost_conditions),
                "external_handoff": list(spec.external_handoff),
                "default_action": spec.default_action,
                "note": spec.note,
            })
        return out

    def legacy_category_map(self) -> dict:
        return dict(LEGACY_CATEGORY_MAP)


@lru_cache(maxsize=1)
def get_reference() -> ReferenceData:
    """Process-wide cached reference data."""
    return ReferenceData(Path(settings.REFERENCE_DIR))


def reload_reference() -> ReferenceData:
    get_reference.cache_clear()
    return get_reference()


if __name__ == "__main__":  # pragma: no cover
    ref = get_reference()
    print(f"missing files      : {ref.missing_files or 'none'}")
    print(f"incident categories: {len(ref.incidents)}")
    print(f"rts services       : {len(ref.rts_services)}")
    print(f"equipment rates    : {len(ref.equipment_rates)}")
    print(f"departments        : {len(ref.departments)}")
    for name in ("pothole", "water_quality", "garbage", "streetlight"):
        spec = ref.incident(name)
        print(f"  {name:>14} -> {spec.incident_type:<28} "
              f"target={spec.response_target_minutes} "
              f"dept={spec.department_id} floor={spec.priority_floor}")

