"""Walk the whole built-so-far backend in one run, printing what it decided.

Run it from the ``backend`` directory:

    python demo_pipeline.py

It uses a throwaway database (``demo_pipeline.db``) and a throwaway upload folder,
so it never touches real data. Nothing here is imported by the application; it
exists so a human can watch the pipeline think.

Covers: category canonicalisation, ward resolution with missing ward data, the two
SLA clocks, perceptual-hash deduplication with a proximity veto, recurrence after
a failed repair, cost estimation with unknown lines left NULL, the four fuzzy
criteria, and fuzzy-AHP weights with a consistency gate that refuses contradictory
judgements. Prioritisation and allocation are deliberately out of scope here -- they
are built, but they belong to the running server; see ``DEMO_SCRIPT.md``.
"""
from __future__ import annotations

import io
import os
import random
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# Demo artefacts live in the OS temp folder, not in the repo: nothing to clean up,
# nothing to accidentally commit, and no citizen photos anywhere near git.
SCRATCH = Path(tempfile.gettempdir()) / "crpp_demo"
DEMO_DB = SCRATCH / "demo_pipeline.db"
DEMO_UPLOADS = SCRATCH / "uploads"
os.environ["CRPP_DB_PATH"] = str(DEMO_DB)
os.environ["UPLOAD_DIR"] = str(DEMO_UPLOADS)

from database import get_conn, init_db  # noqa: E402
from services import dedup, tickets, wards, weights  # noqa: E402

RULE = "=" * 78


def head(title: str) -> None:
    print(f"\n{RULE}\n  {title}\n{RULE}")


