"""Kopargaon Civic Resource Prioritization Platform -- HTTP entrypoint.

Run it from the ``backend`` directory:

    uvicorn main:app --reload --port 8000

Two decisions in here are deliberate and worth stating, because both are about
keeping a half-migrated codebase serviceable rather than about elegance:

* **Routers are registered through a registry that tolerates failure.** The data
  layer was rebuilt on stdlib ``sqlite3``; a couple of older routers still import
  SQLAlchemy symbols that no longer exist. Importing them the ordinary way makes
  a single stale module take down the entire API, including the endpoints the
  frontend teammate is actively building against. Instead each router is imported
  in isolation and any failure is recorded, surfaced at ``/health`` and printed
  at startup. The API boots; the broken route simply is not there, and says so.
* **Startup uses ``lifespan``, not ``@app.on_event``.** The event hooks are
  deprecated in current FastAPI and emit warnings on every boot, which is the
  kind of noise that hides a real error during a demo.

``init_db()`` is idempotent: it creates the schema if absent and runs additive
migrations if the file predates a column, so starting the server is always safe.
"""
from __future__ import annotations

import importlib
import os
import sys
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
# track1_engine lives one level up, next to the backend package.
for path in (str(BACKEND_DIR), str(BACKEND_DIR.parent)):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from config import settings  # noqa: E402
from database import get_conn, init_db  # noqa: E402

# module path -> short name used in diagnostics. Order is display order in /docs.
ROUTER_MODULES: list[tuple[str, str]] = [
    ("routers.tickets", "tickets"),
    ("routers.weights", "weights"),
    ("routers.triage", "triage"),
    ("routers.explain", "explain"),
    ("routers.media", "media"),
    ("routers.audit", "audit"),
    ("routers.reference", "reference"),
    ("routers.staff", "staff"),
    ("routers.webhooks", "webhooks"),
]

ROUTERS_LOADED: list[str] = []
ROUTERS_FAILED: dict[str, str] = {}


def _register_routers(application: FastAPI) -> None:
    """Import each router alone so one stale module cannot break the rest."""
    for module_path, name in ROUTER_MODULES:
        try:
            module = importlib.import_module(module_path)
            application.include_router(module.router)
            ROUTERS_LOADED.append(name)
        except Exception as exc:  # noqa: BLE001 - deliberately broad
            ROUTERS_FAILED[name] = f"{type(exc).__name__}: {exc}"
            if settings.DEBUG:
                traceback.print_exc()


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[crpp] database   : {settings.DB_PATH}")
    print(f"[crpp] uploads    : {settings.UPLOAD_DIR}")
    print(f"[crpp] routers    : {', '.join(ROUTERS_LOADED) or 'none'}")
    if ROUTERS_FAILED:
        for name, reason in ROUTERS_FAILED.items():
            print(f"[crpp] NOT loaded : {name} -- {reason}")
    if not settings.ENFORCE_AUTH:
        print("[crpp] auth       : ENFORCE_AUTH=false, endpoints are open "
              "(set ENFORCE_AUTH=true before the judging run)")
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Prioritises competing civic complaints under a fixed daily budget and "
        "workforce, and explains every decision. Fuzzy AHP weights (consistency-"
        "gated), fuzzy TOPSIS ranking, multi-constraint knapsack allocation, "
        "perceptual-hash + geo deduplication, and a null-until-verified stance "
        "on missing data."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # A credentialed request cannot use a wildcard origin, so when CORS_ORIGINS
    # is "*" we mirror the caller's origin instead of silently failing preflight.
    allow_origins=settings.CORS_ORIGINS if "*" not in settings.CORS_ORIGINS else [],
    allow_origin_regex=".*" if "*" in settings.CORS_ORIGINS else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_register_routers(app)


@app.get("/")
def root():
    """What this service is and where to look next."""
    return {
        "message": "Kopargaon Civic Resource Prioritization Platform (CRPP)",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "tickets": "/api/tickets",
            "weights": "/api/weights",
            "triage": "/api/triage",
            "explain": "/api/explain",
            "media": "/api/media",
            "audit": "/api/audit",
            "reference": "/api/reference",
            "staff": "/api/staff",
            "webhooks": "/webhooks",
        },
        "routers_loaded": ROUTERS_LOADED,
        "routers_unavailable": sorted(ROUTERS_FAILED),
    }


@app.get("/health")
def health_check():
    """Liveness plus an honest report of what is and is not wired up.

    Returns 200 while the core ingest path works even if an older router failed
    to import, and 503 only when the database itself is unreachable -- the one
    condition under which nothing useful can happen.
    """
    db_ok, db_error, ticket_count = True, None, None
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM tickets").fetchone()
            ticket_count = int(row["n"]) if row else 0
    except Exception as exc:  # noqa: BLE001
        db_ok, db_error = False, f"{type(exc).__name__}: {exc}"

    body = {
        "status": "healthy" if db_ok else "unhealthy",
        "service": "kopargaon-crpp",
        "version": settings.APP_VERSION,
        "database": {
            "path": str(settings.DB_PATH),
            "reachable": db_ok,
            "tickets": ticket_count,
            "error": db_error,
        },
        "routers": {"loaded": ROUTERS_LOADED, "failed": ROUTERS_FAILED},
        "enforce_auth": settings.ENFORCE_AUTH,
        "notifications_enabled": settings.ENABLE_NOTIFICATIONS,
    }
    return JSONResponse(status_code=200 if db_ok else 503, content=body)


@app.get("/api/config")
def public_config():
    """Tunables the UI may display. Never includes secrets -- see
    ``Settings.as_public_dict``."""
    return settings.as_public_dict()


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("main:app", host=os.getenv("HOST", "0.0.0.0"),
                port=int(os.getenv("PORT", "8000")), reload=settings.DEBUG)
