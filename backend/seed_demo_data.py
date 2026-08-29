"""Fill the real database with a demo pool that exercises every decision path.

Run it from the ``backend`` directory:

    python seed_demo_data.py --reset

The point of this script is not "some rows exist". It is that after it runs, a
judge clicking through the UI meets, without anyone staging it:

* a ticket the allocator **committed before optimising** because the floor is
  critical (a road blockage with people isolated),
* tickets **deferred because nobody costed them** -- reason code
  ``deferred_cost_not_estimated``, cost left NULL and never zero,
* tickets **deferred because a better-value combination took the money** --
  ``deferred_capacity_used_by_higher_value_set``,
* at least one ticket **scheduled ahead of a better-ranked one**, which is the
  knapsack doing real work and the hardest thing to explain honestly,
* a **duplicate cluster** merged by perceptual hash, and a second merged on text
  plus proximity, both raising the parent's community multiplier,
* a near-miss that was **refused** a merge and says why.

The capacity figure is not hard-coded to a lucky number: ``--auto-capacity``
dry-runs several budgets and picks the first that produces both deferral reasons
*and* a rank inversion, so the demo stays interesting even after the case list is
edited. Dry runs write nothing.

Nothing here fabricates data the council does not have. Ward population and
equity index stay NULL unless ``--ward-estimates`` is passed, and even then they
are written as ``operator_entered``, never ``verified`` -- which is exactly how
the equity criterion reports itself downstream.

Phone numbers are ``90000000xx``, deliberately outside any real range.
"""
from __future__ import annotations

