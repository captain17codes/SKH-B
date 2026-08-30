"""Dump the real response skeleton of every GET endpoint, for BACKEND_API.md.

Not a test. This exists because the only trustworthy source for "which fields are
nullable" is a live response over the seeded database -- a docstring can drift, a
Pydantic model does not exist here, and guessing is exactly what caused the last
wiring bug.

Usage (server must already be running):
    python tools/api_shape_dump.py http://127.0.0.1:8031

Prints, per endpoint, a flattened `path: type = sample` line. `null` in the type
column is the whole point: it means the seeded DB actually returned null there.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8031"
MAXLEN = 58

# Marathi citizen text and the rupee sign are real response content; a cp1252
# console would raise UnicodeEncodeError halfway through the dump and leave a
# truncated file that looks like a backend fault.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def get(path: str):
    try:
        with urllib.request.urlopen(f"{BASE}{path}", timeout=90) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        except Exception:  # noqa: BLE001
            return exc.code, None
    except Exception as exc:  # noqa: BLE001
        return 0, {"_transport_error": f"{type(exc).__name__}: {exc}"}


def kind(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return f"list[{kind(value[0]) if value else 'empty'}]"
    return "object"


def sample(value) -> str:
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) \
        else value
    text = " ".join(str(text).split())
    return text[:MAXLEN] + ("..." if len(text) > MAXLEN else "")


def walk(node, prefix: str = "", out: list | None = None, depth: int = 0) -> list:
    out = [] if out is None else out
    if depth > 4:
        return out
    if isinstance(node, dict):
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                out.append((here, "object", f"{len(value)} key(s)"))
                walk(value, here, out, depth + 1)
            elif isinstance(value, list):
                out.append((here, kind(value), f"{len(value)} item(s)"))
                if value and isinstance(value[0], (dict, list)):
                    walk(value[0], f"{here}[0]", out, depth + 1)
            else:
                out.append((here, kind(value), sample(value)))
    elif isinstance(node, list):
        out.append((prefix or "(root)", kind(node), f"{len(node)} item(s)"))
        if node and isinstance(node[0], (dict, list)):
            walk(node[0], f"{prefix}[0]", out, depth + 1)
    return out


def report(label: str, path: str) -> None:
    status, body = get(path)
    print(f"\n### {label}\nGET {path}  ->  {status}")
    if body is None:
        print("  (no JSON body)")
        return
    for name, type_, value in walk(body):
        print(f"  {name:<52} {type_:<13} {value}")


def main() -> int:
    # Discover live ids so the {id} routes are probed against real rows rather
    # than a 404, which would document the error shape instead of the real one.
    _, tickets = get("/api/triage/priorities?limit=200")
    rows = (tickets or {}).get("tickets") or []
    ticket_id = rows[0]["id"] if rows else None
    scored = next((r["id"] for r in rows if r.get("scored")), ticket_id)
    _, today = get("/api/triage/today")
    run_id = (today or {}).get("run_id")
    manifest_id = (today or {}).get("manifest_id") or (today or {}).get("id")
    _, media = get("/api/media/index?limit=5")
    media_rows = (media or {}).get("media") or (media or {}).get("items") or []
    media_id = media_rows[0].get("media_id") or media_rows[0].get("id") \
        if media_rows else None
    _, plan = get("/api/staff/plan")
    dispatch_date = (plan or {}).get("dispatch_date")
    _, versions = get("/api/weights/versions?limit=5")
    vrows = (versions or {}).get("versions") or []
    version = vrows[0].get("version") if vrows else 1

    print(f"probe base       : {BASE}")
    print(f"ticket_id        : {ticket_id}")
    print(f"scored ticket_id : {scored}")
    print(f"run_id           : {run_id}")
    print(f"manifest_id      : {manifest_id}")
    print(f"media_id         : {media_id}")
    print(f"dispatch_date    : {dispatch_date}")
    print(f"weight version   : {version}")

    endpoints: list[tuple[str, str]] = [
        ("root", "/"),
        ("health", "/health"),
        ("public config", "/api/config"),
        # tickets
        ("tickets.list", "/api/tickets/list?limit=3"),
        ("tickets.list (filtered)",
         "/api/tickets/list?status=scheduled&sla=OVERDUE&limit=3"),
        ("tickets.queue", "/api/tickets/queue"),
        ("tickets.wards", "/api/tickets/wards"),
        ("tickets.detail", f"/api/tickets/{ticket_id}"),
        ("tickets.detail (bad id)", "/api/tickets/not-a-real-id"),
        # weights
        ("weights.active", "/api/weights/active"),
        ("weights.scale", "/api/weights/scale"),
        ("weights.versions", "/api/weights/versions?limit=3"),
        ("weights.version", f"/api/weights/versions/{version}"),
        ("weights.compare",
         f"/api/weights/compare?from_version={version}&to_version={version}"),
        # triage
        ("triage.today", "/api/triage/today"),
        ("triage.priorities", "/api/triage/priorities?limit=3"),
        ("triage.capacity", "/api/triage/capacity"),
        ("triage.manifests", "/api/triage/manifests?limit=3"),
        ("triage.manifest (date)", f"/api/triage/manifest/{dispatch_date}"),
        ("triage.manifest (no such date)", "/api/triage/manifest/2020-01-01"),
        ("triage.manifest-by-id", f"/api/triage/manifest-by-id/{manifest_id}"),
        # explain
        ("explain.ticket", f"/api/explain/{scored}"),
        ("explain.ticket (+shap)", f"/api/explain/{scored}?include_shap=true"),
        ("explain.citizen en", f"/api/explain/{scored}/citizen?lang=en"),
        ("explain.citizen mr", f"/api/explain/{scored}/citizen?lang=mr"),
        ("explain.history", f"/api/explain/{scored}/history"),
        ("explain.run", f"/api/explain/run/{run_id}?limit=3"),
        ("explain.run shap", f"/api/explain/run/{run_id}/shap"),
        # media
        ("media.index", "/api/media/index?limit=3"),
        ("media.clusters", "/api/media/clusters?limit=3"),
        ("media.ticket", f"/api/media/ticket/{ticket_id}"),
        ("media.cluster", f"/api/media/cluster/{ticket_id}"),
        # audit
        ("audit.verify", "/api/audit/verify"),
        ("audit.stats", "/api/audit/stats"),
        ("audit.recent", "/api/audit/recent?limit=3"),
        ("audit.entity", f"/api/audit/entity/ticket/{ticket_id}?limit=3"),
        ("audit.export", f"/api/audit/export?ticket_id={ticket_id}&limit=5"),
        # reference
        ("reference.config", "/api/reference/config"),
        ("reference.gaps", "/api/reference/gaps"),
        ("reference.criteria", "/api/reference/criteria"),
        ("reference.sla", "/api/reference/sla"),
        ("reference.categories", "/api/reference/categories"),
        ("reference.channels", "/api/reference/channels"),
        ("reference.contacts", "/api/reference/contacts"),
        # staff
        ("staff.plan", "/api/staff/plan"),
        ("staff.plan (no manifest)", "/api/staff/plan?dispatch_date=2020-01-01"),
        ("staff.headcount", "/api/staff/headcount"),
    ]
    for label, path in endpoints:
        report(label, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
