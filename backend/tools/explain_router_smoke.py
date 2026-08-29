"""Exercise routers/explain.py without FastAPI installed.

Same reason as ``triage_router_smoke.py``: the sandbox cannot reach PyPI, so an
AST check is the most the import auditor can prove. What matters about this router
is not that it parses but that a citizen-facing GET returns a filled-in paragraph,
that ``latest`` resolves, that an unknown ticket 404s while an unscored one does
not, and that re-reading does not grow the table. So the fastapi/pydantic stubs
from the triage harness are reused and the endpoint functions are called directly.

Run:  python3 tools/explain_router_smoke.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tools"))

# Importing the triage harness installs the fastapi/pydantic stand-ins into
# sys.modules and points CRPP_DB_PATH/UPLOAD_DIR at its own throwaway directory,
# which it wipes first. That has to happen before any first-party import, because
# ``config`` reads the database path once.
import triage_router_smoke as harness  # noqa: E402

HTTPException = harness.HTTPException

from database import get_conn, init_db  # noqa: E402
from routers import explain as api  # noqa: E402
from routers import triage  # noqa: E402


def _expect_404(fn, *args, **kwargs) -> str:
    try:
        fn(*args, **kwargs)
    except HTTPException as exc:
        assert exc.status_code == 404, exc
        return exc.detail
    raise AssertionError(f"{getattr(fn, '__name__', fn)} should have raised 404")


def main() -> None:
    init_db()
    request = harness.FakeRequest()
    with get_conn() as conn:
        made = harness.seed(conn)
        ids = [entry["ticket_id"] for entry in made]

        routes = sorted(api.router.routes)
        print("registered routes:")
        for method, path, name in routes:
            print(f"   {method:<4} {path:<40} {name}")
        assert ("GET", "/api/explain/{ticket_id}", "explain") in routes
        assert ("GET", "/api/explain/{ticket_id}/citizen", "citizen") in routes
        assert ("GET", "/api/explain/{ticket_id}/history", "history") in routes
        assert ("GET", "/api/explain/run/{run_id}", "run_review") in routes
        assert ("GET", "/api/explain/run/{run_id}/shap", "run_shap") in routes
        # ``/run/{run_id}`` and ``/{ticket_id}/citizen`` are both two segments, so
        # a request for /api/explain/run/citizen is ambiguous. The literal-prefixed
        # route must be declared first for the resolution to be deterministic.
        order = [path for _, path, _ in api.router.routes]
        assert (order.index("/api/explain/run/{run_id}")
                < order.index("/api/explain/{ticket_id}/citizen")), order

        # --- before any run --------------------------------------------------
        detail = _expect_404(api.run_review, "latest", conn=conn)
        print(f"\nrun review before any run -> 404 {detail}")
        detail = _expect_404(api.explain, "no-such-ticket", request, conn=conn)
        print(f"unknown ticket -> 404 {detail}")

        # An unscored ticket is not an error: the citizen is owed a sentence.
        body = api.explain(ids[0], request, conn=conn)
        assert body["scored"] is False, body
        assert body["citizen_message_en"] and body["citizen_message_mr"]
        assert body["requested_by"].startswith("anonymous_")
        print("unscored ticket -> 200 with scored=false and text in both "
              "languages  OK")
        cit = api.citizen(ids[0], lang="mr", conn=conn)
        assert cit["message"] and "{" not in cit["message"]
        assert cit["translation_status"] == api.svc.TRANSLATION_STATUS
        assert cit["scored"] is False
        print(f"   mr: {cit['message'][:90]}...")

        # --- run triage, then explain it -------------------------------------
        triage.put_capacity(
            triage.CapacityPayload(budget_inr=25_000, workforce_hours=18,
                                   verified_by="ward_engineer_smoke"),
            request, conn=conn)
        run = triage.run(triage.TriageRunRequest(daily_budget=25_000,
                                                 daily_workforce=18),
                         request, conn=conn)
        print(f"\n{run['message']}")

        review = api.run_review("latest", conn=conn)
        assert review["count"] == len(made), review["count"]
        assert review["run_id"] == run["run_id"], (review["run_id"],
                                                   run["run_id"])
        by_id = api.run_review(run["run_id"], conn=conn)
        assert by_id["run_id"] == review["run_id"]
        print(f"\nGET /api/explain/run/latest -> {review['count']} lines, "
              f"run {review['run_id'][:8]}, method {review['method']}")

        print(f"\n{'rank':<5}{'ref':<20}{'decision':<11}{'driver':<12}citizen sentence")
        for line in review["explanations"]:
            for key in ("ticket_id", "ref_no", "rank", "decision",
                        "reason_code", "top_driver", "citizen_message_en",
                        "citizen_message_mr"):
                assert line.get(key) is not None, (key, line)
            for text in (line["citizen_message_en"], line["citizen_message_mr"]):
                assert "{" not in text and "}" not in text, text
                assert text.strip().endswith((".", "।")), text
            print(f"{line['rank']:<5}{line['ref_no']:<20}"
                  f"{line['decision']:<11}{line['top_driver']:<12}"
                  f"{line['citizen_message_en'][:60]}...")

        # --- one ticket in full ----------------------------------------------
        outbid = next(l for l in review["explanations"]
                      if l["reason_code"]
                      == "deferred_capacity_used_by_higher_value_set")
        full = api.explain(outbid["ticket_id"], request, conn=conn)
        assert full["scored"] is True
        assert full["attribution"]["reconciles"], full["attribution"]
        assert full["capacity_went_to"], "an outbid ticket must name its rivals"
        assert full["what_would_change_it"]["changeable"] is True
        assert full["officer_rationale"].startswith(str(full["ref_no"]))
        print(f"\nGET /api/explain/{outbid['ref_no']}")
        print(f"   rank {full['rank']} of {full['of_candidates']}, CCi "
              f"{full['cci_score']}, driver "
              f"{full['attribution']['top_driver']}, weights v"
              f"{full['weight_version']}")
        print(f"   capacity went to: "
              + ", ".join(f"{r['ref_no']} (INR {r['cost_inr']:.0f})"
                          for r in full["capacity_went_to"]))
        print(f"   lever: {full['what_would_change_it']['what_would_change_it']}")

        # A scheduled ticket ranked below a deferred one must say why, or the
        # allocation looks arbitrary to the person reading it.
        jumped = [l for l in review["explanations"]
                  if l["decision"] == "allocated"
                  and l["rank"] > min(x["rank"] for x in review["explanations"]
                                      if x["decision"] != "allocated")]
        if jumped:
            body = api.explain(jumped[0]["ticket_id"], request, conn=conn)
            assert body["outranked_deferred_count"] > 0, body
            assert "rank order" in body["citizen_message_en"], (
                "a ticket scheduled ahead of a better-ranked one must explain "
                "that the day is packed by combination, not by list order")
            print(f"\nrank {body['rank']} was scheduled while "
                  f"{body['outranked_deferred_count']} better-ranked "
                  f"complaint(s) were not, and the message says so  OK")

        # --- citizen endpoint, both languages --------------------------------
        for lang in ("en", "mr"):
            cit = api.citizen(outbid["ticket_id"], lang=lang, conn=conn)
            assert cit["language"] == lang
            assert cit["outcome_sentence"] and cit["next_step"]
            assert cit["message"].startswith(cit["outcome_sentence"])
            assert cit["message"].endswith(cit["next_step"])
            assert cit["decision"] == "deferred"
        assert (api.citizen(outbid["ticket_id"], lang="mr",
                            conn=conn)["translation_status"]
                == api.svc.TRANSLATION_STATUS)
        assert (api.citizen(outbid["ticket_id"], lang="en",
                            conn=conn)["translation_status"]
                == "source_language")
        print("citizen endpoint: en is source_language, mr is stamped "
              f"{api.svc.TRANSLATION_STATUS}  OK")

        # --- history: reads do not accumulate, re-runs do --------------------
        hist = api.history(outbid["ticket_id"], conn=conn)
        assert hist["count"] == 1, hist["count"]
        api.explain(outbid["ticket_id"], request, conn=conn)
        api.citizen(outbid["ticket_id"], conn=conn)
        again = api.history(outbid["ticket_id"], conn=conn)
        assert again["count"] == 1, ("re-reading an explanation must not grow "
                                     "the table", again["count"])
        second = triage.run(triage.TriageRunRequest(daily_budget=120_000,
                                                    daily_workforce=90),
                            request, conn=conn)
        api.run_review(second["run_id"], conn=conn)
        after = api.history(outbid["ticket_id"], conn=conn)
        assert after["count"] == 2, after["count"]
        assert after["explanations"][0]["run_id"] == run["run_id"], (
            "the first explanation must survive verbatim")
        print(f"history: {again['count']} row after repeated reads, "
              f"{after['count']} after a second run, first preserved  OK")

        # A named older run must still explain itself under the old plan.
        old = api.explain(outbid["ticket_id"], request, run_id=run["run_id"],
                          conn=conn)
        assert old["run_id"] == run["run_id"]
        assert old["reason_code"] == outbid["reason_code"], (
            "asking for a past run must return that run's decision")
        print("a past run still explains itself under its own decision  OK")

        # --- shap refuses, never 500s ----------------------------------------
        shap = api.run_shap("latest", conn=conn)
        assert shap["available"] is False
        assert shap["reason"] and shap["exact_attribution_unaffected"] is True
        print(f"\nGET /run/latest/shap -> available=false, reason: "
              f"{shap['reason']}")

        print("\nsmoke test passed.")


if __name__ == "__main__":
    main()