import argparse
import io
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (str(HERE), str(HERE.parent)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Kopargaon town centre. Offsets below are metres-scale, so the dedup radius
# (default 60 m) and the text radius behave the way they would in the field.
KOP_LAT, KOP_LON = 19.8872, 74.4772

# Tables this script owns. Ordered child-before-parent so plain DELETEs work
# whether or not foreign keys are enforced on the connection.
DEMO_TABLES = [
    "ticket_explanations", "dispatch_manifest_items", "dispatch_manifests",
    "ticket_scores", "ticket_criteria_scores", "ticket_media", "ticket_events",
    "notifications", "tickets", "capacity_resources", "daily_capacity",
    "citizens", "wards",
]

WARD_LABELS = ["Ward-1", "Ward-2", "Ward-3", "Ward-4", "Ward-5",
               "Ward-6", "Ward-7", "Ward-8", "Ward-9"]

# Operator-entered estimates, used only with --ward-estimates. These are
# plausible for a town of Kopargaon's size and are NOT published figures; the
# loader stamps them operator_entered so every equity interval stays wide.
WARD_ESTIMATES = {
    "Ward-1": (7400, 0.71, 0.38), "Ward-2": (5900, 0.64, 0.52),
    "Ward-3": (6300, 0.88, 0.47), "Ward-4": (8100, 0.79, 0.66),
    "Ward-5": (4800, 1.02, 0.44), "Ward-6": (5200, 0.94, 0.58),
    "Ward-7": (3900, 1.41, 0.35), "Ward-8": (6600, 0.83, 0.61),
    "Ward-9": (4400, 1.28, 0.72),
}

# One row per complaint as it would arrive. ``cost`` is (rupees, crew-hours) when
# a ward officer has measured it and None when nobody has -- the second case is
# not an oversight in the fixture, it is a state the allocator must handle.
# ``photo`` seeds a deterministic synthetic image so perceptual hashes reproduce.
CASES: list[dict] = [
    {"key": "hospital_drain", "cat": "drain_blockage", "ward": "Ward-4",
     "lat": 19.88110, "lon": 74.47850, "photo": 11, "cost": (11800, 6.0),
     "desc": "Drain choked outside the Civil Hospital gate, sewage standing on "
             "the footpath where patients walk in",
     "extra": {"sensitive_site": "hospital", "affected_population": 2400,
               "duration_hours": 30}},
    {"key": "approach_road_flood", "cat": "flood_road_blockage", "ward": "Ward-9",
     "lat": 19.86020, "lon": 74.47010, "cost": (8900, 5.0),
     "desc": "Water logged right across the Kopargaon-Yeola approach road, "
             "two-wheelers and autos cannot get through",
     "extra": {"affected_population": 3000, "blocks_major_road": True,
               "duration_hours": 14}},
    {"key": "nagar_road_pothole", "cat": "road_damage", "ward": "Ward-3",
     "lat": 19.89010, "lon": 74.47520, "photo": 21, "cost": (7300, 4.0),
     "desc": "Deep pothole at the Nagar Road turning, bikes are skidding in it "
             "every evening",
     "extra": {"affected_population": 800, "blocks_major_road": True}},
    {"key": "sai_nagar_water", "cat": "water_distribution_failure",
     "ward": "Ward-5", "lat": 19.88500, "lon": 74.48210, "cost": (5600, 3.0),
     "desc": "No water supply in Sai Nagar for two days, tankers not coming "
             "either",
     "extra": {"affected_population": 1500, "duration_hours": 48}},
    {"key": "school_light", "cat": "street_light_fault", "ward": "Ward-2",
     "lat": 19.89250, "lon": 74.47000, "cost": (2200, 1.5),
     "desc": "Street light out at the girls' school gate, children leaving "
             "coaching at night in the dark",
     "extra": {"sensitive_site": "school", "affected_population": 400}},
    {"key": "phc_garbage", "cat": "waste_overflow_near_sensitive_site",
     "ward": "Ward-4", "lat": 19.88320, "lon": 74.48050, "cost": (4300, 2.5),
     "desc": "Garbage heap overflowing beside the primary health centre wall, "
             "dogs spreading it on the road",
     "extra": {"sensitive_site": "primary_health_centre",
               "affected_population": 1200, "duration_hours": 72}},
    {"key": "shivaji_nagar_waste", "cat": "missed_waste_collection",
     "ward": "Ward-6", "lat": 19.87900, "lon": 74.46800, "cost": (3100, 2.0),
     "desc": "Ghanta gaadi has not come to Shivaji Nagar for four days, waste "
             "piling at the lane corner",
     "extra": {"affected_population": 900, "duration_hours": 96}},
    {"key": "market_leak", "cat": "water_leakage", "ward": "Ward-1",
     "lat": 19.88800, "lon": 74.47600, "photo": 31, "cost": (6900, 4.0),
     "desc": "Main pipeline leaking at the market chowk, drinking water running "
             "straight into the drain",
     "extra": {"affected_population": 2000, "duration_hours": 20}},
    {"key": "bus_stand_mosquito", "cat": "mosquito_or_vector_control",
     "ward": "Ward-1", "lat": 19.88690, "lon": 74.47410, "cost": None,
     "desc": "Mosquito breeding in the stagnant water behind the bus stand, "
             "whole lane getting bitten",
     "extra": {"affected_population": 1800, "duration_hours": 240}},
    {"key": "stp_inlet", "cat": "stp_inlet_blockage", "ward": "Ward-7",
     "lat": 19.87020, "lon": 74.46010, "cost": (15200, 8.0),
     "desc": "STP inlet screen choked, flow backing up towards the pumping "
             "chamber",
     "extra": {"affected_population": 600, "duration_hours": 10}},
    {"key": "wtp_pump", "cat": "pump_or_electrical_failure", "ward": "Ward-7",
     "lat": 19.87180, "lon": 74.46240, "cost": (9400, 5.0),
     "desc": "Pump 2 at the water treatment plant tripped again, supply to two "
             "wards is down to one hour",
     "extra": {"affected_population": 5200, "duration_hours": 8}},
    {"key": "rain_silt", "cat": "heavy_silt_or_flood_debris", "ward": "Ward-9",
     "lat": 19.86400, "lon": 74.47400, "cost": None,
     "desc": "Silt and flood debris left on the road after the rain, nobody has "
             "cleared it",
     "extra": {"affected_population": 700, "duration_hours": 60}},
    {"key": "tehsil_footpath", "cat": "general_infrastructure", "ward": "Ward-1",
     "lat": 19.88960, "lon": 74.47780, "cost": None,
     "desc": "Footpath slab broken outside the tehsil office, elderly people "
             "stepping into the drain",
     "extra": {"affected_population": 1100}},
    {"key": "mandir_drain", "cat": "drain_blockage", "ward": "Ward-8",
     "lat": 19.89400, "lon": 74.48400, "cost": (5100, 3.0),
     "desc": "Open drain blocked in the Ganesh Mandir lane, water entering the "
             "ground floor rooms",
     "extra": {"affected_population": 650, "duration_hours": 26}},
    {"key": "crossing_cavein", "cat": "road_damage", "ward": "Ward-8",
     "lat": 19.89620, "lon": 74.48720, "photo": 41, "cost": (21000, 11.0),
     "desc": "Road has caved in near the railway crossing, a pit has opened in "
             "the middle of the carriageway",
     "extra": {"affected_population": 2600, "blocks_major_road": True,
               "duration_hours": 12}},
    {"key": "gandhi_nagar_fogging", "cat": "mosquito_or_vector_control",
     "ward": "Ward-3", "lat": 19.89240, "lon": 74.47240, "cost": None,
     "desc": "Fogging has not been done in Gandhi Nagar for over a month, "
             "dengue cases in two houses",
     "extra": {"affected_population": 1400, "duration_hours": 720}},
    {"key": "veg_market_waste", "cat": "missed_waste_collection",
     "ward": "Ward-1", "lat": 19.88540, "lon": 74.47320, "cost": (3600, 2.0),
     "desc": "Vegetable market waste not lifted for three days, smell is "
             "unbearable by afternoon",
     "extra": {"affected_population": 2200, "duration_hours": 70}},
    {"key": "riverside_lights", "cat": "street_light_fault", "ward": "Ward-6",
     "lat": 19.87640, "lon": 74.46420, "cost": (2900, 2.0),
     "desc": "Four poles dark on the riverside road, women avoid that stretch "
             "after seven",
     "extra": {"affected_population": 950}},
    {"key": "drain_mouth_plastic", "cat": "flood_related_waste_accumulation",
     "ward": "Ward-9", "lat": 19.86720, "lon": 74.47760, "cost": None,
     "desc": "Plastic and waste washed into the drain mouth, next rain will "
             "block it completely",
     "extra": {"affected_population": 800, "duration_hours": 40}},
    {"key": "tail_end_pressure", "cat": "water_distribution_failure",
     "ward": "Ward-6", "lat": 19.87860, "lon": 74.46140, "cost": (4800, 3.0),
     "desc": "Tail-end houses getting no pressure at all, only the front lane "
             "gets water",
     "extra": {"affected_population": 1300, "duration_hours": 120}},
    {"key": "sbi_lane_drain", "cat": "drain_blockage", "ward": "Ward-2",
     "lat": 19.89080, "lon": 74.46860, "cost": None,
     "desc": "Drain overflowing at the SBI lane corner every time the pump "
             "upstream runs",
     "extra": {"affected_population": 500, "duration_hours": 18}},
    {"key": "speed_breaker", "cat": "road_damage", "ward": "Ward-2",
     "lat": 19.89320, "lon": 74.46620, "cost": (1900, 1.5),
     "desc": "Speed breaker broken up, loose pieces of concrete lying on the "
             "road",
     "extra": {"affected_population": 400}},
    {"key": "stp_aerator", "cat": "stp_aeration_failure", "ward": "Ward-7",
     "lat": 19.86880, "lon": 74.46420, "cost": None,
     "desc": "Aerator at the STP making a loud noise and stopping every few "
             "minutes",
     "extra": {"affected_population": 300, "duration_hours": 16}},
    {"key": "trunk_main_burst", "cat": "major_water_distribution_failure",
     "ward": "Ward-5", "lat": 19.88240, "lon": 74.48520, "cost": None,
     "desc": "Trunk main burst near the overhead tank, whole area's supply "
             "stopped",
     "extra": {"affected_population": 4600, "duration_hours": 6}},
    {"key": "kolhe_valve", "cat": "water_leakage", "ward": "Ward-4",
     "lat": 19.88620, "lon": 74.48320, "cost": (3400, 2.0),
     "desc": "Valve chamber leaking at Kolhe Chowk, road staying wet all day",
     "extra": {"affected_population": 1000, "duration_hours": 36}},
    {"key": "ward8_silt", "cat": "heavy_silt_or_flood_debris", "ward": "Ward-8",
     "lat": 19.89840, "lon": 74.48240, "cost": None,
     "desc": "Silt dumped at the lane end after desilting has not been carried "
             "away",
     "extra": {"affected_population": 450, "duration_hours": 90}},
    {"key": "ward7_waste", "cat": "missed_waste_collection", "ward": "Ward-7",
     "lat": 19.87420, "lon": 74.46620, "cost": None,
     "desc": "Collection vehicle skipping the STP colony lane for a week now",
     "extra": {"affected_population": 380, "duration_hours": 168}},
    {"key": "muddy_water", "cat": "water_quality_alert", "ward": "Ward-5",
     "lat": 19.88060, "lon": 74.48740, "cost": (4600, 2.5),
     "desc": "Water coming muddy and smelling from the taps in Indira Nagar "
             "since yesterday",
     "extra": {"affected_population": 1700, "duration_hours": 22}},
    {"key": "stp_sludge", "cat": "stp_sludge_handling_issue", "ward": "Ward-7",
     "lat": 19.86640, "lon": 74.46060, "cost": (12800, 7.0),
     "desc": "Sludge drying beds full, no room left to draw the next batch",
     "extra": {"affected_population": 300, "duration_hours": 50}},
    {"key": "school_wall", "cat": "general_infrastructure", "ward": "Ward-3",
     "lat": 19.89540, "lon": 74.47060, "photo": 51, "cost": (9800, 6.0),
     "desc": "Boundary wall of the municipal school is leaning towards the "
             "playground side",
     "extra": {"sensitive_site": "school", "affected_population": 620}},
]

# Reports that arrive *after* the ones above and are meant to collide with them.
# ``expect`` is what the dedup policy should decide; the run prints actual vs
# expected, so a policy change shows up here instead of silently in the demo.
FOLLOW_UPS: list[dict] = [
    {"key": "hospital_drain_dup1", "of": "hospital_drain",
     "cat": "drain_blockage", "ward": "Ward-4",
     "lat": 19.88118, "lon": 74.47858, "photo": 11, "jitter": 8, "quality": 45,
     "desc": "Same drain near the hospital gate is still overflowing",
     "expect": "duplicate", "why": "same photo re-compressed by WhatsApp, 12 m away"},
    {"key": "hospital_drain_dup2", "of": "hospital_drain",
     "cat": "drain_blockage", "ward": "Ward-4",
     "lat": 19.88103, "lon": 74.47843, "photo": 11, "jitter": 4, "quality": 70,
     "desc": "Sewage outside the hospital gate, third day now",
     "expect": "duplicate", "why": "same photo again, 11 m the other side"},
    {"key": "far_lookalike", "of": None, "cat": "drain_blockage", "ward": "Ward-9",
     "lat": 19.92000, "lon": 74.51000, "photo": 11, "jitter": 6, "quality": 55,
     "desc": "Drain overflowing in our lane too",
     "expect": "unique", "why": "identical photo but 4 km away -- merge must be refused"},
    {"key": "shivaji_nagar_dup", "of": "shivaji_nagar_waste",
     "cat": "missed_waste_collection", "ward": "Ward-6",
     "lat": 19.87908, "lon": 74.46808,
     "desc": "Ghanta gaadi has not come to Shivaji Nagar for four days, waste "
             "piling at the corner of the lane",
     "expect": "duplicate", "why": "no photo at all: merged on text overlap plus 12 m"},
]

# Budgets tried in order by the capacity search. The first that produces both
# deferral reasons and a rank inversion wins. Deliberately not a single magic
# number: the interesting figure moves whenever a cost above is edited, and the
# figures entered below are cost *inputs* -- the estimator adds its own reference
# lines on top, so the final rupee amount is always higher than the number typed.
CAPACITY_LADDER: list[tuple[float, float]] = [
    (60_000, 34.0), (48_000, 28.0), (35_000, 20.0), (75_000, 42.0),
    (28_000, 16.0), (100_000, 56.0),
]

RULE = "=" * 78


def head(title: str) -> None:
    print(f"\n{RULE}\n  {title}\n{RULE}")


def photo(seed: int, jitter: int = 0, quality: int = 92) -> bytes:
    """A deterministic synthetic 'photo', so perceptual hashes reproduce exactly.

    Real citizen photos cannot be committed to this repository, and a random
    image would make the duplicate cluster appear or vanish between runs. An
    8x8 block pattern rendered at 220 px and re-encoded at a lower JPEG quality
    is the same thing WhatsApp does to a forwarded picture, which is precisely
    the case the perceptual hash exists to survive.
    """
    from PIL import Image  # imported lazily so --no-photos works without Pillow

    random.seed(seed)
    img = Image.new("RGB", (220, 220))
    px = img.load()
    blocks = [[random.randint(0, 255) for _ in range(8)] for _ in range(8)]
    for y in range(220):
        for x in range(220):
            value = max(0, min(255, blocks[y * 8 // 220][x * 8 // 220] + jitter))
            px[x, y] = (value, value, value)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def wipe(conn) -> dict[str, int]:
    """Delete every row this script owns. Users and weights are left alone.

    Weights are append-only and version-numbered; deleting them would renumber
    versions that manifests already reference by number, so a reset that dropped
    them would corrupt the audit trail it is supposed to make readable.
    """
    from database import execute, query_one

    removed: dict[str, int] = {}
    for table in DEMO_TABLES:
        row = query_one(conn, f"SELECT COUNT(*) AS n FROM {table}")
        before = int(row["n"]) if row else 0
        if before:
            execute(conn, f"DELETE FROM {table}")
        removed[table] = before
    return {t: n for t, n in removed.items() if n}


def seed_wards(conn, estimates: bool) -> dict:
    """Register the ward labels the complaints refer to.

    Without ``--ward-estimates`` the rows carry a name and nothing else, which is
    the truth: no ward population, area or equity index exists in any Kopargaon
    file we were given. C3 Socio-Spatial Equity then reports itself as a wide
    low-confidence interval, and that is the honest state to demo. With the flag,
    plausible operator estimates go in -- still never marked ``verified``.
    """
    from services import wards

    for label in WARD_LABELS:
        payload: dict = {"name": label,
                         "source_note": "ward label referenced by seeded demo "
                                        "complaints; no published dataset supplied"}
        if estimates:
            population, area, equity = WARD_ESTIMATES[label]
            payload.update(population=population, area_sq_km=area,
                           equity_index=equity,
                           data_confidence="operator_entered",
                           source_note="operator estimate entered for the demo, "
                                       "not a published figure")
        wards.upsert_ward(conn, payload, actor="seed_demo_data")
    return wards.coverage(conn)


def seed_tickets(conn, with_photos: bool) -> tuple[dict, list[dict]]:
    """Create every complaint, then the follow-ups meant to collide with them.

    Returns (created_by_key, dedup_notes). The base cases are created first and
    in list order so the follow-ups always find a parent that already exists --
    dedup only ever looks backwards.
    """
    from services import tickets as ticket_service

    created: dict[str, dict] = {}
    for index, case in enumerate(CASES):
        uploads = []
        if with_photos and case.get("photo") is not None:
            uploads = [{"filename": f"{case['key']}.jpg",
                        "content": photo(case["photo"])}]
        created[case["key"]] = ticket_service.create_ticket(
            conn,
            {"citizen_phone": f"90000000{index:02d}", "channel": "web",
             "category": case["cat"], "description": case["desc"],
             "ward_id": case["ward"], "lat": case["lat"], "lon": case["lon"],
             **case.get("extra", {})},
            uploads, actor="seed_demo_data")
    return created, _seed_follow_ups(conn, created, with_photos)


def _seed_follow_ups(conn, created: dict, with_photos: bool) -> list[dict]:
    """The colliding reports, with actual-vs-expected recorded for each."""
    from services import tickets as ticket_service

    notes = []
    for index, case in enumerate(FOLLOW_UPS):
        uploads = []
        if with_photos and case.get("photo") is not None:
            uploads = [{"filename": f"{case['key']}.jpg",
                        "content": photo(case["photo"], case.get("jitter", 0),
                                         case.get("quality", 92))}]
        result = ticket_service.create_ticket(
            conn,
            {"citizen_phone": f"900000009{index}", "channel": "whatsapp",
             "category": case["cat"], "description": case["desc"],
             "ward_id": case["ward"], "lat": case["lat"], "lon": case["lon"]},
            uploads, actor="seed_demo_data")
        created[case["key"]] = result
        decision = result["dedup"]["decision"]
        expected = case["expect"]
        # Without photos the two pHash merges cannot happen, so the expectation
        # is relaxed rather than reported as a failure.
        if not with_photos and case.get("photo") is not None:
            expected = "unique"
        notes.append({
            "key": case["key"], "ref_no": result["ref_no"],
            "expected": expected, "actual": decision,
            "ok": decision == expected,
            "why": case["why"],
            "basis": (result["dedup"].get("match") or {}).get("basis"),
            "reason": (result["dedup"].get("match") or {}).get("reason")
                      or ((result["dedup"].get("near_misses") or [{}])[0]
                          .get("reason")),
            "report_count": result["dedup"]["action"].get("report_count"),
            "community_multiplier":
                result["dedup"]["action"].get("community_multiplier"),
        })
    return notes


def apply_costs(conn, created: dict) -> dict:
    """Enter the money a human had to measure, for the cases that have it.

    The split into material/labour/vehicle is not decoration: the estimator
    stores the entered lines so the figure can be reproduced later, and a demo
    that posted a single lump sum would hide that. Cases with ``cost: None`` are
    left untouched, which is what keeps them COST_INCOMPLETE with a NULL amount.
    """
    from services import tickets as ticket_service

    costed = uncosted = 0
    for case in CASES:
        entry = created[case["key"]]
        if case.get("cost") is None:
            uncosted += 1
            continue
        rupees, hours = case["cost"]
        ticket_service.update_cost_inputs(
            conn, entry["ticket_id"],
            {"runtime_material_cost": round(rupees * 0.55, 2),
             "runtime_labour_cost": round(rupees * 0.30, 2),
             "runtime_vehicle_cost": round(rupees * 0.15, 2),
             "crew_hours": hours,
             "runtime_labour_cost_note": "ward officer measurement entered "
                                         "during the demo seed"},
            actor="ward_engineer")
        costed += 1
    return {"costed": costed, "left_uncosted": uncosted}


def _interesting(result: dict) -> dict:
    """Score a candidate plan by what it lets a judge see, not by how full it is.

    A plan where the top-ranked tickets simply fit demonstrates nothing: it looks
    like a sorted list. The three properties below are the ones that only a real
    multi-constraint allocator can produce, so they are what the ladder searches
    for.
    """
    deferred_reasons = {row["reason_code"] for row in result["deferred"]}
    allocated_ranks = [row["rank"] for row in result["allocated"]]
    deferred_ranks = [row["rank"] for row in result["deferred"]]
    inversion = (bool(allocated_ranks) and bool(deferred_ranks)
                 and max(allocated_ranks) > min(deferred_ranks))
    return {
        "budget": result["capacity"]["budget_inr"],
        "hours": result["capacity"]["workforce_hours"],
        "scheduled": len(result["allocated"]),
        "deferred": len(result["deferred"]),
        "uncosted_deferral": "deferred_cost_not_estimated" in deferred_reasons,
        "outbid_deferral": ("deferred_capacity_used_by_higher_value_set"
                            in deferred_reasons),
        "rank_inversion": inversion,
        "inverted_by": (max(allocated_ranks) - min(deferred_ranks)
                        if inversion else 0),
        "solver": result["plan"]["solver"] if result.get("plan") else None,
        "outcome": result["plan"]["budget_outcome"] if result.get("plan") else None,
    }


def choose_capacity(conn, ladder: list[tuple[float, float]]) -> tuple[float, float, list[dict]]:
    """Dry-run the ladder and take the first budget that shows all three things.

    ``dry_run=True`` writes nothing at all, so this costs a few seconds of CPU and
    leaves no manifests behind. If none of the rungs qualifies, the first is used
    and the caller prints why -- picking a silently uninteresting plan and calling
    it a demo is worse than saying so.
    """
    from services import prioritisation

    tried = []
    for budget, hours in ladder:
        verdict = _interesting(prioritisation.run_triage(
            conn, budget=budget, workforce=hours, dry_run=True,
            actor="seed_demo_data"))
        tried.append(verdict)
        if (verdict["uncosted_deferral"] and verdict["outbid_deferral"]
                and verdict["rank_inversion"] and verdict["scheduled"] >= 3):
            return budget, hours, tried
    return ladder[0][0], ladder[0][1], tried


def run_and_explain(conn, budget: float, hours: float) -> dict:
    """Set today's capacity, plan the day for real, and store the explanations.

    Explanations are generated here rather than on first request so that a judge
    who opens the explanations page before anyone has run triage still sees the
    reasoning for today's plan. ``verified_by`` is filled because the whole point
    of that column is that a named person stands behind the figure.
    """
    from services import explain, prioritisation

    prioritisation.set_capacity(
        conn, budget_inr=budget, workforce_hours=hours,
        verified_by="ward_engineer", actor="seed_demo_data",
        note="figures entered by the demo seed; replace with the day's real "
             "sanctioned budget before any live use")
    result = prioritisation.run_triage(conn, budget=budget, workforce=hours,
                                       actor="seed_demo_data")
    stored = explain.explain_run(conn, result["run_id"], limit=200)
    return {"run": result, "explained": stored["count"]}


def report(conn, run: dict, notes: list[dict], tried: list[dict]) -> None:
    """Print what a judge will find, so a bad seed is obvious before the demo."""
    from services import explain, wards

    head("CAPACITY SEARCH -- dry runs, nothing written")
    print(f"{'INR':>8}{'hrs':>7}{'sched':>7}{'defer':>7}"
          f"{'uncosted':>10}{'outbid':>8}{'inversion':>11}  solver")
    for row in tried:
        print(f"{row['budget']:>8.0f}{row['hours']:>7.1f}{row['scheduled']:>7}"
              f"{row['deferred']:>7}{str(row['uncosted_deferral']):>10}"
              f"{str(row['outbid_deferral']):>8}"
              f"{str(row['rank_inversion']):>11}  {row['solver']}")

    head("TODAY'S PLAN")
    print(run["message"])
    capacity = run["capacity"]
    print(f"  capacity source : {capacity['source']}"
          f"  verified_by={capacity.get('verified_by')}")
    print(f"  solver          : {run['plan']['solver']}"
          f"  ({run['plan']['budget_outcome']}, "
          f"{run['plan']['states_explored']} states)")
    print(f"  weights         : version {run['weight_version']}")
    print(f"\n{'rank':<6}{'ref':<21}{'CCi':<9}{'INR':>8}{'h':>6}  "
          f"{'decision':<10}reason")
    for row in run["allocated"] + run["deferred"]:
        cost = "-" if row["estimated_cost_inr"] is None else f"{row['estimated_cost_inr']:.0f}"
        hrs = "-" if row["estimated_hours"] is None else f"{row['estimated_hours']:.1f}"
        flag = "*" if row["mandatory"] else " "
        print(f"{row['rank']:<5}{flag}{row['ref_no']:<21}{row['cci_score']:<9.4f}"
              f"{cost:>8}{hrs:>6}  {row['decision']:<10}{row['reason_code']}")
    print("  * committed before optimisation because the priority floor is "
          "critical")

    head("DEDUPLICATION -- expected vs actual")
    for note in notes:
        mark = "OK " if note["ok"] else "!! "
        print(f"{mark}{note['ref_no']}  expected {note['expected']:<10}"
              f"got {note['actual']:<10}{note['basis'] or '-'}")
        print(f"     {note['why']}")
        print(f"     {note['reason']}")
        if note["report_count"]:
            print(f"     parent now report_count={note['report_count']}, "
                  f"community multiplier {note['community_multiplier']}")

    head("WHAT THE UI WILL SHOW")
    coverage = wards.coverage(conn)
    print(f"  wards known         : {coverage['ward_count']}"
          f"  with population+area {coverage['with_population_and_area']}"
          f"  with equity index {coverage['with_equity_index']}")
    review = explain.explain_run(conn, run["run_id"], limit=3)
    print(f"  explanations stored : {review['count']} for this run"
          f" (method {review['method']})")
    for line in review["explanations"][:3]:
        print(f"\n  {line['ref_no']}  rank {line['rank']}  "
              f"driver {line['top_driver']}")
        print(f"    EN: {line['citizen_message_en']}")
        print(f"    MR: {line['citizen_message_mr']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Seed a demo complaint pool and run one day's triage.")
    parser.add_argument("--reset", action="store_true",
                        help="delete existing tickets, manifests, capacity and "
                             "wards first (weights and users are kept)")
    parser.add_argument("--db", metavar="PATH",
                        help="write to this sqlite file instead of the "
                             "configured one")
    parser.add_argument("--ward-estimates", action="store_true",
                        help="fill operator-estimated ward population, area and "
                             "equity index instead of leaving them NULL")
    parser.add_argument("--no-photos", action="store_true",
                        help="skip synthetic photos (also disables the two "
                             "perceptual-hash merges)")
    parser.add_argument("--budget", type=float,
                        help="today's budget in rupees; skips the capacity search")
    parser.add_argument("--hours", type=float,
                        help="today's crew-hours; skips the capacity search")
    parser.add_argument("--no-run", action="store_true",
                        help="seed the complaints only, leave triage unrun")
    return parser


def main(args: argparse.Namespace) -> int:
    from config import settings
    from database import get_conn, init_db, query_one

    init_db()
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[seed] database : {settings.DB_PATH}")
    print(f"[seed] uploads  : {settings.UPLOAD_DIR}")

    with get_conn() as conn:
        existing = query_one(conn, "SELECT COUNT(*) AS n FROM tickets")
        count = int(existing["n"]) if existing else 0
        if count and not args.reset:
            print(f"\n[seed] refusing: {count} tickets are already in this "
                  f"database.\n       Re-run with --reset to replace them, or "
                  f"--db <path> to seed elsewhere.\n       Nothing was changed.")
            return 2
        if args.reset:
            removed = wipe(conn)
            head("RESET")
            print("  deleted: " + (", ".join(f"{k}={v}" for k, v in
                                             removed.items()) or "nothing"))

        head("WARDS")
        coverage = seed_wards(conn, args.ward_estimates)
        print(f"  {coverage['ward_count']} wards registered; "
              f"{coverage['with_equity_index']} carry an equity index")
        if not args.ward_estimates:
            print("  population, area and equity index left NULL on purpose -- "
                  "no published Kopargaon ward dataset was supplied.\n"
                  "  C3 Socio-Spatial Equity will report itself as a wide, "
                  "low-confidence interval. Pass --ward-estimates to fill\n"
                  "  operator estimates instead (never marked verified).")

        head("COMPLAINTS")
        created, notes = seed_tickets(conn, not args.no_photos)
        print(f"  {len(CASES)} first reports + {len(FOLLOW_UPS)} follow-ups "
              f"created")

        from services import tickets as ticket_service

        confirmed = ticket_service.confirm_conditions(
            conn, created["approach_road_flood"]["ticket_id"],
            {"access_isolated": True}, actor="ward_officer")
        print(f"  officer confirms people are cut off by the road flooding: "
              f"floor -> {confirmed['priority_floor']}")
        print(f"    {confirmed.get('priority_floor_reason')}")

        costs = apply_costs(conn, created)
        print(f"  costs entered on {costs['costed']} tickets; "
              f"{costs['left_uncosted']} first reports deliberately left "
              f"uncosted (NULL, never 0),\n  plus the follow-up that was refused "
              f"a merge -- so the run reports one more than that.")

        if args.no_run:
            head("DONE -- triage not run (--no-run)")
            print("  POST /api/triage/run to plan the day.")
            return 0

        if args.budget or args.hours:
            from services import prioritisation

            budget = args.budget or CAPACITY_LADDER[0][0]
            hours = args.hours or CAPACITY_LADDER[0][1]
            tried = [_interesting(prioritisation.run_triage(
                conn, budget=budget, workforce=hours, dry_run=True,
                actor="seed_demo_data"))]
        else:
            budget, hours, tried = choose_capacity(conn, CAPACITY_LADDER)

        outcome = run_and_explain(conn, budget, hours)
        report(conn, outcome["run"], notes, tried)

        chosen = next((t for t in tried if t["budget"] == budget), None)
        if chosen and not (chosen["uncosted_deferral"] and chosen["outbid_deferral"]
                          and chosen["rank_inversion"]):
            head("WARNING")
            print("  This capacity does not produce all three teaching cases.\n"
                  "  The plan above is valid but less interesting; widen "
                  "CAPACITY_LADDER or adjust the costs in CASES.")

        head("DONE")
        print("  GET /api/triage/today          -- today's manifest")
        print("  GET /api/triage/priorities     -- the live queue")
        print("  GET /api/explain/run/latest    -- one line per ticket")
        print(f"  {outcome['explained']} explanations are already stored, so the "
              f"explanations page works before anyone clicks Run.")
    return 0


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    if parsed.db:
        # config reads the path once at import, so this must happen before any
        # first-party import -- which is why every import in this file is local.
        os.environ["CRPP_DB_PATH"] = parsed.db
    raise SystemExit(main(parsed))
