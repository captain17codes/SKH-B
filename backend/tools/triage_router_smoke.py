"""Exercise routers/triage.py without FastAPI installed.

The sandbox cannot reach PyPI, so ``fastapi`` and ``pydantic`` are unavailable and
the router can otherwise only be AST-checked. AST parsing proves the file is
syntactically valid; it proves nothing about whether the response bodies the React
app destructures are actually populated. That is the part worth testing, so this
harness supplies just enough of both libraries for the module to import, then calls
the endpoint functions directly against a throwaway database.

Run:  python3 tools/triage_router_smoke.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCRATCH = Path(tempfile.gettempdir()) / "crpp_router_smoke"
shutil.rmtree(SCRATCH, ignore_errors=True)
(SCRATCH / "uploads").mkdir(parents=True, exist_ok=True)
os.environ["CRPP_DB_PATH"] = str(SCRATCH / "smoke.db")
os.environ["UPLOAD_DIR"] = str(SCRATCH / "uploads")
sys.path.insert(0, str(BACKEND))


# --------------------------------------------------------------------------
# minimal fastapi / pydantic stand-ins
# --------------------------------------------------------------------------
class HTTPException(Exception):
    def __init__(self, status_code: int, detail: str = "") -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class _Router:
    def __init__(self, **kw):
        self.kw = kw
        self.routes = []

    def _record(self, method, path):
        def decorate(fn):
            self.routes.append((method, self.kw.get("prefix", "") + path,
                                fn.__name__))
            return fn
        return decorate

    def get(self, path, **_):
        return self._record("GET", path)

    def post(self, path, **_):
        return self._record("POST", path)

    def put(self, path, **_):
        return self._record("PUT", path)

def _Depends(dependency=None):
    return None


def _Query(default=None, **_):
    return default


def _Field(default=None, **_):
    return default


class _BaseModel:
    """Enough of pydantic to construct a payload and dump it back.

    Field defaults are read off the class, so ``Optional[str] = Field(None)``
    behaves as it would under real pydantic. No validation is attempted: this
    harness is testing the router's shaping, not pydantic's coercion.
    """

    def __init__(self, **kwargs):
        for name in getattr(type(self), "__annotations__", {}):
            setattr(self, name, kwargs.get(name, getattr(type(self), name, None)))
        for key, value in kwargs.items():
            setattr(self, key, value)

    def model_dump(self):
        return {name: getattr(self, name, None)
                for name in getattr(type(self), "__annotations__", {})}


fastapi = types.ModuleType("fastapi")
fastapi.APIRouter = _Router
fastapi.Depends = _Depends
fastapi.Query = _Query
fastapi.HTTPException = HTTPException
fastapi.Request = type("Request", (), {"state": None, "client": None})
sys.modules["fastapi"] = fastapi

pydantic = types.ModuleType("pydantic")
pydantic.BaseModel = _BaseModel
pydantic.Field = _Field
sys.modules["pydantic"] = pydantic

from database import get_conn, init_db  # noqa: E402
from routers import triage  # noqa: E402
from services import prioritisation as svc  # noqa: E402
from services import tickets as ticket_service  # noqa: E402


class FakeRequest:
    """Stands in for ``fastapi.Request`` in the actor helper."""
    def __init__(self, host="203.0.113.7"):
        self.state = types.SimpleNamespace(user=None)
        self.client = types.SimpleNamespace(host=host)


def seed(conn) -> list[dict]:
    """Five competing complaints, three of them costed. Same fixture as the
    service self-test, so a discrepancy points at the router rather than the
    engine."""
    cases = [
        ("live electrical wire down across the lane", "road_damage", "Ward-4",
         19.8811, 74.4785, {"sensitive_site": "hospital",
                            "affected_population": 2400}),
        ("drain blocked, sewage on the street", "drain_blockage", "Ward-4",
         19.8830, 74.4800, {"affected_population": 900}),
        ("pothole on the approach road", "road_damage", "Ward-9",
         19.8600, 74.4700, {"affected_population": 200}),
        ("street light out near the school", "streetlight_failure", "Ward-9",
         19.8620, 74.4720, {"sensitive_site": "school",
                            "affected_population": 400}),
        ("water not coming since morning", "water_distribution_failure",
         "Ward-2", 19.8700, 74.4600, {"affected_population": 1500}),
    ]
    made = []
    for i, (desc, category, ward, lat, lon, extra) in enumerate(cases):
        made.append(ticket_service.create_ticket(
            conn, {"citizen_phone": f"90000000{i:02d}", "category": category,
                   "description": desc, "ward_id": ward, "lat": lat, "lon": lon,
                   **extra}, [], actor="smoke"))
    for entry, cost, hours in zip(made, (18_000, 9_000, 4_500, None, None),
                                  (9.0, 5.0, 3.0, None, None)):
        if cost is None:
            continue
        ticket_service.update_cost_inputs(
            conn, entry["ticket_id"],
            {"runtime_material_cost": cost * 0.55,
             "runtime_labour_cost": cost * 0.30,
             "runtime_vehicle_cost": cost * 0.15,
             "crew_hours": hours}, actor="smoke")
    return made

# Exactly what the shipped React components destructure. If any of these stops
# being present the Triage panel breaks silently, showing "undefined" rather than
# an error, so they are asserted by name rather than eyeballed.
RUN_KEYS = {"message", "prioritized_count", "scheduled_count", "deferred_count",
            "manifest_id", "total_cci_score"}
MANIFEST_KEYS = {"manifest_id", "dispatch_date", "budget_cap",
                 "workforce_cap_hours", "solver_status", "summary", "scheduled",
                 "deferred"}
ITEM_KEYS = {"ticket_id", "selected", "cost_estimate", "hours_estimate",
             "category", "cci_score", "citizen_phone", "lat", "lon", "ward_id"}
PRIORITY_KEYS = {"id", "citizen_phone", "category", "cci_score", "status",
                 "community_multiplier", "ward_id", "lat", "lon"}


def main() -> None:
    init_db()
    request = FakeRequest()
    with get_conn() as conn:
        made = seed(conn)
        print(f"seeded {len(made)} tickets")

        routes = sorted(triage.router.routes)
        print("\nregistered routes:")
        for method, path, name in routes:
            print(f"   {method:<4} {path:<34} {name}")
        assert ("POST", "/api/triage/run", "run") in routes
        assert ("GET", "/api/triage/today", "manifest_today") in routes
        assert ("GET", "/api/triage/manifest/{manifest_date}",
                "manifest_for_date") in routes
        assert ("GET", "/api/triage/priorities", "priorities") in routes

        # --- capacity ------------------------------------------------------
        before = triage.capacity(conn=conn)
        assert before["source"].startswith("configured_default"), before
        stored = triage.put_capacity(
            triage.CapacityPayload(budget_inr=25_000, workforce_hours=18,
                                   verified_by="ward_engineer_smoke",
                                   note="smoke figures"),
            request, conn=conn)
        print(f"\ncapacity before run: {before['source']} "
              f"-> after PUT: {stored['source']} verified={stored['verified']}")
        assert stored["budget_inr"] == 25_000 and stored["verified"] is True

        # --- 404 before any run --------------------------------------------
        try:
            triage.manifest_today(conn=conn)
        except HTTPException as exc:
            assert exc.status_code == 404, exc
            print(f"GET /today before any run -> 404 {exc.detail}")
        else:
            raise AssertionError("expected 404 before triage has run")

        for bad in ("29-08-2026", "today", "2026-8-1"):
            try:
                triage.manifest_for_date(bad, conn=conn)
            except HTTPException as exc:
                assert exc.status_code == 400, (bad, exc)
            else:
                raise AssertionError(f"{bad} should have been rejected")
        print("malformed dates rejected with 400  OK")

        # --- dry run writes nothing ----------------------------------------
        preview = triage.run(
            triage.TriageRunRequest(daily_budget=200_000, daily_workforce=200,
                                    dry_run=True), request, conn=conn)
        assert preview["manifest_id"] is None and preview["persisted"] is False
        assert not triage.svc.list_manifests(conn), "dry run persisted a manifest"
        print(f"\ndry run at INR 200000/200h -> "
              f"{preview['scheduled_count']} scheduled, nothing written  OK")

        # --- the real run --------------------------------------------------
        result = triage.run(triage.TriageRunRequest(daily_budget=25_000,
                                                    daily_workforce=18),
                            request, conn=conn)
        missing = RUN_KEYS - set(result)
        assert not missing, f"POST /run lost frontend keys: {missing}"
        print("\nPOST /api/triage/run")
        for key in ("message", "prioritized_count", "scheduled_count",
                    "deferred_count", "manifest_id", "total_cci_score",
                    "solver_status", "weight_version"):
            print(f"   {key:<19} {result[key]}")
        assert result["prioritized_count"] == len(made)
        assert (result["scheduled_count"] + result["deferred_count"]
                == result["prioritized_count"])
        assert 0.0 < result["total_cci_score"] <= 1.0
        assert result["manifest_id"]

        # A dry run at far higher capacity must schedule at least as much as the
        # real run did. When it schedules less, something is silently dropping
        # tickets between runs -- the exact bug the queue filter had.
        assert preview["scheduled_count"] >= result["scheduled_count"], (
            preview["scheduled_count"], result["scheduled_count"])

        # --- read it back --------------------------------------------------
        manifest = triage.manifest_today(conn=conn)
        missing = MANIFEST_KEYS - set(manifest)
        assert not missing, f"GET /today lost frontend keys: {missing}"
        assert manifest["manifest_id"] == result["manifest_id"]
        assert manifest["budget_cap"] == 25_000.0
        assert manifest["workforce_cap_hours"] == 18.0
        assert manifest["summary"]["total_tickets"] == len(made)
        assert (manifest["summary"]["scheduled"] == len(manifest["scheduled"])
                == result["scheduled_count"])
        assert (manifest["summary"]["deferred"] == len(manifest["deferred"])
                == result["deferred_count"])
        print(f"\nGET /api/triage/today -> {manifest['solver_status']}, "
              f"INR {manifest['budget_used']}/{manifest['budget_cap']}, "
              f"{manifest['workforce_used']}/"
              f"{manifest['workforce_cap_hours']}h, weights v"
              f"{manifest['weight_version']}, capacity "
              f"{manifest['capacity_source']} "
              f"(verified by {manifest['capacity_verified_by']})")

        print(f"\n{'rank':<5}{'ticket':<14}{'CCi':<9}{'INR':<9}{'h':<6}"
              f"{'sel':<6}reason")
        for item in manifest["scheduled"] + manifest["deferred"]:
            missing = ITEM_KEYS - set(item)
            assert not missing, f"manifest item lost keys: {missing}"
            cost = "-" if item["cost_estimate"] is None else f"{item['cost_estimate']:.0f}"
            hours = "-" if item["hours_estimate"] is None else f"{item['hours_estimate']:.1f}"
            print(f"{item['rank']:<5}{item['ticket_id'][:12]:<14}"
                  f"{item['cci_score']:<9.4f}{cost:<9}{hours:<6}"
                  f"{str(item['selected']):<6}{item['reason_code']}")
            # Every line must justify itself, including the deferred ones, and
            # must name the criterion that drove the score.
            assert item["reason_code"] and item["reason_text"]
            assert item["top_driver"], item["ticket_id"]
            assert item["attribution"], item["ticket_id"]
            total = sum(a["contribution"] for a in item["attribution"])
            assert abs(total - item["cci_base"]) < 1e-5, (item["ticket_id"],
                                                          total,
                                                          item["cci_base"])
            # A cost of zero and an unknown cost must never collapse into each
            # other: one is free work, the other is work nobody has costed.
            if item["reason_code"] == "deferred_cost_not_estimated":
                assert item["cost_estimate"] is None, item
            else:
                assert item["cost_estimate"] is not None, item
        assert all(i["selected"] for i in manifest["scheduled"])
        assert not any(i["selected"] for i in manifest["deferred"])

        spent = sum(i["cost_estimate"] for i in manifest["scheduled"])
        hours = sum(i["hours_estimate"] for i in manifest["scheduled"])
        assert spent <= manifest["budget_cap"] + 1e-6, (spent,
                                                        manifest["budget_cap"])
        assert hours <= manifest["workforce_cap_hours"] + 1e-6
        print(f"scheduled work fits the cap: INR {spent:.0f} <= "
              f"{manifest['budget_cap']:.0f}, {hours:.1f}h <= "
              f"{manifest['workforce_cap_hours']:.1f}h  OK")

        by_date = triage.manifest_for_date(manifest["dispatch_date"], conn=conn)
        assert by_date["manifest_id"] == manifest["manifest_id"]
        by_id = triage.manifest_by_id(manifest["manifest_id"], conn=conn)
        assert by_id["manifest_id"] == manifest["manifest_id"]
        try:
            triage.manifest_by_id("no-such-manifest", conn=conn)
        except HTTPException as exc:
            assert exc.status_code == 404
        print("/manifest/{date}, /manifest-by-id/{id} and its 404 agree  OK")

        # --- priorities ----------------------------------------------------
        queue = triage.priorities(limit=20, conn=conn)
        assert queue["total"] == len(queue["tickets"]) == len(made)
        for row in queue["tickets"]:
            missing = PRIORITY_KEYS - set(row)
            assert not missing, f"priorities lost frontend keys: {missing}"
        scores = [r["cci_score"] for r in queue["tickets"] if r["scored"]]
        assert scores == sorted(scores, reverse=True), scores
        print(f"\nGET /api/triage/priorities -> {queue['total']} tickets, "
              f"{queue['unscored']} unscored, top "
              f"{queue['tickets'][0]['category']} at "
              f"{queue['tickets'][0]['cci_score']:.4f} "
              f"({queue['tickets'][0]['status']})")

        filtered = triage.priorities(status="deferred", conn=conn)
        assert all(t["status"] == "deferred" for t in filtered["tickets"])
        assert filtered["total"] == result["deferred_count"], (
            filtered["total"], result["deferred_count"])
        print(f"status=deferred filter -> {filtered['total']} tickets, "
              f"matching the run's deferred count  OK")

        # --- re-run appends, never overwrites -------------------------------
        second = triage.run(triage.TriageRunRequest(daily_budget=120_000,
                                                    daily_workforce=90),
                            request, conn=conn)
        listing = triage.manifests(conn=conn)
        assert listing["count"] == 2, listing["count"]
        assert second["manifest_id"] != result["manifest_id"]
        newest = triage.manifest_today(conn=conn)
        assert newest["manifest_id"] == second["manifest_id"], (
            "GET /today must return the newest run for the date")
        # The first manifest is still readable exactly as issued.
        first_again = triage.manifest_by_id(result["manifest_id"], conn=conn)
        assert first_again["budget_cap"] == 25_000.0
        assert (first_again["summary"]["scheduled"]
                == result["scheduled_count"]), "history was rewritten"
        print(f"\nre-run at INR 120000/90h -> {second['scheduled_count']} "
              f"scheduled (was {result['scheduled_count']}); "
              f"{listing['count']} manifests on record and the first is "
              f"unchanged  OK")
        assert second["scheduled_count"] >= result["scheduled_count"]

        print("\nsmoke test passed.")


if __name__ == "__main__":
    main()

