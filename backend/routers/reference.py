"""Reference vocabulary: the values the UI must not invent for itself.

Three of the four things here exist because a dropdown that disagrees with the
engine is a silent bug. The category list, the criteria names and the SLA status
strings are all decided in `domain/`, from the council's own datasets; if a page
hardcodes `["pothole", "garbage", "streetlight"]` it will happily submit a
category the engine has never heard of, and the ticket will score as
`unclassified` without anyone noticing. So the vocabulary is served, not shipped.

The fourth, `/gaps`, is the opposite: it exists to be *displayed*. It is the list
of things this platform does not know -- unverified unit rates, wards with no
population, an unreviewed Marathi translation -- each paired with the fallback it
takes instead. A reviewer should be able to read it and confirm that no unknown
was quietly rounded to zero.

Everything here is a read, and everything is derived from files on disk plus
`settings`, so there is no database dependency and nothing to audit.
`domain/reference.py` caches its parse process-wide; `/reload` clears that cache
for the case where a dataset file is corrected while the server is up.
"""
from __future__ import annotations

import os
import sys

from fastapi import APIRouter, Query

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from domain import criteria as crit  # noqa: E402
from domain.reference import get_reference, reload_reference  # noqa: E402

router = APIRouter(prefix="/api/reference", tags=["reference"])

# The four operational SLA verdicts and the two statutory ones, with the words to
# print. Kept here rather than in the UI so "AT_RISK" never becomes "At risk?" on
# one page and "Warning" on another -- and so the two clocks stay distinguishable.
OPERATIONAL_SLA_STATUSES = [
    {"code": "ON_TRACK", "label_en": "On track",
     "meaning": "less than half the municipal response target has elapsed"},
    {"code": "AT_RISK", "label_en": "At risk",
     "meaning": "half or more of the response target has elapsed"},
    {"code": "OVERDUE", "label_en": "Overdue",
     "meaning": "the response target has passed"},
    {"code": "IMMEDIATE_HANDOFF", "label_en": "Immediate handoff",
     "meaning": "a zero-minute target: this is handed to 108/112, not queued"},
    {"code": "TARGET_UNDEFINED", "label_en": "No target defined",
     "meaning": "the council publishes no response target for this category, so "
                "no operational verdict is claimed"},
]

RTS_STATUSES = [
    {"code": "WITHIN_RTS_TIME", "label_en": "Within statutory limit",
     "meaning": "the Right to Service day limit has not been reached"},
    {"code": "RTS_LIMIT_REACHED", "label_en": "Statutory limit reached",
     "meaning": "the notified service limit has been reached or passed"},
    {"code": "NOT_A_NOTIFIED_SERVICE", "label_en": "Not a notified service",
     "meaning": "no RTS service maps to this category, so no statutory clock runs"},
]

COST_STATUSES = [
    {"code": "COST_COMPLETE", "label_en": "Costed",
     "meaning": "every required cost input is present, so this ticket can "
                "compete for budget"},
    {"code": "COST_INCOMPLETE", "label_en": "Not costed",
     "meaning": "at least one required input is missing; the cost stays NULL and "
                "the ticket is ranked but cannot be allocated budget"},
]

CRITERIA_LABELS = {
    "C1_infra": ("Infrastructural criticality",
                 "how central the asset is to the network, anchored on the "
                 "council's own published response target for the category"),
    "C2_safety": ("Public safety and health",
                  "the danger the fault poses to people, including sensitive "
                  "sites nearby and the health pathway the category opens"),
    "C3_equity": ("Equity of service",
                  "whether this ward has been under-served, which is why an "
                  "unentered population figure must stay unentered"),
    "C4_cost": ("Cost to resolve",
                "the only cost criterion: lower is better, so it is minimised "
                "while the other three are maximised"),
}


@router.get("/config")
def config():
    """Policy values the UI may display, plus which of them are policy not fact.

    `domain/reference.py` points here for the dedup thresholds specifically
    because they are the one pair of numbers in the system that is *not* a civic
    fact -- nobody published them, we chose them -- and `dedupe.provenance` says
    so in the payload rather than in a comment nobody reads.
    """
    ref = get_reference()
    return {
        **settings.as_public_dict(),
        "reference_dir": str(settings.REFERENCE_DIR),
        "datasets_loaded": len(ref.raw) - len(ref.missing_files),
        "datasets_missing": list(ref.missing_files),
        "incident_categories": len(ref.incidents),
        "criteria": crit.CRITERIA,
    }


@router.get("/gaps")
def gaps():
    """What the platform does not know, and the fallback it takes instead.

    This is the compliance page's honesty panel. Each gap names a `status` and a
    `fallback`; a reviewer reading the list should be able to confirm that no
    unknown was quietly turned into a zero.
    """
    return get_reference().data_gaps()