def photo(seed: int, jitter: int = 0, quality: int = 92) -> bytes:
    """A deterministic synthetic 'photo' so hashes are reproducible."""
    from PIL import Image
    random.seed(seed)
    img = Image.new("RGB", (220, 220))
    px = img.load()
    blocks = [[random.randint(0, 255) for _ in range(8)] for _ in range(8)]
    for y in range(220):
        for x in range(220):
            v = max(0, min(255, blocks[y * 8 // 220][x * 8 // 220] + jitter))
            px[x, y] = (v, v, v)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def show_ingest(result: dict, label: str) -> None:
    print(f"\n[{label}] {result['ref_no']}  ->  {result['category']}"
          f"   dept {result['department_id']}")
    print(f"  citizen is told : {result['message']}")
    sla = result["sla"]
    target = sla.get("operational_target_minutes")
    print(f"  response clock  : {target} min target"
          f" ({sla.get('operational_status')})"
          if target is not None else
          "  response clock  : no published target for this category (NULL, not guessed)")
    if result["sla"].get("rts_time_limit_days"):
        print(f"  statutory clock : Right to Service {sla['rts_time_limit_days']} days"
              f" -> {sla.get('rts_status')}")
    print(f"  ward            : {result['ward']['ward_id']}"
          f" via {result['ward']['method']}"
          f" (confidence: {result['ward'].get('confidence')})")
    print(f"  priority floor  : {result['priority_floor']}"
          f"  <- {result['priority_floor_reason']}")
    cost = result["cost"]
    print(f"  cost            : {cost.get('estimated_cost_inr')} INR"
          f"  status {cost.get('cost_status')}"
          f"  confidence {cost.get('cost_confidence')}")
    print(f"  dedup           : {result['dedup']['decision']}"
          f"  -- {result['dedup'].get('reason')}")
    print("  criteria (fuzzy triangular intervals, width = what we don't know):")
    for name, score in result["criteria"].items():
        low, mid, high = score["tfn"]
        print(f"      {name:<11} [{low:.3f} {mid:.3f} {high:.3f}]"
              f"  conf {score['confidence']:.2f}   {score['source']}")
    if result["criteria_flags"]:
        print(f"  flags           : {', '.join(result['criteria_flags'])}")


def main() -> None:
    if SCRATCH.exists():
        shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    init_db()

    head("1. WEIGHTS -- where the ranking's priorities come from")
    with get_conn() as c:
        print(weights.explain_active(c)["summary"])
        print("\nA panel that contradicts itself is refused, not silently averaged:")
        bad = weights.derive_and_save(c, {
            "C2_safety vs C1_infra": "moderate",
            "C2_safety vs C3_equity": "inverse_strong",
            "C2_safety vs C4_cost": "strong",
            "C1_infra vs C3_equity": "equal_to_moderate",
            "C1_infra vs C4_cost": "moderate",
            "C3_equity vs C4_cost": "very_strong",
        }, label="contradictory_panel", created_by="demo")
        blame = bad["consistency"]["most_inconsistent"]
        print(f"  consistency ratio {bad['consistency']['consistency_ratio']}"
              f" (limit {bad['consistency']['threshold']}) -> "
              f"{'ADOPTED' if bad['activation']['activated'] else 'REFUSED'}")
        print(f"  the comparison to revisit: {blame['stated']} was rated "
              f"{blame['stated_value']}, but the other judgements imply "
              f"{blame['implied_value']} (via {blame['implied_via']})")
        print(f"  weights still in force: version {weights.active_vector(c)[1]}")

    head("2. INGEST -- four reports arriving at the council")
    with get_conn() as c:
        first = tickets.create_ticket(c, {
            "citizen_phone": "9876500001", "category": "sanitation",
            "description": "Drain overflowing outside the civil hospital gate, "
                           "sewage on the footpath",
            "ward_id": "Ward-4", "lat": 19.88110, "lon": 74.47850,
            "sensitive_site": "hospital", "affected_population": 1800,
        }, [{"filename": "drain.jpg", "content": photo(11)}], actor="demo")
        show_ingest(first, "A  new report, photo, near a hospital")

        near = tickets.create_ticket(c, {
            "citizen_phone": "9123400002", "category": "sanitation",
            "description": "Same drain overflowing near the hospital",
            "ward_id": "Ward-4", "lat": 19.88121, "lon": 74.47861,
        }, [{"filename": "again.jpg", "content": photo(11, jitter=8, quality=45)}],
            actor="demo")
        show_ingest(near, "B  same photo re-compressed, 15 m away")
        print(f"  merge effect    : parent now carries report_count="
              f"{near['dedup']['action'].get('report_count')},"
              f" community weight {near['dedup']['action'].get('community_multiplier')}")

        far = tickets.create_ticket(c, {
            "citizen_phone": "9123400003", "category": "sanitation",
            "description": "Drain overflowing",
            "ward_id": "Ward-9", "lat": 19.92000, "lon": 74.51000,
        }, [{"filename": "far.jpg", "content": photo(11, jitter=4, quality=60)}],
            actor="demo")
        show_ingest(far, "C  identical photo, 4 km away -- must NOT merge")
        vetoed = far["dedup"].get("near_misses") or []
        if vetoed:
            print(f"  veto recorded   : {vetoed[0].get('reason')}")

        flood = tickets.create_ticket(c, {
            "citizen_phone": "9123400004", "category": "waterlogging",
            "description": "Water logged across the main approach road, "
                           "vehicles cannot pass",
            "ward_id": "Ward-9", "lat": 19.86000, "lon": 74.47000,
        }, [], actor="demo")
        show_ingest(flood, "D  no photo at all -- still accepted")

    head("3. HUMAN INPUT CHANGES THE DECISION, AND SAYS SO")
    with get_conn() as c:
        print("An officer confirms people are cut off by the waterlogging:")
        before = flood["priority_floor"]
        after = tickets.confirm_conditions(
            c, flood["id"], {"access_isolated": True}, actor="ward_officer")
        print(f"  priority floor  : {before} -> {after['priority_floor']}")
        print(f"  because         : {after.get('priority_floor_reason')}")

        print("\nThe same officer measures what the drain repair actually cost:")
        costed = tickets.update_cost_inputs(c, first["id"], {
            "runtime_labour_cost": 1200, "runtime_material_cost": 850,
            "runtime_vehicle_cost": 400, "other_cost": 0,
        }, actor="ward_officer")
        print(f"  cost status     : {costed.get('cost_status_before')}"
              f" -> {costed.get('cost_status')}")
        print(f"  estimate        : {costed.get('estimated_cost_inr')} INR")

        print("\nWard data arrives, so equity stops being a guess:")
        wards.upsert_ward(c, {"id": "W4", "name": "Ward-4", "population": 6200,
                              "area_sq_km": 0.78, "equity_index": 0.72,
                              "data_confidence": "operator_entered"}, "demo")
        wards.upsert_ward(c, {"id": "W9", "name": "Ward-9", "population": 4100,
                              "area_sq_km": 1.35, "equity_index": 0.41,
                              "data_confidence": "operator_entered"}, "demo")
        wards.upsert_ward(c, {"id": "W1", "name": "Ward-1", "population": 5800,
                              "area_sq_km": 0.62, "data_confidence": "operator_entered"},
                         "demo")
        rescored = tickets.rescore_ticket(c, first["id"])
        detail = tickets.get_ticket(c, first["id"])
        eq = detail["criteria"]["C3_equity"]
        print(f"  C3_equity now   : {[round(v, 3) for v in eq['tfn']]}"
              f"  conf {eq['confidence']}   {eq['source']}")
        print(f"  overall conf    : {rescored['overall_confidence']}")

    head("4. RECURRENCE -- a repair that failed is not a duplicate")
    with get_conn() as c:
        tickets.update_status(c, first["id"], "scored", actor="demo")
        tickets.update_status(c, first["id"], "scheduled", actor="demo")
        tickets.update_status(c, first["id"], "dispatched", actor="demo")
        tickets.update_status(c, first["id"], "resolved", actor="crew_1",
                              note="drain cleared")
        again = tickets.create_ticket(c, {
            "citizen_phone": "9123400005", "category": "sanitation",
            "description": "The same drain is overflowing again",
            "ward_id": "Ward-4", "lat": 19.88113, "lon": 74.47852,
        }, [{"filename": "relapse.jpg", "content": photo(11, jitter=3)}],
            actor="demo")
        print(f"  decision        : {again['dedup']['decision']}"
              f" (parent {again['dedup'].get('parent_id') and 'linked' or 'none'})")
        print(f"  is_duplicate    : {again['is_duplicate']}"
              "   <- keeps its own place in the queue")
        print(f"  citizen is told : {again['message']}")

    head("5. WHAT AN OFFICER SEES, AND WHAT A REFUSAL LOOKS LIKE")
    with get_conn() as c:
        listing = tickets.list_tickets(c)
        print(f"  queue ({listing['total']} live, duplicates hidden):")
        for row in listing["items"]:
            print(f"    {row['ref_no']}  {row['category']:<22}"
                  f" {row['status']:<10} floor={str(row['priority_floor']):<8}"
                  f" ward={row['ward_id']}"
                  f" cost={row['estimated_cost_inr']}")
        print("\n  an impossible status jump is refused, not logged as fact:")
        print("   ", tickets.update_status(c, again["id"], "resolved"))
        print(f"\n  audit trail for {first['ref_no']}:")
        for event in tickets.get_ticket(c, first["id"])["events"]:
            print(f"    {event['created_at'][11:19]}  {event['event']:<26}"
                  f" {str(event['from_value'] or ''):>10} -> "
                  f"{str(event['to_value'] or ''):<10} by {event['actor']}")
        print(f"\n  ward data coverage (the honest gap):")
        cov = wards.coverage(c)
        print(f"    {cov['ward_count']} wards known,"
              f" {cov['with_population_and_area']} with population+area,"
              f" {cov['with_equity_index']} with an equity index")

    head("DONE")
    print(f"database : {DEMO_DB}")
    print(f"uploads  : {DEMO_UPLOADS}")
    # Scope of THIS script, not of the platform: prioritisation, allocation, the
    # explain endpoints and the audit chain are all built and live on the running
    # server. They are absent here because this walkthrough deliberately stops at
    # the ingest boundary, and printing "not yet built" would misstate that.
    print("not shown here (they need the running server, not this scratch DB):"
          " prioritisation (fuzzy TOPSIS), allocation (knapsack),"
          " the /api/explain endpoints, and the audit hash chain.")
    print("for those: python -m uvicorn main:app --port 8000, then"
          " GET /api/triage/today -- see DEMO_SCRIPT.md")


if __name__ == "__main__":
    main()
