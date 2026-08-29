"""Prove the audit chain detects tampering, without FastAPI installed.

The other smoke tools check that a router shapes its output correctly. This one
has a harder job: an audit chain that *reports* `ok: true` is worthless unless it
also reports `ok: false` when it should. So the interesting half of this script is
deliberate vandalism -- edit a payload in place, remove a row from the middle --
followed by checking that `verify` points at the right `seq` and calls the break
by the right name.

Run:  python tools/audit_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tools"))

# Installs the fastapi/pydantic stand-ins and redirects CRPP_DB_PATH/UPLOAD_DIR
# at a throwaway directory it wipes first. Must precede every first-party import.
import triage_router_smoke as harness  # noqa: E402

HTTPException = harness.HTTPException

from database import get_conn, init_db  # noqa: E402
from routers import audit as api  # noqa: E402
from services import audit as svc  # noqa: E402
from services import explain as explain_svc  # noqa: E402
from services import prioritisation as triage_svc  # noqa: E402
from services import weights as weight_svc  # noqa: E402


def _expect_404(fn, *args, **kwargs) -> str:
    try:
        fn(*args, **kwargs)
    except HTTPException as exc:
        assert exc.status_code == 404, exc
        return exc.detail
    raise AssertionError(f"{getattr(fn, '__name__', fn)} should have raised 404")


def _seqs(conn) -> list[int]:
    return [int(r["seq"]) for r in
            conn.execute("SELECT seq FROM audit_log ORDER BY seq").fetchall()]


def main() -> None:
    init_db()
    with get_conn() as conn:
        # ---- an empty chain is honest, not broken ---------------------------
        empty = api.verify(conn=conn)
        assert empty["ok"] is True, empty
        assert empty["entries"] == 0, empty
        assert empty["tip_hash"] is None, empty
        print(f"empty chain -> ok={empty['ok']}, {empty['message']}")

        routes = sorted(api.router.routes)
        print("\nregistered routes:")
        for method, path, name in routes:
            print(f"   {method:<4} {path:<45} {name}")
        for expected in (("GET", "/api/audit/verify", "verify"),
                         ("GET", "/api/audit/recent", "recent"),
                         ("GET", "/api/audit/entity/{entity_type}/{entity_id}",
                          "entity_history"),
                         ("GET", "/api/audit/export", "export")):
            assert expected in routes, (expected, routes)

        # ---- the five hooked actions ---------------------------------------
        made = harness.seed(conn)          # ticket.created x5, cost edits x3
        run = triage_svc.run_triage(conn, actor="audit_smoke")

        # explanation.stored is hooked inside explain._store, which only runs on
        # a persisting explain call -- so the hook is exercised the way the
        # /explanations page exercises it, not by poking the table.
        explain_svc.explain_ticket(conn, made[0]["ticket_id"])

        version = conn.execute("SELECT version FROM criteria_weights "
                               "ORDER BY version DESC LIMIT 1").fetchone()
        assert version, "no criteria_weights rows -- init_db did not seed weights"
        activated = weight_svc.activate_version(conn, int(version["version"]),
                                                "audit_smoke")
        assert activated.get("activated") is True, activated

        stats = api.stats(conn=conn)
        by_action = {row["action"]: row["count"] for row in stats["by_action"]}
        print(f"\nentries after seeding: {stats['entries']}")
        for action, count in sorted(by_action.items()):
            print(f"   {action:<32} {count}")
        for action in (svc.ACTION_TICKET_CREATED, svc.ACTION_COST_EDITED,
                       svc.ACTION_TRIAGE_RUN, svc.ACTION_WEIGHTS_ACTIVATED,
                       svc.ACTION_EXPLANATION_STORED):
            assert by_action.get(action), (
                f"{action} was never recorded -- its hook is not wired")
        assert by_action[svc.ACTION_TICKET_CREATED] == len(made), by_action
        print("all five hooked actions appear in the chain  OK")

        # ---- genesis and links --------------------------------------------
        first = conn.execute("SELECT prev_hash FROM audit_log ORDER BY seq "
                             "LIMIT 1").fetchone()
        assert first["prev_hash"] == svc.GENESIS_PREV_HASH, first["prev_hash"]
        assert first["prev_hash"] == "0" * 64
        print(f"genesis prev_hash is 64 zeros  OK")

        good = api.verify(conn=conn)
        assert good["ok"] is True, good
        assert good["first_broken_seq"] is None, good
        assert len(good["tip_hash"]) == 64, good
        print(f"\nverify -> ok, {good['entries']} entries, "
              f"tip seq {good['tip_seq']} hash {good['tip_hash'][:12]}...")

        # ---- the reads the compliance page makes ---------------------------
        ticket_id = made[0]["ticket_id"]
        history = api.entity_history(svc.ENTITY_TICKET, ticket_id, conn=conn)
        actions = [e["action"] for e in history["entries"]]
        print(f"\nentity/{svc.ENTITY_TICKET}/{ticket_id[:12]} -> "
              f"{history['count']} entries: {', '.join(actions)}")
        assert svc.ACTION_TICKET_CREATED in actions, actions
        assert history["entries"] == sorted(history["entries"],
                                           key=lambda e: e["seq"]), \
            "entity history must read oldest-first as a narrative"

        absent = api.entity_history(svc.ENTITY_TICKET, "no-such-ticket", conn=conn)
        assert absent["count"] == 0 and absent["entries"] == [], absent
        print("entity history for an unknown id -> 0 entries, not a 404  OK")

        feed = api.recent(limit=5, action=None, conn=conn)
        assert feed["count"] == 5, feed
        assert feed["entries"][0]["seq"] > feed["entries"][-1]["seq"], \
            "recent must read newest-first as a feed"
        filtered = api.recent(limit=50, action=svc.ACTION_TRIAGE_RUN, conn=conn)
        assert filtered["count"] == by_action[svc.ACTION_TRIAGE_RUN], filtered
        print(f"recent -> newest first; action filter returns "
              f"{filtered['count']} triage run(s)  OK")

        _run_export_checks(conn, made, run)
        _run_tamper_checks(conn)

    print("\naudit smoke test passed.")


def _run_export_checks(conn, made: list[dict], run: dict) -> None:
    """An export must find the triage run that deferred the ticket, not just the
    rows filed against it -- that run is usually what the citizen is asking about.
    """
    ticket_id = made[0]["ticket_id"]
    ref_no = made[0]["ref_no"]

    by_id = api.export(ticket_id=ticket_id, limit=500, conn=conn)
    by_ref = api.export(ticket_id=ref_no, limit=500, conn=conn)
    assert by_id["ticket_found"] and by_ref["ticket_found"]
    assert by_id["ticket_id"] == by_ref["ticket_id"] == ticket_id, (by_id, by_ref)
    assert [e["seq"] for e in by_id["entries"]] == \
           [e["seq"] for e in by_ref["entries"]], "id and ref_no must agree"

    matched = {e["matched_on"] for e in by_id["entries"]}
    print(f"\nexport?ticket_id={ref_no} -> {by_id['count']} entries, "
          f"matched_on {sorted(matched)}")
    assert "entity_id" in matched, matched
    assert "payload_reference" in matched, (
        "the triage run naming this ticket only inside its payload was not "
        "found -- payload search is not working")
    assert by_id["chain"]["ok"] is True, by_id["chain"]

    run_entries = [e for e in by_id["entries"]
                   if e["action"] == svc.ACTION_TRIAGE_RUN]
    assert run_entries, "no triage.run entry in the export"
    assert run_entries[0]["matched_on"] == "payload_reference", run_entries[0]
    print(f"   triage.run {run_entries[0]['seq']} pulled in by payload reference "
          f"(manifest {run.get('manifest_id', '')[:12]})  OK")

    detail = _expect_404(api.export, ticket_id="KMC-does-not-exist", limit=500,
                         conn=conn)
    print(f"   unknown ticket -> 404: {detail}")


def _run_tamper_checks(conn) -> None:
    """The half that matters: a chain that cannot say `ok: false` proves nothing.

    Two different attacks, because they fail differently. Editing a row in place
    leaves the links intact but breaks that row's own digest -- a *content* break,
    and verify should name exactly the row that was edited. Deleting a row from
    the middle leaves every remaining digest correct but orphans the next row's
    `prev_hash` -- a *link* break, and verify should name the row that followed
    the hole, because that is the first row that can no longer be justified.
    """
    seqs = _seqs(conn)
    target = seqs[len(seqs) // 2]

    # ---- attack 1: edit a payload in place ---------------------------------
    original = conn.execute("SELECT payload FROM audit_log WHERE seq = ?",
                            (target,)).fetchone()["payload"]
    forged = original.replace('"ref_no":"', '"ref_no":"FORGED-', 1) \
        if '"ref_no":"' in original else original + " "
    conn.execute("UPDATE audit_log SET payload = ? WHERE seq = ?",
                 (forged, target))

    broken = api.verify(conn=conn)
    print(f"\ntampered with the payload of seq {target}:")
    print(f"   ok={broken['ok']}  first_broken_seq={broken['first_broken_seq']}  "
          f"break_type={broken['break_type']}")
    print(f"   {broken['reason']}")
    assert broken["ok"] is False, broken
    assert broken["first_broken_seq"] == target, (target, broken)
    assert broken["break_type"] == "content", broken
    assert broken["verified_prefix"] == target - 1, broken

    conn.execute("UPDATE audit_log SET payload = ? WHERE seq = ?",
                 (original, target))
    restored = api.verify(conn=conn)
    assert restored["ok"] is True, restored
    print(f"   payload restored -> ok={restored['ok']}  "
          "(the break was the edit, not a false positive)")

    # ---- attack 2: remove a row from the middle -----------------------------
    conn.execute("DELETE FROM audit_log WHERE seq = ?", (target,))
    after = seqs[seqs.index(target) + 1]
    gap = api.verify(conn=conn)
    print(f"\ndeleted seq {target} outright:")
    print(f"   ok={gap['ok']}  first_broken_seq={gap['first_broken_seq']}  "
          f"break_type={gap['break_type']}")
    print(f"   {gap['reason']}")
    assert gap["ok"] is False, gap
    assert gap["break_type"] == "link", gap
    assert gap["first_broken_seq"] == after, (after, gap)
    assert target not in _seqs(conn)

    print(f"\n{gap['truncation_caveat']}")


if __name__ == "__main__":
    main()