@router.get("/criteria")
def criteria():
    """The four ranking criteria: names, direction, and what each one means.

    `type` is load-bearest: three criteria are `benefit` (higher is better) and
    `C4_cost` is `cost` (lower is better). A UI that renders all four as
    "higher is better" bars tells the opposite of the truth about cost.
    """
    ref = get_reference()
    return {
        "criteria": [
            {
                "code": code,
                "type": crit.CRITERIA_TYPES[code],
                "direction": ("higher is better"
                              if crit.CRITERIA_TYPES[code] == "benefit"
                              else "lower is better"),
                "label_en": CRITERIA_LABELS[code][0],
                "meaning": CRITERIA_LABELS[code][1],
            }
            for code in crit.CRITERIA
        ],
        "aggregation": "fuzzy AHP weights (Buckley geometric mean) -> fuzzy "
                       "TOPSIS closeness coefficient CCi in [0, 1]",
        "cr_threshold": settings.AHP_CR_THRESHOLD,
        "cr_gate": (f"weights derived from pairwise judgements with a consistency "
                    f"ratio of {settings.AHP_CR_THRESHOLD} or above are stored "
                    f"but refused for activation: contradictory judgements must "
                    f"not rank citizens' work"),
        "max_tfn_spread": crit.MAX_TFN_SPREAD,
        "population_saturation": crit.POPULATION_SATURATION,
        "sensitive_site_weights": dict(crit.SENSITIVE_SITE_WEIGHT),
        "sensitive_site_types": ref.sensitive_site_types,
    }


@router.get("/sla")
def sla():
    """Two independent clocks, and the vocabulary of each.

    The operational response target is in minutes and is the council's own
    service promise. The statutory Right to Service limit is in days and is law.
    They are never merged: a category can be overdue operationally while still
    inside its RTS limit, and the reverse, and both facts matter to a different
    audience.
    """
    ref = get_reference()
    return {
        "operational": {
            "unit": "minutes",
            "source": "council operational response targets, per category",
            "statuses": OPERATIONAL_SLA_STATUSES,
            "at_risk_fraction": 0.5,
            "categories_with_target": sum(
                1 for s in ref.incidents.values() if s.has_response_target),
            "categories_without_target": sorted(
                k for k, v in ref.incidents.items() if not v.has_response_target),
        },
        "statutory_rts": {
            "unit": "days",
            "source": "Maharashtra Right to Service notified services",
            "statuses": RTS_STATUSES,
            "services": [
                {"service_id": sid, **{k: v for k, v in row.items()
                                       if k != "service_id"}}
                for sid, row in sorted(ref.rts_services.items())
            ],
        },
        "cost_statuses": COST_STATUSES,
        "escalation_levels": ref.escalation_levels,
        "notification_events": ref.notification_events,
        "budget_outcomes": ref.budget_outcomes,
        "cost_rules": ref.cost_rules,
        "note": ("is_statutory_rts and rts_deadline_at are independent: a "
                 "category can be a notified service while a particular ticket "
                 "has no computed deadline. Key any deadline display off "
                 "rts_deadline_at != null."),
    }


@router.get("/categories")
def categories(include_legacy: bool = Query(True, description="also return the "
                                                             "legacy UI slug map")):
    """Every incident category the engine recognises, with what it implies.

    This is what a submit form's dropdown should be built from. Each row carries
    the owning department, the response target (`null` when none is published),
    the priority floor, the RTS link, the roles and equipment a crew would need,
    and the cost inputs required before the ticket can be costed at all.
    """
    ref = get_reference()
    catalogue = ref.incident_catalogue()
    body = {
        "count": len(catalogue),
        "categories": catalogue,
        "departments": [
            {"department_id": did, **{k: v for k, v in row.items()
                                     if k != "department_id"}}
            for did, row in sorted(ref.departments.items())
        ],
    }
    if include_legacy:
        body["legacy_category_map"] = ref.legacy_category_map()
        body["legacy_note"] = ("keys are older UI slugs; submit the canonical "
                               "incident_type where possible -- an unrecognised "
                               "category is accepted but scores as unclassified")
    return body


@router.get("/channels")
def channels():
    """The six escalation channels and the public contact behind each.

    Worth being precise about, because the obvious reading is wrong: these are
    keyed by *channel* (`medical_emergency`, `police_fire_immediate_threat`,
    `municipal_civic_service`, ...), not by incident category. There is no
    per-category routing table in the datasets, so a caller wanting "where does a
    pothole go" should read `department_id` from `/categories` and treat these
    channels as the escalation and external-handoff paths that sit beside it.
    """
    ref = get_reference()
    rows = []
    for name in sorted(ref.routing_rules):
        rule = ref.routing_for(name) or {}
        rows.append({"channel": name, **rule})
    return {"count": len(rows), "channels": rows,
            "keyed_by": "escalation_channel",
            "note": ("not keyed by incident category -- use department_id from "
                     "GET /api/reference/categories for departmental ownership")}


@router.get("/contacts")
def contacts():
    """Official public helplines and office channels only.

    The source dataset contains no personal officer mobile numbers and nothing
    here adds any -- this endpoint is safe to render on a citizen-facing page.
    """
    rows = get_reference().public_contacts()
    return {"count": len(rows), "contacts": rows}


@router.post("/reload")
def reload_datasets():
    """Re-read the dataset files from disk, for when one is corrected in place.

    A POST because it mutates process state. Reports what is still missing after
    the reload rather than claiming success unconditionally.
    """
    ref = reload_reference()
    return {"reloaded": True,
            "reference_dir": str(settings.REFERENCE_DIR),
            "incident_categories": len(ref.incidents),
            "rts_services": len(ref.rts_services),
            "equipment_rates": len(ref.equipment_rates),
            "departments": len(ref.departments),
            "datasets_missing": list(ref.missing_files)}
